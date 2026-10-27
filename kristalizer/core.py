"""Kristalizer: lecture locale, exploration EncyK, staging v11 non destructif.

Tout accès à EncyK est en lecture seule. Les décisions sont humaines/explicitement
revues; un score ou une égalité de nom n'est JAMAIS une approbation canonique.
Python standard library only.
"""
from __future__ import annotations
import csv, hashlib, json, re, shutil, sqlite3, subprocess, sys, unicodedata
from collections import Counter, defaultdict
from .topic_index import build_topic_index
from datetime import datetime, timezone
from pathlib import Path

ID_RE = re.compile(r'^K([QP])([1-9]\d*)$')
WD_RE = re.compile(r'^([QP])([1-9]\d*)$')
KS_RE = re.compile(r'^KS[1-9]\d*$')
CANDIDATE_FIELDS = ['project','namespace','kind','local_id','external_id','local_label','wikidata_label','wikidata_description','origin','name_relation','risk','evidence','decision_hint']
DECISION_FIELDS = ['project','local_id','external_id','decision','reviewer','reason','evidence_refs']


def clean(s):
    s=unicodedata.normalize('NFKD', str(s or ''))
    return ' '.join(re.sub(r'[^\w]+',' ',''.join(c for c in s if not unicodedata.combining(c)).casefold()).split())


def load(path):
    with Path(path).open('r', encoding='utf-8-sig') as f: return json.load(f)


def dump(path, obj):
    path=Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w',encoding='utf-8') as f: json.dump(obj,f,indent=2,ensure_ascii=False,sort_keys=True);f.write('\n')


def read_csv(path):
    path=Path(path)
    if not path.is_file(): return []
    with path.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def write_csv(path,rows,fields):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    # Atomic replacement; decisions existing kept across scans.
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    temp.replace(path)


def goodpath(root,relative):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute() or '\\' in relative:
        raise ValueError('Chemin relatif non autorisé: '+str(relative))
    p=Path(relative)
    if '..' in p.parts or '.' in p.parts: raise ValueError('Parcours interdit: '+relative)
    root=Path(root).resolve()
    path=(root/p).resolve()
    if not path.is_relative_to(root):raise ValueError('Évasion du workspace: '+relative)
    return path


def discover(root):
    root=Path(root).expanduser().resolve()
    if not root.is_dir():raise FileNotFoundError('Dossier source introuvable: '+str(root))
    if (root/'kristal.workspace.json').is_file():return [root]
    projects=[p for p in root.iterdir() if p.is_dir() and (p/'kristal.workspace.json').is_file()]
    if not projects:
        raise ValueError('Aucun kristal.workspace.json trouvé dans le dossier ou ses sous-dossiers directs.')
    return sorted(projects,key=lambda p:p.name.casefold())


