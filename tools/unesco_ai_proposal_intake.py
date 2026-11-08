"""Review-only AI/Wikimedia/UNESCO proposals intake for one branch Kristal.

AI model training/knowledge may suggest claims but is NOT a source KS. URLs,
Wikidata candidate QIDs and raw Wikipedia wikitext are NOT automatic factual
approvals. All proposals stay unminted and unapproved pending evidence review.
"""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from pathlib import Path
PROFILE='kristalizer.unesco-mt1-10-ai-claim-candidates/1.0'
class ProposalError(ValueError):pass

def _sha(b):return hashlib.sha256(b).hexdigest()

def read(path,max_bytes=9_000_000):
    if not path.is_file() or path.stat().st_size>max_bytes:raise ProposalError('Missing/oversized local JSON source')
    b=path.read_bytes();return json.loads(b),_sha(b)

def accept(dossier:dict,proposals:dict,*,dossier_sha256:str):
    if (dossier.get('profile')!='skope.unesco-mt1-10-local-source-dossier/1.0' or dossier.get('branch')!='unesco-mt1-10' or
        dossier.get('private') is not True or dossier.get('not_canonical') is not True or
        dossier.get('public_upload_authorized') is not False):
        raise ProposalError('Wrong or unsafe source dossier')
    if (proposals.get('format')!='kristalizer.unesco-mt1-10-raw-ai-proposals/1.0' or
        proposals.get('branch')!='unesco-mt1-10' or proposals.get('dossier_sha256')!=dossier_sha256):
        raise ProposalError('Proposals do not match exact local dossier digest')
    entries=dossier.get('entries')
    if not isinstance(entries,list) or len(entries)!=41:raise ProposalError('Expected 41 UNESCO concepts')
    concepts={r['unesco_id']:r for r in entries}
    raw=proposals.get('proposals')
    if not isinstance(raw,list):raise ProposalError('Proposals array required')
    if len(raw)>500:raise ProposalError('Candidate batch too large')
    prepared=[];seen=set()
    for p in raw:
        if not isinstance(p,dict):raise ProposalError('Bad candidate entry')
        rid=p.get('proposal_ref');cid=p.get('unesco_id')
        if not isinstance(rid,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,100}',rid) or rid in seen:
            raise ProposalError('Invalid/duplicate proposal_ref')
        seen.add(rid)
        if cid not in concepts:raise ProposalError('Proposed UNESCO ID outside one branch')
        text=p.get('statement_text');model=p.get('model_id');gen=p.get('generation_ref')
        if not isinstance(text,str) or not text.strip() or len(text)>10_000:
            raise ProposalError('Missing/bounded statement text')
        if not isinstance(model,str) or not model.strip() or not isinstance(gen,str) or not gen.strip():
            raise ProposalError('Actual AI model/generation provenance required')
        evidence=p.get('evidence_refs',[])
        if not isinstance(evidence,list) or len(evidence)>30:raise ProposalError('Evidence list invalid')
        contexts=[]
        for e in evidence:
            if not isinstance(e,dict):raise ProposalError('Bad evidence pointer')
            typ=e.get('source_type')
            if typ=='unesco':
                if e.get('uri')!=concepts[cid].get('unesco_source_uri'):
                    raise ProposalError('UNESCO URI does not belong to selected concept')
                contexts.append({'source_type':'unesco','uri':e['uri'],'verified_as':'LOCAL_POINTER_ONLY'})
            elif typ=='wikipedia_en':
                match=[q['local_text'] for q in concepts[cid].get('wikipedia_en',[]) if
                       q['page_id']==e.get('page_id') and q.get('local_text')]
                if not match or match[0].get('text_sha256')!=e.get('sha256'):
                    raise ProposalError('Wikimedia article text digest/page ID does not match dossier')
                source=match[0]
                excerpt=source.get('context_excerpt_unverified')
                if (source.get('mediawiki_redirect') is True or
                    (isinstance(excerpt,str) and re.match(r'^\ufeff?\s*#\s*redirect\b\s*:?\s*\[\[',excerpt,re.I))):
                    raise ProposalError('MediaWiki redirect cannot support an AI factual proposal')
                if (source.get('ai_context_eligible') is not True or
                    source.get('source_integrity_status')!='CANDIDATE_MATCHED' or
                    source.get('title_agrees') is not True or
                    source.get('revision_agrees') is not True):
                    raise ProposalError('Wikimedia text is mismatched and ineligible as AI research context')
                if (source.get('revision_id') is None or
                    str(source['revision_id'])!=str(e.get('revision_id'))):
                    raise ProposalError('Exact Wikipedia revision ID must accompany the text SHA-256')
                contexts.append({'source_type':'wikipedia_en','page_id':e['page_id'],
                                 'revision_id':source['revision_id'], 'sha256':e['sha256'],
                                 'verified_as':'LOCAL_TEXT_IDENTITY_ONLY'})
            else:
                raise ProposalError('Unknown evidence pointer; a QID is not a KS')
        prepared.append({'proposal_ref':rid,'unesco_id':cid,'text_candidate':text,
                         'model_id':model,'generation_ref':gen,
                         'research_context_refs':contexts,'local_research_context_count':len(contexts),
                         'canonical_KA':None,'canonical_KS':[],
                         'epistemic_status':'AI_CANDIDATE_NOT_ASSERTION',
                         'review_status':'PENDING','source_validation':'PENDING',
                         'copyright_review':'PENDING'})
    return {'profile':PROFILE,'branch':'unesco-mt1-10','one_branch_kristal':True,
            'source_dossier_sha256':dossier_sha256,'proposed_count':len(prepared),
            'canonical_assertions_minted':0,'proposals':prepared,'not_canonical':True,
            'publication_authorized':False,'unreviewed_ai_proposals':True}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dossier',type=Path,required=True)
    p.add_argument('--proposals',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        d,sha=read(a.dossier);p,_=read(a.proposals)
        result=accept(d,p,dossier_sha256=sha)
        if a.out.exists() or any((p/'.git').exists() for p in a.out.resolve().parents):
            raise ProposalError('New output outside Git required')
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
        print(json.dumps({'status':'PRIVATE_AI_CANDIDATES','count':result['proposed_count'],
                          'canonical_assertions_minted':0,'publication':'BLOCKED','out':str(a.out)}));return 0
    except (ProposalError,ValueError,KeyError,TypeError,OSError) as e:
        print(json.dumps({'status':'BLOCKED','error':str(e)}),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
