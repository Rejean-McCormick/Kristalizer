"""Traceability of source claim topics to migrated v11 identities (read-only)."""
from pathlib import Path
from collections import defaultdict

def build_topic_index(projects, load, topic_rows, wikidata_rows):
    links=[];missing=[]
    for project in projects:
        migration=project/'.kristal/v11/identity-migration-map.json'
        if not migration.is_file():continue
        m=load(migration).get('by_kind',{})
        for file in sorted((project/'knowledge-base/sources').glob('*.json')):
            d=load(file)
            if not isinstance(d,dict) or not isinstance(d.get('claims'),list):continue
            topic=d.get('topic') or file.stem
            for claim in d['claims']:
                cid=claim.get('claim_id','');a=cid.split(':',2)
                aid=('urn:'+a[0]+':assertion:'+a[1]+'/'+a[2]) if len(a)==3 else ''
                sid=claim.get('statement',{}).get('subject',{}).get('id','')
                kq=m.get('Q',{}).get(sid,'');ka=m.get('A',{}).get(aid,'')
                status='LIAISON_EXISTANTE' if kq and ka else 'A_RECONCILIER'
                links.append({'project':project.name,'topic':topic,'source_file':file.relative_to(project).as_posix(),
                              'claim_id':cid,'original_subject':sid,'existing_kq':kq,'existing_ka':ka,
                              'evidence_refs':';'.join(claim.get('evidence_refs',[])), 'status':status})
                if status!='LIAISON_EXISTANTE':missing.append(links[-1])
    grp=defaultdict(list)
    for s in wikidata_rows:grp[(s['project'],s['topic'])].append(s)
    review=[]
    for t in topic_rows:
        candidates=grp[(t['project'],t['topic'])]
        plausible=[r for r in candidates if r['risk'] not in ('HORS_DOMAINE_PROBABLE','HOMONYMIE')]
        review.append({'project':t['project'],'topic':t['topic'],'claims_count':t['claims_count'],
          'source_file':t['source_file'],'wikidata_candidates':len(candidates),
          'candidates_to_review':len(plausible),
          'qid_to_review':';'.join(s['wikidata_id'] for s in plausible),
          'status':'CANDIDATS_A_ARBITRER' if plausible else 'MODELER_NOTION_LOCALE',
          'note':'Notion documentaire et non KQ certifié; aucun exactMatch automatique'})
    return links,review,missing
