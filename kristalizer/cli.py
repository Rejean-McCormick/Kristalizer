#!/usr/bin/env python3
"""Kristalizer CLI — scan, stage, build, publish and activate on copies."""
import argparse,json,sys
from pathlib import Path
from kristalizer.core import scan, stage, build, load, import_legacy_decisions

HERE=Path(__file__).resolve().parents[1]
DEFAULT_KIT=HERE/'vendor/Kristal-Authoring-Kit/tools/kristal.py'

def main():
    ap=argparse.ArgumentParser(description='Kristalizer: analyse, staging, build et activation locale non destructifs')
    sub=ap.add_subparsers(dest='action',required=True)
    p=sub.add_parser('scan',help='Lire un dossier de Kristals et proposer KQ/QID, KP/PID')
    p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p.add_argument('--index',default='');p.add_argument('--max-results',type=int,default=8)
    p=sub.add_parser('stage',help='Copier les projets et préparer les crosswalks approuvés')
    p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p=sub.add_parser('build',help='Valider et construire uniquement les copies de staging')
    p.add_argument('--staging',required=True);p.add_argument('--kit',default=str(DEFAULT_KIT))
    p.add_argument('--publish',action='store_true');p.add_argument('--activate',action='store_true')
    p=sub.add_parser('import-decisions',help='Importer ancien 02_DECISIONS.csv sans effacer le nouveau registre')
    p.add_argument('--file',required=True);p.add_argument('--output',required=True)
    p=sub.add_parser('status');p.add_argument('--output',required=True)
    args=ap.parse_args()
    try:
        if args.action=='scan':
            obj=scan(args.source,args.output,args.index,args.max_results)
            print(f"[OK] {obj['projects']} Kristals, {obj['candidates']} candidats; {obj['migration_required']} requièrent une migration v11.")
            print('Index EncyK utilisé:', obj['indexed']['connected'])
        elif args.action=='stage':
            obj=stage(args.source,args.output)
            print('[OK] Copies préparées dans',obj['staging'],'\n',json.dumps(obj['projects'],ensure_ascii=False))
        elif args.action=='build':
            obj=build(args.staging,args.kit,args.publish,args.activate)
            print('[OK]' if obj['failures']==0 else '[ATTENTION]',len(obj['projects']),'projets; erreurs:',obj['failures'])
            for p in obj['projects']: print('   ',p['project'],p['status'],p.get('phase',''))
            if obj['failures']: return 2
        elif args.action=='import-decisions':
            obj=import_legacy_decisions(args.file,args.output)
            print('[OK] Décisions historiques :',json.dumps(obj,ensure_ascii=False))
        elif args.action=='status':
            root=Path(args.output);paths=[root/'ANALYSE/RAPPORT.json']
            paths.extend(sorted(list((root/'STAGING').glob('*/KRISTALIZER_BUILD_REPORT.json')) + list((root/'STAGING').glob('*/BRIDGE_BUILD_REPORT.json')))[-1:]) if (root/'STAGING').is_dir() else None
            for p in paths:
                if p.is_file():print(p,'\n',json.dumps(load(p),ensure_ascii=False,indent=2)[:10000])
                else:print('Pas encore produit:',p)
        return 0
    except Exception as e:
        print('[ERREUR]',type(e).__name__,str(e),file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
