#!/usr/bin/env python3
"""Independently verify UNESCO Wikipedia *research* citations against local dump extracts.

No new dump scan, no remote download, no legal attestation, no KS creation.
A Wikipedia redirect or a mismatched revision/hash must never qualify as context.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
from pathlib import Path
import re

BRANCH='unesco-mt1-10'
REDIRECT=re.compile(r'^\s*#\s*REDIRECT\s*\[\[',re.I)
class ProvenanceError(ValueError):pass

def _json(path:Path,limit=4_000_000):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>limit:raise ProvenanceError('Manifeste local absent/hors limites')
    return json.loads(path.read_text('utf-8-sig'))

def _rows(path:Path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>2_000_000:raise ProvenanceError('References CSV absentes/hors limites')
    r=csv.DictReader(io.StringIO(path.read_text('utf-8-sig'),newline=''))
    rows=list(r)
    if not r.fieldnames or any(None in x or any(v is None for v in x.values()) for x in rows):raise ProvenanceError('CSV invalide')
    return rows

def verify(extract_dir:Path,stage11:Path):
    extract_dir=Path(extract_dir);stage11=Path(stage11)
    m=_json(extract_dir/'manifest.json')
    if m.get('branch')!=BRANCH or m.get('private') is not True or m.get('public_upload_authorized') is not False or m.get('extracted_pages')!=14:
        raise ProvenanceError('Origine de l extraction non conforme')
    pages=m.get('pages')
    if not isinstance(pages,list) or len(pages)!=14:raise ProvenanceError('14 pages locales attendues')
    refs=_rows(stage11/'WIKIPEDIA_16_CONTEXTES_NON_KS.csv')
    if len(refs)!=16:raise ProvenanceError('16 contextes de recherche attendus')
    by_id={};redirects=[];substantive=[]
    for page in pages:
        pid=page.get('page_id');rel=page.get('relative_path')
        if type(pid)!=int or pid in by_id or rel!=f'page-{pid}.wikitext.txt':raise ProvenanceError('Page locale inattendue')
        f=extract_dir/rel
        if not f.is_file() or f.is_symlink() or f.stat().st_size>5_000_000:raise ProvenanceError('Texte local absent ou volume non conforme')
        raw=f.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=page.get('sha256') or len(raw)!=page.get('bytes'):
            raise ProvenanceError('Texte local modifie: '+str(pid))
        first=raw.decode('utf-8-sig').lstrip('\ufeff\n').splitlines()[0] if raw else ''
        is_redirect=bool(REDIRECT.match(first))
        by_id[pid]=page
        (redirects if is_redirect else substantive).append(pid)
    seen=set();checked=[]
    for row in refs:
        try:pid=int(row.get('page_id',''))
        except ValueError:raise ProvenanceError('Identifiant de page invalide')
        page=by_id.get(pid)
        if (not page or pid in redirects or str(page.get('revision_id'))!=str(row.get('revision_id'))
            or row.get('local_text_sha256')!=page.get('sha256')
            or row.get('usage')!='RESEARCH_CONTEXT_ONLY_NOT_KS'
            or row.get('wikipedia_licence_cleared')!='NO'):
            raise ProvenanceError('Reference inadmissible: '+str(row.get('proposal_ref')))
        ref=(row.get('proposal_ref'),row.get('unesco_id'))
        if ref in seen:raise ProvenanceError('Reference de proposition double')
        seen.add(ref)
        checked.append({'proposal_ref':ref[0],'unesco_id':ref[1],'page_id':pid,
            'local_sha256':page.get('sha256'),'revision_id':str(page.get('revision_id')),
            'usage':'PRIVATE_RESEARCH_ONLY_NOT_KS','license_cleared':False})
    leads=_rows(stage11/'FILE_81_SOURCES_A_ATTESTER.csv')
    if len(leads)!=81 or any(x.get('approved_KS')!='NO' for x in leads):
        raise ProvenanceError('Pistes de sources non conformes')
    return {'format':'kristalizer.unesco-mt1-10-local-provenance-audit/1.0','branch':BRANCH,
        'dump_pages_verified':14,'substantive_pages':len(substantive),
        'redirect_pages_excluded':len(redirects),'redirect_page_ids':sorted(redirects),
        'candidate_research_contexts_verified':len(checked),'unique_research_page_ids':len({x['page_id'] for x in checked}),
        'contexts':checked,'source_leads_unattested':len(leads),
        'approved_KS':0,'legal_source_text_attested':False,
        'copyright_redistribution_cleared':False,'canonical_writes':0,
        'publication_authorized':False}
