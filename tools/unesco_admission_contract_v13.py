#!/usr/bin/env python3
"""Read-only validation chaining stage12 unsigned review to Kristalizer's existing gate."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from unesco_global_review_gate import validate

PROFILE='kristalizer.unesco-mt1-10-admission-contract/1.0'

def inspect(work:Path):
    report=validate(work)
    if report.get('status')!='KRISTALIZER_PRIVATE_REVIEW_VALIDATED_CANON_BLOCKED':
        raise ValueError('Etat de revue non reconnu')
    return {'format':PROFILE,'branch':'unesco-mt1-10',
            'unsigned_recommendations_validated':report['reviewed_proposals'],
            'admission_input_kind':report['intake_kind'],
            'canonical_KQ_KP_KA_KS_created':0, 'approved_KS':0,
            'human_decisions_verified':0,'publication_authorized':False,
            'status':'INTEGRITY_PASSED_CONTENT_NOT_ADMITTED'}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',required=True,type=Path)
    a=p.parse_args(argv)
    print(json.dumps(inspect(a.work),ensure_ascii=False,indent=2,sort_keys=True))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as e:
        print('KRISTALIZER V13 BLOQUE: '+str(e),file=sys.stderr);sys.exit(2)