class EncyIndex:
    def __init__(self,path):
        self.path=Path(path).expanduser().resolve() if path else None
        self.db=None;self.names=False
        if self.path and self.path.is_file():
            self.db=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)
            self.db.row_factory=sqlite3.Row
            cols={r['name'] for r in self.db.execute('PRAGMA table_info(entity)')}
            if not {'id','wid','kind','label_fr','label_en','description_fr','description_en'} <= cols:
                self.close();raise ValueError('L’index SQLite EncyK a un schéma incompatible.')
            tables={r['name'] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            indexes={r['name'] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
            self.names='name' in tables and 'idx_name_norm' in indexes

    def close(self):
        if self.db:self.db.close();self.db=None
    def __enter__(self):return self
    def __exit__(self,*exc):self.close()
    def details(self,wid):
        if not self.db:return {}
        kind=wid[:1];number=wid[1:]
        if not WD_RE.fullmatch(wid):return {}
        eid=int(number)+(1_000_000_000 if kind=='P' else 0)
        r=self.db.execute('SELECT wid,label_fr,label_en,description_fr,description_en,kind FROM entity WHERE id=?',(eid,)).fetchone()
        if not r:return {'missing':True}
        if r['wid']!=wid:return {'missing':True}
        return {'label':r['label_fr'] or r['label_en'] or '',
                'description':r['description_fr'] or r['description_en'] or '', 'kind':r['kind']}

    def matches(self,label,kind,max_results=8):
        if not self.db or not self.names or not clean(label):return []
        rows=self.db.execute('SELECT DISTINCT e.wid,e.label_fr,e.label_en,e.description_fr,e.description_en '
            'FROM name n JOIN entity e ON e.id=n.entity_id WHERE n.norm=? AND e.wid LIKE ? LIMIT ?',
            (clean(label),kind+'%',max_results+1)).fetchall()
        return [ {'wid':r['wid'],'label':r['label_fr'] or r['label_en'] or '',
                  'description':r['description_fr'] or r['description_en'] or ''} for r in rows[:max_results] ]


def v11_assets(project):
    p=project/'.kristal/v11/authoring.json'
    if p.is_file():
        profile=load(p)
        files={key:goodpath(project,profile[key]) for key in ('registry','graph','crosswalk','catalog')}
    else:
        base=project/'.kristal/v11'
        names={'registry':'identity-registry.json','graph':'semantic-graph.json',
               'crosswalk':'external-crosswalk.json','catalog':'dictionaries/catalog.json'}
        files={k:base/v for k,v in names.items()}
    if not all(x.is_file() for x in files.values()):return None
    objs={k:load(v) for k,v in files.items()}
    ns=objs['registry']['namespace_id']
    if objs['graph']['namespace_id']!=ns or objs['catalog']['namespace_id']!=ns:
        raise ValueError(f'Namespaces v11 incohérents dans {project.name}')
    return {'files':files, 'objects':objs, 'namespace':ns,
            'active_profile':p.is_file(), 'ids':{x['id']:x['kind'] for x in objs['registry']['identities']}}


def labels_from_catalog(project,assets):
    catalog=assets['objects']['catalog'];catalog_path=assets['files']['catalog']
    labels={};aliases=defaultdict(list)
    # Prioritize preferred_term from curated layers, then stable lexical layers.
    for language in catalog.get('languages',[]):
        for layer in sorted(language.get('layers',[]),key=lambda x:-int(x.get('priority',0))):
            path=goodpath(catalog_path.parent,layer['path'])
            if not path.is_file():continue
            if layer.get('sha256') and hashlib.sha256(path.read_bytes()).hexdigest()!=layer['sha256']:
                raise ValueError('Dictionnaire modifié/empreinte incorrecte: '+str(path))
            try:entries=load(path).get('entries',[])
            except (json.JSONDecodeError,ValueError):continue
            for entry in entries:
                sid=entry.get('semantic_id','')
                value=entry.get('preferred_term','')
                if sid and value: labels.setdefault(sid,value)
                for alt in entry.get('synonyms',[]):
                    if isinstance(alt,str) and alt not in aliases[sid]:aliases[sid].append(alt)
    return labels,aliases


def skope_candidate_labels(project):
    current=project/'sources/wikidata-skope/current.json'
    if not current.is_file():return {}
    run=load(current).get('run_id','')
    if not isinstance(run,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,90}',run):return {}
    path=project/'sources/wikidata-skope/runs'/run/'raw/review-candidates.generated.csv'
    if not path.is_file():return {}
    return {(r.get('semantic_id',''),r.get('candidate_external_id','')):r
            for r in read_csv(path) if r.get('semantic_id') and r.get('candidate_external_id')}


def skope_rows(project):
    current=project/'sources/wikidata-skope/current.json'
    if not current.is_file():return []
    obj=load(current);run=obj.get('run_id')
    if not isinstance(run,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,90}',run):return []
    f=project/'sources/wikidata-skope/runs'/run/'crosswalk-candidates.jsonl'
    if not f.is_file():return []
    out=[]
    with f.open('r',encoding='utf-8') as reader:
        for line in reader:
            if not line.strip():continue
            x=json.loads(line);a=x.get('KQ_ou_KP','');b=x.get('Wikidata_QID_ou_PID','')
            if ID_RE.fullmatch(a) and WD_RE.fullmatch(b) and a[1]==b[0]:
                out.append((a,b))
    return sorted(set(out))


def identity_roles(project, assets):
    """Classify migrated KQ by *semantic role*, not by their lexical similarity.

    Bulk-migrated claim referents and metadata codes are not Wikidata topics.
    Mapping a metadata value such as 'time' to Q11471 would be a false exactMatch.
    For projects without an explicit legacy migration map, do not guess roles.
    """
    path=project/'.kristal/v11/identity-migration-map.json'
    roles={}
    if not path.is_file():return roles
    mp=load(path).get('by_kind',{}).get('Q',{})
    if not isinstance(mp,dict):return roles
    for legacy,local in mp.items():
        if assets['ids'].get(local)!='entity':continue
        if legacy.startswith('dik:metadata-value:'):
            roles[local]='METADONNEE_CATEGORIELLE'
        elif legacy.startswith('urn:foodkristal:source:'):
            roles[local]='REFERENCE_SOURCE'
        elif ':concept:' in legacy and re.search(r':\d+$',legacy):
            roles[local]='REFERENT_ASSERTION'
        else:
            roles[local]='DOMAINE_A_VERIFIER'
    for legacy,local in load(path).get('by_kind',{}).get('P',{}).items():
        if assets['ids'].get(local)=='property' and (legacy.startswith('dik:metadata:') or legacy.startswith('kristal.source.')):
            roles[local]='PROPRIETE_STRUCTURELLE_INTERNE'
    return roles


def topic_wikidata_risk(human_label, remote_label, description):
    """Conservative hints for topic *suggestions*, never identity approvals.

    A subject heading can match the title of a film, song, article or patent.
    Keep the candidate (no data loss), but clearly mark the disambiguation risk.
    """
    d=clean(description)
    if any(phrase in d for phrase in ('page d homonymie','wikimedia disambiguation',
                                      'wikimedia disambiguation page')):
        return 'HOMONYMIE'
    misleading=(
        'work of art','artwork','oeuvre d art','scholarly article','article scientifique',
        'academic article','film sorti','film americain','motion picture','feature film',
        'album de','music album','song by','chanson de','peinture de','painting by',
        'television series','serie televisee','tv series','novel by','roman de',
        'bande dessinee','comic strip','strip de','brevet','us patent',
        'published in','publication scientifique','scientific article','journal article',
        'research article','book by','livre de','us patent','single by', 'chanson d',
        'album d', 'rock band', 'groupe musical', 'bande de rock',
    )
    # Require complete phrase matching for short terms such as 'album'.
    if any(re.search(r'(?<!\w)'+re.escape(phrase)+r'(?!\w)', d) for phrase in misleading):
        return 'HORS_DOMAINE_PROBABLE'
    if clean(remote_label)==clean(human_label):return 'NOM_IDENTIQUE_NON_PROUVE'
    return 'AUTRE_NOM_A_CONTROLER'


def topics_from_sources(project, db, max_results):
    """Inventory explicit claim-set topics, *without fabricating a KQ mapping*.

    Each claim-set often contains hundreds of statement-specific referents. Its
    topic is an index heading, not an existing KQ exactMatch. Wikidata matches
    for topics are deliberately in a separate queue.
    """
    sources=project/'knowledge-base/sources'
    topics=[];suggestions=[];catalog_count=0
    if not sources.is_dir():return topics,suggestions,0
    for f in sorted(sources.rglob('*.json')):
        try:obj=load(f)
        except (ValueError, OSError):continue
        if not isinstance(obj,dict):continue
        claims=obj.get('claims')
        if not isinstance(claims,list):
            catalog_count+=1;continue
        topic=obj.get('topic') or f.stem
        if not isinstance(topic,str) or not topic.strip():topic=f.stem
        # Source headings are suggestions, NOT local canonical entity labels.
        human_label=topic.replace('_',' ').replace('-',' ').strip()
        example=''
        for claim in claims:
            if not isinstance(claim,dict):continue
            subject=claim.get('statement',{})
            text=subject.get('object',{}) if isinstance(subject,dict) else {}
            if isinstance(text,dict) and isinstance(text.get('value'),str):
                example=text['value'][:320];break
        row={'project':project.name,'topic':topic,'label_search':human_label,
             'source_file':f.relative_to(project).as_posix(),
             'claims_count':len(claims),'example_claim':example,
             'existing_kq':'',
             'identity_status':'NOTION_A_MODELER_SANS_KQ_CERTIFIE',
             'note':'Intitulé de section, pas identité KQ ni exactMatch'}
        topics.append(row)
        for remote in db.matches(human_label,'Q',max_results):
            desc=remote['description']; label=remote['label']
            risk=topic_wikidata_risk(human_label,label,desc)
            suggestions.append({'project':project.name,'topic':topic,'label_search':human_label,
                'source_file':row['source_file'],'wikidata_id':remote['wid'],
                'wikidata_label':label,'wikidata_description':desc,
                'risk':risk,'status':'EXPLORATOIRE_SANS_KQ',
                'note':'Proposition de notion : aucune insertion dans les décisions KQ'})
    return topics,suggestions,catalog_count


def audit_project(project,db,max_lookups=8):
    assets=v11_assets(project)
    if assets is None:
        return {'project':project.name,'state':'MIGRATION_V11_REQUISE','candidates':[], 'count':0,
                'excluded':[], 'roles':{},'topics':[],'topic_suggestions':[], 'source_catalog_files':0,
                'detail':'Aucun ensemble registre/graphe/crosswalk/catalog v11 complet; aucune identité fabriquée.'}
    ids=assets['ids'];ns=assets['namespace']
    labels,_=labels_from_catalog(project,assets)
    roles=identity_roles(project,assets)
    skope_names=skope_candidate_labels(project)
    found={};excluded={}
    def candidate(local_id,ext,origin):
        if not ID_RE.fullmatch(local_id) or not WD_RE.fullmatch(ext) or local_id[1]!=ext[0]:return
        if ids.get(local_id)!= ('entity' if local_id.startswith('KQ') else 'property'):return
        k=(local_id,ext)
        role=roles.get(local_id,'DOMAINE_A_VERIFIER')
        if role in ('METADONNEE_CATEGORIELLE','REFERENT_ASSERTION','REFERENCE_SOURCE','PROPRIETE_STRUCTURELLE_INTERNE'):
            excluded.setdefault(k,{'project':project.name,'local_id':local_id,'external_id':ext,
                'local_label':labels.get(local_id,''),'reason':role,'origin':origin})
            return
        found.setdefault(k,set()).add(origin)
    for local,external in skope_rows(project):candidate(local,external,'skope')
    for m in assets['objects']['crosswalk'].get('mappings',[]):
        lr=m.get('local_ref',{});er=m.get('external_ref',{})
        if er.get('system')=='wikidata':candidate(lr.get('id',''),er.get('id',''),'crosswalk_'+m.get('status','candidate'))
    searched=0
    if db.names:
        for local,kind in ids.items():
            if kind not in ('entity','property') or not labels.get(local):continue
            if roles.get(local) in ('METADONNEE_CATEGORIELLE','REFERENT_ASSERTION','REFERENCE_SOURCE','PROPRIETE_STRUCTURELLE_INTERNE'):
                continue
            searched+=1
            for remote in db.matches(labels[local],local[1],max_lookups):candidate(local,remote['wid'],'index_nom_alias')
    rows=[]
    for (local,external),origins in sorted(found.items()):
        remote=db.details(external)
        fallback=skope_names.get((local,external),{})
        ll=labels.get(local,'') or fallback.get('label','')
        rl=remote.get('label','') or fallback.get('candidate_label','')
        desc=remote.get('description','') or fallback.get('candidate_description','')
        status='identique' if ll and rl and clean(ll)==clean(rl) else 'autre_nom'
        risk='A_REVOIR'
        if remote.get('missing'):risk='QID_PID_ABSENT_INDEX'
        elif any(w in clean(desc) for w in ('page d homonymie','disambiguation page','wikimedia disambiguation')):
            risk='HOMONYMIE_A_ECARTER'
        elif status=='identique':risk='NOM_IDENTIQUE_NON_PROUVÉ'
        rows.append({'project':project.name,'namespace':ns,'kind':local[:2],'local_id':local,'external_id':external,
                     'local_label':ll,'wikidata_label':rl,'wikidata_description':desc,
                     'origin':'+'.join(sorted(origins)),'name_relation':status,'risk':risk,
                     'evidence':'SOURCE_SKOPE' if 'skope' in origins else 'AUCUNE_PREUVE_KS_VALIDEE',
                     'decision_hint':'review'})
    topics,suggestions,catalog_count=topics_from_sources(project,db,max_lookups)
    return {'project':project.name,'state':'V11_ACTIF' if assets['active_profile'] else 'V11_NON_ACTIVE',
            'candidates':rows,'excluded':list(excluded.values()),'count':len(rows),
            'topics':topics,'topic_suggestions':suggestions,'source_catalog_files':catalog_count,
            'roles':dict(Counter(roles.values())),
            'namespace':ns,'indexed_labels':searched,
            'skope_present':bool((project/'sources/wikidata-skope/current.json').is_file())}


def scan(source,output,index=None,max_lookups=8):
    source=Path(source).resolve();output=Path(output).resolve()
    if source==output or output.is_relative_to(source):raise ValueError('Sortie doit être en dehors du dossier de Kristals.')
    projects=discover(source)
    if len({p.name.casefold() for p in projects}) != len(projects):raise ValueError('Noms de Kristals ambigus.')
    out=output/'ANALYSE';out.mkdir(parents=True,exist_ok=True)
    old=read_csv(out/'DECISIONS.csv');archived=read_csv(out/'DECISIONS_ARCHIVEES.csv')
    # Decisions reappearing after an updated scan can be restored, preserving
    # reviews and approved/rejected statuses. Never delete old retired decisions.
    previous={(r['project'],r['local_id'],r['external_id']):r for r in archived}
    previous.update({(r['project'],r['local_id'],r['external_id']):r for r in old})
    old_candidates=read_csv(out/'CANDIDATS.csv')
    old_exclusions=read_csv(out/'CANDIDATS_EXCLUS.csv')
    allrows=[];reports=[];excluded=[];topics=[];suggestions=[]
    roles_by_project={}
    with EncyIndex(index) as db:
        for project in projects:
            report=audit_project(project,db,max_lookups)
            allrows.extend(report.pop('candidates'))
            excluded.extend(report.pop('excluded'))
            topics.extend(report.pop('topics'))
            suggestions.extend(report.pop('topic_suggestions'))
            reports.append(report)
            assets=v11_assets(project)
            roles_by_project[project.name]=identity_roles(project,assets) if assets else {}
        index_state={'index':str(db.path) if db.path else None,'connected':db.db is not None,'name_search_available':db.names}
    allrows.sort(key=lambda r:(r['project'],r['kind'],r['local_id'],r['external_id']))
    current={(r['project'],r['local_id'],r['external_id']) for r in allrows}
    decisions=[previous.get(key,{'project':key[0],'local_id':key[1],'external_id':key[2],
           'decision':'pending','reviewer':'','reason':'','evidence_refs':''}) for key in
           [(r['project'],r['local_id'],r['external_id']) for r in allrows]]
    retired=[r for key,r in sorted(previous.items()) if key not in current]
    for r in old_candidates:
        key=(r['project'],r['local_id'],r['external_id'])
        if key not in current and not any((e['project'],e['local_id'],e['external_id'])==key for e in excluded):
            excluded.append({'project':r['project'],'local_id':r['local_id'],'external_id':r['external_id'],
                'local_label':r.get('local_label',''),'reason':roles_by_project.get(r['project'],{}).get(r['local_id'],'ANCIEN_CANDIDAT_NON_REPRODUIT'),
                'origin':r.get('origin','')})
    # Show the exact historical pairs removed from the active register.
    newly_excluded={(r['project'],r['local_id'],r['external_id']):r for r in old_exclusions
                    if (r['project'],r['local_id'],r['external_id']) not in current}
    newly_excluded.update({(r['project'],r['local_id'],r['external_id']):r for r in excluded})
    write_csv(out/'CANDIDATS.csv',allrows,CANDIDATE_FIELDS)
    write_csv(out/'DECISIONS.csv',decisions,DECISION_FIELDS)
    write_csv(out/'DECISIONS_ARCHIVEES.csv',retired,DECISION_FIELDS)
    write_csv(out/'CANDIDATS_EXCLUS.csv',list(newly_excluded.values()),
              ['project','local_id','external_id','local_label','reason','origin'])
    write_csv(out/'NOTIONS_DOMAINE.csv',topics,
              ['project','topic','label_search','source_file','claims_count','example_claim','existing_kq','identity_status','note'])
    write_csv(out/'SUGGESTIONS_NOTIONS_WIKIDATA.csv',suggestions,
              ['project','topic','label_search','source_file','wikidata_id','wikidata_label','wikidata_description','risk','status','note'])
    links,topic_review,missing=build_topic_index(projects,load,topics,suggestions)
    write_csv(out/'LIAISONS_NOTIONS_ASSERTIONS.csv',links,
              ['project','topic','source_file','claim_id','original_subject','existing_kq','existing_ka','evidence_refs','status'])
    write_csv(out/'REVUE_IDENTITES_NOTIONS.csv',topic_review,
              ['project','topic','claims_count','source_file','wikidata_candidates','candidates_to_review','qid_to_review','status','note'])
    stats={'format':'kristal.kristalizer.scan/1.2.2','generated_at':datetime.now(timezone.utc).isoformat(),
           'projects':len(projects),'candidates':len(allrows),'historical_candidates_excluded':len(newly_excluded),
           'decisions_archived':len(retired),'existing_decisions_preserved':sum(k in previous for k in current),
           'domain_topics':len(topics),'topic_wikidata_suggestions':len(suggestions),
           'native_claim_links':len(links)-len(missing),'unresolved_claim_links':len(missing),
           'indexed':index_state,'projects_detail':reports,'migration_required':sum(r['state']=='MIGRATION_V11_REQUISE' for r in reports),
           'notice':'Les notions documentaires ne sont pas des KQ. Aucun exactMatch, KS ni KA n’est approuvé par le scan.'}
    dump(out/'RAPPORT.json',stats)
    return stats


def make_crosswalk(project,assets,decisions):
    obj=json.loads(json.dumps(assets['objects']['crosswalk']))
    mappings=obj.get('mappings',[])
    existing={(m['local_ref']['id'],m['external_ref']['id']):m for m in mappings if m.get('external_ref',{}).get('system')=='wikidata'}
    lused={};eused={}
    for m in mappings:
        if m.get('status')=='accepted' and m.get('relation')=='exactMatch':
            lused[m['local_ref']['id']]=m['external_ref']['id'];eused[m['external_ref']['id']]=m['local_ref']['id']
    count=0
    for row in decisions:
        if row.get('decision','').lower()!='approved':continue
        local=row['local_id'];ext=row['external_id']
        kind=assets['ids'].get(local)
        if not ID_RE.fullmatch(local) or not WD_RE.fullmatch(ext) or local[1]!=ext[0] or kind!=('entity' if local[1]=='Q' else 'property'):
            raise ValueError(f'Identité invalide: {project.name}:{local} -> {ext}')
        ks=[x.strip() for x in row.get('evidence_refs','').split(';') if x.strip()]
        graph_sources=set(assets['objects']['graph'].get('sources',[]))
        if not ks or any(not KS_RE.fullmatch(x) or assets['ids'].get(x)!='source' or x not in graph_sources for x in ks):
            raise ValueError(f'{project.name}: approbation {local}->{ext} requiert des KS du graphe, réellement pertinents.')
        if not row.get('reviewer','').strip() or not row.get('reason','').strip():
            raise ValueError(f'{project.name}: approbation sans reviewer ou justification: {local}->{ext}')
        if local in lused and lused[local]!=ext or ext in eused and eused[ext]!=local:
            raise ValueError(f'Conflit exactMatch dans {project.name}: {local} / {ext}')
        lused[local]=ext;eused[ext]=local
        prior=existing.get((local,ext))
        if prior and prior.get('status')=='accepted':continue
        mid='kristalizer-M'+str(int(hashlib.sha256((assets['namespace']+'|'+local+'|'+ext).encode()).hexdigest(),16))[:25]
        m={'mapping_id':mid,'local_ref':{'namespace_id':assets['namespace'],'id':local},
            'external_ref':{'system':'wikidata','id':ext},'status':'accepted','relation':'exactMatch',
            'review':{'method':'human','decision_id':'kristalizer-review-'+hashlib.sha256((mid+row['reviewer']+row['reason']).encode()).hexdigest()[:20],
                      'evidence_refs':ks}}
        if prior:
            mappings[mappings.index(prior)]=m
        else:mappings.append(m)
        count+=1
    return obj,count


def stage(source,output):
    src=Path(source).resolve();out=Path(output).resolve()
    if src==out or out.is_relative_to(src) or src.is_relative_to(out):raise ValueError('Sortie et source doivent être séparées.')
    projects=discover(src);dec=read_csv(out/'ANALYSE/DECISIONS.csv')
    if not (out/'ANALYSE/DECISIONS.csv').is_file():raise ValueError('Lancer Analyser avant Préparer.')
    known={(r['project'],r['local_id'],r['external_id']) for r in read_csv(out/'ANALYSE/CANDIDATS.csv')}
    for r in dec:
        if r['decision'].lower()=='approved' and (r['project'],r['local_id'],r['external_id']) not in known:
            raise ValueError('Décision non reliée à un candidat actuel: '+str(r))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target=out/'STAGING'/stamp
    seq=1
    while target.exists():target=out/'STAGING'/(stamp+'_'+str(seq));seq+=1
    target.mkdir(parents=True)
    stats=[]
    for p in projects:
        copy=target/p.name
        try:
            # A symlink could direct a Kit write outside staging. Refuse rather
            # than assume every historical workspace uses safe links.
            if any(item.is_symlink() for item in p.rglob('*')):
                raise ValueError('Symlinks interdits pour staging (risque de sortie hors de la copie): '+str(p))
            shutil.copytree(p,copy,symlinks=True)
            assets=v11_assets(copy)
            if assets is None:
                stats.append({'project':p.name,'status':'MIGRATION_MANUELLE_V11','mappings_new':0});continue
            obj,n=make_crosswalk(copy,assets,[r for r in dec if r['project']==p.name])
            # Already active: stage a versioned crosswalk only when approvals changed.
            # Complete pre-v11 assets: bootstrap all four registered canonical inputs.
            bootstrap=not assets['active_profile']
            if n or bootstrap:
                fname='canon/domain/v11/kristalizer-staging-'+stamp+'/external-crosswalk.json'
                dst=goodpath(copy,fname)
                dump(dst,obj)
                artifacts={'crosswalk':fname}
                if bootstrap:
                    prefix='canon/domain/v11/kristalizer-staging-'+stamp+'/'
                    for key,rel in [('registry','identity-registry.json'),('graph','semantic-graph.json'),
                                    ('catalog','dictionaries/catalog.json')]:
                        dest=goodpath(copy,prefix+rel)
                        dest.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copy2(assets['files'][key],dest)
                        artifacts[key]=prefix+rel
                    src_catalog=assets['files']['catalog']
                    dst_catalog=goodpath(copy,artifacts['catalog'])
                    for lang in assets['objects']['catalog'].get('languages',[]):
                        for layer in lang.get('layers',[]):
                            srclayer=goodpath(src_catalog.parent,layer['path'])
                            dstlayer=goodpath(dst_catalog.parent,layer['path'])
                            dstlayer.parent.mkdir(parents=True,exist_ok=True)
                            shutil.copy2(srclayer,dstlayer)
                else:
                    for key in ('registry','graph','catalog'):
                        artifacts[key]=assets['files'][key].relative_to(copy).as_posix()
                manifest={'format':'kristal.kristalizer.stage/1.1','project':p.name,
                    'new_crosswalk':fname,'bootstrap':bootstrap,**artifacts,
                    'new_approved_mappings':n,
                    'note':'Artefacts enregistrés puis activation de profil uniquement via le Kit sur cette copie.'}
                dump(copy/'KRISTALIZER_PENDING_ACTIVATION.json',manifest)
            stats.append({'project':p.name,
                          'status':'V11_A_ACTIVER' if bootstrap else 'CROSSWALK_A_ACTIVER' if n else 'COPIE_INCHANGEE',
                          'mappings_new':n})
        except Exception:
            # On never modify source; report incomplete staging prominently.
            dump(target/'ECHEC_STAGE.json',{'project':p.name,'notice':'Copie de staging partielle; ne pas utiliser cette livraison.'})
            raise
    report={'format':'kristal.kristalizer.stage/1.1','source':str(src),'staging':str(target),'projects':stats,
      'source_modified':False,'canon_domain_assertions_added':0,
      'note':'Ce staging prépare les crosswalks approuvés. Il ne fabrique pas automatiquement des KA ou KS de domaine.'}
    dump(target/'KRISTALIZER_STAGE_REPORT.json',report)
    return report


def kit_command(kit_script,project,command,*args):
    call=[sys.executable,str(kit_script),command,str(project),*map(str,args)]
    proc=subprocess.run(call,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
    if proc.returncode:raise RuntimeError(f'{project.name}: {command} erreur ({proc.returncode}):\n{proc.stdout[-3500:]}')
    return proc.stdout.strip()[-1100:]


def build(staging,kit_script,publish=False,activate=False):
    if activate and not publish:raise ValueError('Activation exige --publish explicite.')
    root=Path(staging).resolve();kit_script=Path(kit_script).resolve()
    if not kit_script.is_file():raise FileNotFoundError('Kit tools/kristal.py non trouvé: '+str(kit_script))
    prior=root/'KRISTALIZER_STAGE_REPORT.json'
    if not prior.is_file():prior=root/'BRIDGE_STAGE_REPORT.json'  # compatibilité historique
    if not prior.is_file():raise ValueError('Dossier STAGING invalide (rapport manquant).')
    report=load(prior);results=[]
    # Never changes any original Kristal; operates only on stage folder.
    for record in report['projects']:
        proj=root/record['project']
        phase='check'
        try:
            if record['status']=='MIGRATION_MANUELLE_V11':
                results.append({'project':proj.name,'status':'MIGRATION_MANUELLE_V11'});continue
            manifest=proj/'KRISTALIZER_PENDING_ACTIVATION.json'
            if not manifest.is_file():manifest=proj/'BRIDGE_PENDING_ACTIVATION.json'  # compatibilité historique
            if manifest.is_file():
                x=load(manifest)
                phase='register-crosswalk'
                historical_prefix='urn:kristal:bridge:' if manifest.name.startswith('BRIDGE_') else 'urn:kristal:kristalizer:'
                kid=historical_prefix+'crosswalk:'+hashlib.sha256((proj.name+x['new_crosswalk']).encode()).hexdigest()[:28]
                # Idempotent recovery after an interrupted registration.
                if x.get('bootstrap'):
                    contracts={'registry':'kristal.v11.identity-registry',
                               'graph':'kristal.v11.semantic-graph',
                               'catalog':'kristal.v11.dictionary-catalog'}
                    for key,contract in contracts.items():
                        logical_id=historical_prefix+key+':'+hashlib.sha256((proj.name+x[key]).encode()).hexdigest()[:28]
                        idx=load(proj/'canon/state.index.json')
                        exists=[a for a in idx.get('canonical_artifacts',[]) if a.get('artifact_id')==logical_id]
                        if exists and (len(exists)!=1 or exists[0].get('path')!=x[key]):
                            raise ValueError('Conflit d’enregistrement '+key)
                        if not exists:
                            phase='register-'+key
                            kit_command(kit_script,proj,'register-artifact','--file',x[key],
                                        '--artifact-id',logical_id,'--contract-id',contract,'--contract-version','11.0')
                    phase='register-crosswalk'
                state_index=load(proj/'canon/state.index.json')
                registered=[a for a in state_index.get('canonical_artifacts',[]) if a.get('artifact_id')==kid]
                if registered:
                    if len(registered)!=1 or registered[0].get('path')!=x['new_crosswalk']:
                        raise ValueError('Conflit de reprise: identifiant déjà engagé pour un autre artefact.')
                else:
                    kit_command(kit_script,proj,'register-artifact','--file',x['new_crosswalk'],'--artifact-id',kid,
                                '--contract-id','kristal.v11.external-crosswalk','--contract-version','11.0')
                phase='enable-v11'
                # The Kit refuses to overwrite an existing v11 profile. There is no
                # select-v11-crosswalk command; preserve the exact old profile in
                # versioned history, then enable the new crosswalk on this COPY only.
                profile=proj/'.kristal/v11/authoring.json'
                original_profile=None
                if profile.is_file():
                    original_profile=profile.read_bytes()
                    digest=hashlib.sha256(original_profile).hexdigest()[:20]
                    history=proj/'.kristal/v11/history'/('kristalizer-before-'+digest+'.authoring.json')
                    history.parent.mkdir(parents=True,exist_ok=True)
                    if history.exists() and history.read_bytes()!=original_profile:
                        raise ValueError('Historique du profil v11 en conflit: '+str(history))
                    if not history.exists():history.write_bytes(original_profile)
                    profile.unlink()  # strictly the staging copy; backup above
                try:
                    kit_command(kit_script,proj,'enable-v11','--registry',x['registry'],'--graph',x['graph'],
                                '--crosswalk',x['new_crosswalk'],'--catalog',x['catalog'])
                except Exception:
                    if original_profile is not None and not profile.exists():profile.write_bytes(original_profile)
                    raise
                # Consumed marker removed ONLY after successful enable, prevents double register on rerun.
                manifest.rename(proj/'KRISTALIZER_CROSSWALK_APPLIQUE.json')
            phase='check-v11'
            kit_command(kit_script,proj,'check-v11')
            phase='check'
            kit_command(kit_script,proj,'check')
            phase='build-v9'
            kit_command(kit_script,proj,'build-v9')
            if publish:
                phase='publish-v9';kit_command(kit_script,proj,'publish-v9')
            if activate:
                phase='activate-v9';kit_command(kit_script,proj,'activate-v9','--channel','current')
            results.append({'project':proj.name,'status':'ACTIVE' if activate else 'PUBLIE' if publish else 'BUILT','checks':'passed'})
        except Exception as exc:
            results.append({'project':proj.name,'status':'FAILED','phase':phase,'error':str(exc)})
            # Continue to other projects, retain failing staging for diagnosis.
    outcome={'format':'kristal.kristalizer.build/1.1','staging':str(root), 'publish':publish,'activate':activate,
             'projects':results,'failures':sum(r['status']=='FAILED' for r in results)}
    dump(root/'KRISTALIZER_BUILD_REPORT.json',outcome)
    return outcome


def import_legacy_decisions(old_file,output):
    """Import décisions v1-v13 sans effacer le nouveau registre ni inventer de candidats.

    Seules les clés présentes dans le scan courant sont mises à jour.
    Les autres sont exportées pour reprise et non silencieusement supprimées.
    """
    old_file=Path(old_file).resolve();out=Path(output).resolve()/'ANALYSE'
    master=out/'DECISIONS.csv'
    if not master.is_file():raise ValueError('Analyser les Kristals avant import des décisions historiques.')
    existing=read_csv(master);index={(x['project'],x['local_id'],x['external_id']):x for x in existing}
    imported=0;unchanged=0;notfound=[];conflicts=[];seen=set()
    for src in read_csv(old_file):
        k=tuple(src.get(x,'') for x in ('project','local_id','external_id'))
        if k in seen:raise ValueError('Décision historique dupliquée: '+str(k))
        seen.add(k)
        if k not in index:notfound.append(src);continue
        status=(src.get('decision') or 'pending').lower().strip()
        status={'accepté':'approved','accepte':'approved','rejeté':'rejected','rejete':'rejected'}.get(status,status)
        if status not in ('pending','approved','rejected'):
            conflicts.append({'project':k[0],'local_id':k[1],'external_id':k[2],'cause':'Statut inconnu: '+status});continue
        dest=index[k];curr=dest.get('decision','pending').lower().strip()
        if status=='pending':unchanged+=1;continue
        if curr not in ('','pending',status):
            conflicts.append({'project':k[0],'local_id':k[1],'external_id':k[2],'cause':'Décision déjà présente: '+curr});continue
        if status=='approved' and not all((src.get(x) or '').strip() for x in ('reviewer','reason','evidence_refs')):
            conflicts.append({'project':k[0],'local_id':k[1],'external_id':k[2],'cause':'Approbation sans reviewer, raison ou KS'});continue
        dest.update({f:src.get(f,'') for f in ('reviewer','reason','evidence_refs')});dest['decision']=status
        imported+=1
    # Write review output first, then backup master and write changes atomically.
    write_csv(out/'IMPORT_NON_RETROUVES.csv',notfound,DECISION_FIELDS)
    write_csv(out/'IMPORT_CONFLITS.csv',conflicts,['project','local_id','external_id','cause'])
    if imported:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup=out/('DECISIONS_BACKUP_'+stamp+'.csv')
        shutil.copy2(master,backup)
        write_csv(master,existing,DECISION_FIELDS)
    report={'format':'kristal.kristalizer.import-legacy/1.1','imported':imported,
            'not_found':len(notfound),'conflicts':len(conflicts),'pending_ignored':unchanged}
    dump(out/'IMPORT_RAPPORT.json',report)
    return report
