#!/usr/bin/env python3
"""Kristalizer intake gate for unsigned, *review-only* UNESCO recommendations.

Strictly validates the companion EncyKlopedia stage-12 handoff and never
registers KQ/KP/KA/KS or publishes. The handoff is NOT a Kit v11 input.
"""
from __future__ import annotations
import argparse
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re
import sys

BRANCH='unesco-mt1-10'
DEFAULT_WORK=Path(r'D:\EncyKlopedia\30_working\unesco_mt1_10\autopilot_concept10_puis_41')
FILENAME='RECOMMANDATIONS_85_POUR_KRISTALIZER_NON_CANONIQUES.json'
PROFILE='kristalizer.unesco-mt1-10-unsigned-global-review-handoff/1.0'
REVIEW_MANIFEST='MANIFESTE_OVERLAY_ETAPE12.json'
HEX=re.compile(r'^[0-9a-f]{64}$')

class GateError(ValueError):pass

def sha(p):
 h=sha256()
 with p.open('rb') as s:
  for chunk in iter(lambda:s.read(1048576),b''):h.update(chunk)
 return h.hexdigest()

def read_json(p):
 if not p.is_file() or p.is_symlink():raise GateError('Source absente ou lien: '+str(p))
 return json.loads(p.read_text(encoding='utf-8-sig'))

def read_rows(p):
 if not p.is_file() or p.is_symlink():raise GateError('CSV source absent ou lien: '+str(p))
 return list(csv.DictReader(StringIO(p.read_text(encoding='utf-8-sig'),newline='')))

def validate(work):
 stage12=work/'semantic_stage_v12_revue_chatgpt'
 stage11=work/'semantic_stage_v11_global'
 if stage12.is_symlink() or stage11.is_symlink():raise GateError('Chemins symboliques interdits')
 manifest=read_json(stage12/REVIEW_MANIFEST)
 if manifest.get('format')!='koa.unesco-mt1-10-review-overlay-installation/1.0' or manifest.get('branch')!=BRANCH:
  raise GateError('Manifeste overlay incompatible')
 if manifest.get('canonical_created')!=0 or manifest.get('publication_authorized') is not False:
  raise GateError('Signal de canonisation/publication interdit')
 stage11_manifest=stage11/'MANIFESTE_PASSE_GLOBALE.json'
 if not stage11_manifest.is_file() or sha(stage11_manifest)!=manifest.get('stage11_manifest_sha256'):
  raise GateError('Source globale non ancree')
 expected=manifest.get('files_sha256')
 if not isinstance(expected,dict) or FILENAME not in expected:
  raise GateError('Handoff sans empreinte')
 for name, digest in expected.items():
  p=Path(name)
  if (p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name
      or not isinstance(digest,str) or not HEX.fullmatch(digest)):
   raise GateError('Chemin ou SHA incorrect')
  actual=stage12/p
  if not actual.is_file() or actual.is_symlink() or sha(actual)!=digest:
   raise GateError('Revue deployee modifiee: '+name)
 handoff=read_json(stage12/FILENAME)
 review_file=stage12/'REVUE_85_PROPOSITIONS_NON_SIGNEE.csv'
 review_rows=read_rows(review_file)
 review_by_ref={r['proposal_ref']:r for r in review_rows}
 if len(review_by_ref)!=85 or len(review_rows)!=85:
  raise GateError('Revue 85 candidate non unique')
 if (handoff.get('format')!=PROFILE or handoff.get('branch')!=BRANCH or
   handoff.get('one_branch_kristal') is not True or
   handoff.get('source_stage11_manifest_sha256')!=manifest['stage11_manifest_sha256'] or
   handoff.get('review_manifest_sha256')!=sha(stage12/'MANIFESTE_RECOMMANDATIONS.json') or
   handoff.get('recommendation_count')!=85 or
   handoff.get('human_decisions_written_by_tool')!=0 or
   handoff.get('canonical_identifiers_minted_by_tool')!=0 or
   handoff.get('approved_KS_by_tool')!=0 or
   handoff.get('canon_admission_authorized') is not False or
   handoff.get('publication_authorized') is not False):
  raise GateError('Handoff avec contrat ou controles d admission invalides')
 stage11_proposals=read_rows(stage11/'TABLEAU_85_PROPOSITIONS.csv')
 source={r['proposal_ref']:r for r in stage11_proposals}
 entries=handoff.get('proposals')
 if not isinstance(entries,list) or len(entries)!=85 or len(source)!=85:
  raise GateError('Nombre de propositions inattendu')
 seen=set()
 for e in entries:
  ref=e.get('proposal_ref')
  if ref not in source or ref in seen:
   raise GateError('Reference proposition inconnue/double')
  seen.add(ref)
  original=source[ref]
  if ref not in review_by_ref or e.get('editorial_suggestion_en')!=review_by_ref[ref]['texte_propose_en']:
   raise GateError('Recommandation non concordante avec la revue: '+str(ref))
  if (e.get('unesco_id')!=original['unesco_id'] or
     e.get('statement_original_en')!=original['statement_en'] or
     not isinstance(e.get('editorial_suggestion_en'),str) or not e['editorial_suggestion_en'].strip() or
     e.get('review_status')!='HUMAN_DECISION_REQUIRED' or e.get('not_ks') is not True or
     e.get('canonical_KA') is not None or e.get('canonical_KQ') is not None or
     e.get('canonical_KP') is not None or e.get('canonical_KS')!=[]):
   raise GateError('Assertion candidate incoherente ou canonisee: '+str(ref))
 return {
  'status':'KRISTALIZER_PRIVATE_REVIEW_VALIDATED_CANON_BLOCKED',
  'branch':BRANCH,
  'reviewed_proposals':85,
  'intake_kind':'UNSIGNED_EDITORIAL_RECOMMENDATIONS_NOT_RAW_AI_AND_NOT_KA',
  'canonical_KQ_KP_KA_KS_created':0,
  'approved_KS':0,
  'publication_authorized':False,
  'git_push':False,
 }

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--work',type=Path,default=DEFAULT_WORK)
 args=p.parse_args(argv)
 print(json.dumps(validate(args.work),sort_keys=True,ensure_ascii=False,indent=2))
 return 0

if __name__=='__main__':
 try:sys.exit(main())
 except (OSError,GateError,KeyError,ValueError,UnicodeError,json.JSONDecodeError) as e:
  print('KRISTALIZER GATE BLOQUE: '+str(e),file=sys.stderr)
  sys.exit(2)
