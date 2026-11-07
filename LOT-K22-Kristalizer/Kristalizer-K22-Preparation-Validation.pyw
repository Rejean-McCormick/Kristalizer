# -*- coding: utf-8 -*-
"""KRISTALIZER K22 — interface autonome, copies seulement, aucun publish/activate.
Python 3.10+ avec Tkinter; à placer dans LOT-K22-Kristalizer ou lancer directement.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import traceback
import zipfile

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

NAMES = (
    'Kristal-Accounting',
    'Kristal-Botany',
    'Kristal-Catho',
    'Kristal-Droit-International-Global',
    'Kristal-K-Monetary-System-Socio-Monetary-Transition-Model',
    'Kristal-King-Klown-4-2-0-MEDIA',
    'Kristal-kOA-Ecosystem',
    'Kristal-kOA-Koali-Sales-Pitch',
    'Kristal-Pi-Theory-Prime-Bridge-Spiral-Mirror-Equivariance-Invariant-Regime-Key',
    'Kristal-PiTheory',
    'Kristal-PoliceOps',
    'Kristal-Pouvoirs-Australie',
    'Kristal-Pouvoirs-Canada-Quebec',
    'Kristal-Pouvoirs-Coree-du-Sud',
    'Kristal-Pouvoirs-Finlande',
    'Kristal-Pouvoirs-France',
    'Kristal-Pouvoirs-Japon',
    'Kristal-Pouvoirs-Pays-Bas',
    'Kristal-Power-Topologie-du-pouvoir-Power-Dynamics',
    'Kristal-prime-numbers',
    'Kristal-ScolQc-Education-Quebec',
    'Kristal-VehiculeDiag',
)
assert len(NAMES) == 22 and len({n.casefold() for n in NAMES}) == 22

HERE = Path(__file__).resolve().parent
BASE = HERE.parent if HERE.name.casefold() == 'lot-k50-kristalizer' else Path(r'C:\mycode\Kristal')
DEFAULT_LOT = HERE if HERE.name.casefold() == 'lot-k50-kristalizer' else BASE / 'LOT-K22-Kristalizer'
DEFAULT_SOURCE = BASE / 'locals'
DEFAULT_CLI = BASE / 'Kristalizer' / 'kristalizer.py'
DEFAULT_KIT = BASE / 'Kristal-Authoring-Kit' / 'tools' / 'kristal.py'
DEFAULT_INDEX = Path(r'D:\EncyKlopedia\30_working\wikidata\wikidata.compact.sqlite')


def read_json(path: Path) -> dict:
    with path.open('r', encoding='utf-8-sig') as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError('JSON invalide (objet attendu) : ' + str(path))
    return data


def paths_from_settings(settings: dict) -> dict:
    source = Path(settings['source']).expanduser().resolve()
    lot = Path(settings['lot']).expanduser().resolve()
    cli = Path(settings['cli']).expanduser().resolve()
    kit = Path(settings['kit']).expanduser().resolve()
    index = Path(settings['index']).expanduser().resolve() if settings.get('index', '').strip() else None
    return {'source': source, 'lot': lot, 'cli': cli, 'kit': kit,
            'index': index, 'links': lot / 'LIENS_K22', 'out': lot / 'SORTIE_K22'}


def no_redirect(path: Path) -> None:
    # Une jonction/symlink intermédiaire pourrait rediriger les écritures vers locals.
    physical = os.path.normcase(os.path.abspath(os.path.realpath(path)))
    nominal = os.path.normcase(os.path.abspath(path))
    if physical != nominal:
        raise RuntimeError('Redirection de dossier interdite pour les sorties K22 : ' + str(path))


def validate_base(p: dict) -> None:
    for dest in (p['links'], p['out'], p['out'] / 'STAGING', p['out'] / 'ANALYSE'):
        no_redirect(dest)
        if dest.resolve() == p['source'] or dest.resolve().is_relative_to(p['source']):
            raise RuntimeError('Écriture possible dans locals : ' + str(dest))
    if not p['source'].is_dir():
        raise FileNotFoundError('Dossier locals absent : ' + str(p['source']))
    if not p['cli'].is_file() or p['cli'].name.casefold() != 'kristalizer.py':
        raise FileNotFoundError('Choisir le vrai fichier Kristalizer/kristalizer.py : ' + str(p['cli']))
    if not (p['cli'].parent / 'kristalizer' / 'cli.py').is_file():
        raise FileNotFoundError('Installation Kristalizer incomplète : package kristalizer/cli.py absent.')
    if p['lot'] == p['source'] or p['lot'].is_relative_to(p['source']):
        raise ValueError('Le dossier LOT ne doit pas se trouver dans locals.')
    missing = []
    for name in NAMES:
        q = p['source'] / name
        if not q.is_dir() or not (q / 'kristal.workspace.json').is_file():
            missing.append(str(q))
    if missing:
        raise FileNotFoundError(f'{len(missing)} Kristals absents ou sans kristal.workspace.json :\n' + '\n'.join(missing[:12]))


def validate_kit(p: dict) -> None:
    kit = p['kit']
    if kit.name.casefold() != 'kristal.py' or kit.parent.name.casefold() != 'tools' or not kit.is_file():
        raise FileNotFoundError('Sélectionne le Kit externe : .../Kristal-Authoring-Kit/tools/kristal.py')
    if not (kit.parent.parent / 'VERSION').is_file():
        raise FileNotFoundError('Le dossier Authoring Kit ne contient pas VERSION.')


def link_targets(p: dict, log) -> int:
    """Vérifie l'intégrité des 50 liens; ne remplace ni ne supprime jamais une entrée."""
    root = p['links']
    no_redirect(root)
    if os.path.lexists(root) and (root.is_symlink() or (hasattr(root, 'is_junction') and root.is_junction())):
        raise RuntimeError('LIENS_K22 ne doit pas être lui-même une jonction.')
    root.mkdir(parents=True, exist_ok=True)
    extras = [f.name for f in root.iterdir()
              if f.is_dir() and (f / 'kristal.workspace.json').is_file() and f.name.casefold() not in {n.casefold() for n in NAMES}]
    if extras:
        raise RuntimeError('Autres projets détectés dans LIENS_K22; refus de traiter plus que K22 : ' + ', '.join(extras))
    created = 0
    for i, name in enumerate(NAMES, 1):
        src = p['source'] / name
        dest = root / name
        if os.path.lexists(dest):
            if not dest.is_dir() or not os.path.samefile(src, dest):
                raise RuntimeError('Lien déjà occupé ou pointant ailleurs : ' + str(dest))
            continue
        if os.name != 'nt':
            # Pour essais sur Linux/macOS; sur Windows, de véritables jonctions.
            dest.symlink_to(src, target_is_directory=True)
        else:
            env = os.environ.copy()
            env['KRISTAL_K22_LINK'] = str(dest)
            env['KRISTAL_K22_TARGET'] = str(src)
            # L'environnement évite l'imbrication de guillemets Windows qui a
            # cassé l'ancien lanceur mklink /J.
            command = ("$ErrorActionPreference='Stop'; "
                       "if (!(Test-Path -LiteralPath $env:KRISTAL_K22_TARGET -PathType Container)) "
                       "{ throw 'Source introuvable' }; "
                       "New-Item -ItemType Junction -Path $env:KRISTAL_K22_LINK "
                       "-Target $env:KRISTAL_K22_TARGET -ErrorAction Stop | Out-Null")
            try:
                r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                                    '-Command', command], capture_output=True,
                                   text=True, encoding='utf-8', errors='replace', env=env,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except OSError as exc:
                raise RuntimeError('PowerShell requis pour créer la jonction : ' + str(exc)) from exc
            if r.returncode:
                raise RuntimeError(f'Création jonction {name} : {(r.stderr or r.stdout).strip()}')
        if not dest.is_dir() or not os.path.samefile(src, dest):
            raise RuntimeError('Jonction créée mais incorrecte : ' + str(dest))
        created += 1
        if created == 1 or created % 10 == 0:
            log(f'Liens créés : {created} / 22\n')
    log(f'50/22 chemins vérifiés, {created} nouvelle(s) jonction(s).\n')
    return created


def valid_scan(p: dict) -> bool:
    folder = p['out'] / 'ANALYSE'
    if not (folder / 'DECISIONS.csv').is_file() or not (folder / 'RAPPORT.json').is_file():
        return False
    try:
        report = read_json(folder / 'RAPPORT.json')
        names = {v.get('project') for v in report.get('projects_detail', [])}
        return report.get('projects') == 22 and names == set(NAMES)
    except (OSError, ValueError, TypeError):
        return False


def decisions_summary(p: dict) -> dict:
    path = p['out'] / 'ANALYSE' / 'DECISIONS.csv'
    if not path.is_file():
        return {'pending': 0, 'rejected': 0, 'approved': 0, 'other': 0}
    counter = {'pending': 0, 'rejected': 0, 'approved': 0, 'other': 0}
    with path.open('r', newline='', encoding='utf-8-sig') as handle:
        for row in csv.DictReader(handle):
            state = (row.get('decision') or 'pending').strip().casefold()
            counter[state if state in counter else 'other'] += 1
    return counter


def valid_stage(stage: Path) -> bool:
    try:
        data = read_json(stage / 'KRISTALIZER_STAGE_REPORT.json')
        names = {r.get('project') for r in data.get('projects', [])}
        return len(data.get('projects', [])) == 22 and names == set(NAMES)
    except (OSError, ValueError, TypeError):
        return False


def latest_stage(p: dict) -> Path | None:
    folder = p['out'] / 'STAGING'
    if not folder.is_dir():
        return None
    choices = [q for q in folder.iterdir() if q.is_dir() and valid_stage(q)]
    return max(choices, key=lambda q: q.name) if choices else None


def interpreter() -> str:
    current = Path(sys.executable)
    if os.name == 'nt' and current.name.casefold() == 'pythonw.exe':
        console = current.with_name('python.exe')
        if console.is_file():
            return str(console)
    return sys.executable


def report_zip(p: dict, staging: Path | None, history: list[str], error: str = '') -> tuple[Path, dict]:
    """Export reports only: no originals, no staged canonical data."""
    p['lot'].mkdir(parents=True, exist_ok=True)
    dest = p['lot'] / 'RAPPORT_BUILD_K22_A_ENVOYER.zip'
    stage_obj = read_json(staging / 'KRISTALIZER_STAGE_REPORT.json') if staging and (staging / 'KRISTALIZER_STAGE_REPORT.json').is_file() else {}
    build_obj = read_json(staging / 'KRISTALIZER_BUILD_REPORT.json') if staging and (staging / 'KRISTALIZER_BUILD_REPORT.json').is_file() else {}
    stage_by = {row.get('project'):row for row in stage_obj.get('projects', [])}
    build_by = {row.get('project'):row for row in build_obj.get('projects', [])}
    statuses = {}
    rows = []
    for name in NAMES:
        s, b = stage_by.get(name, {}), build_by.get(name, {})
        status = b.get('status') or s.get('status') or 'PAS_TRAITE'
        statuses[status] = statuses.get(status, 0) + 1
        rows.append({'Kristal': name, 'Chemin_source': str(p['source'] / name),
                     'Etat_stage': s.get('status',''), 'Etat_build': b.get('status',''),
                     'Phase': b.get('phase',''), 'Erreur': b.get('error','')})
    from io import StringIO
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]), delimiter=';')
    writer.writeheader()
    writer.writerows(rows)
    lines = ['RAPPORT K22 — COPIES STAGING ET BUILD (SANS PUBLICATION)',
             'Date UTC : ' + dt.datetime.now(dt.timezone.utc).isoformat(),
             'Originaux intacts : le traitement cible exclusivement STAGING.',
             'Ne certifie pas Framework C1/C2/C3; aucune validation Wikidata automatique.',
             'Staging : ' + (str(staging) if staging else 'non généré'),
             'Résultats : ' + ', '.join(f'{v} {k}' for k,v in sorted(statuses.items())),
             'Échecs de build : ' + str(build_obj.get('failures', 'pas de rapport')),
             'Erreur d\'orchestration : ' + (error or 'aucune'),
             'Envoyer ce ZIP directement à ChatGPT.', '']
    temp = dest.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('RESUME.txt', '\n'.join(lines).encode('utf-8-sig'))
        z.writestr('RESULTATS_K22.csv', buf.getvalue().encode('utf-8-sig'))
        z.writestr('JOURNAL_K22.txt', ''.join(history).encode('utf-8-sig'))
        scan = p['out'] / 'ANALYSE' / 'RAPPORT.json'
        if scan.is_file(): z.write(scan, 'ANALYSE/RAPPORT.json')
        if staging:
            for fname in ['KRISTALIZER_STAGE_REPORT.json','KRISTALIZER_BUILD_REPORT.json','ECHEC_STAGE.json']:
                source = staging / fname
                if source.is_file():z.write(source, 'STAGING/' + fname)
    temp.replace(dest)
    return dest, statuses


class K22UI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Kristalizer K22 — Préparer et vérifier les 22 copies')
        self.root.geometry('1050x760')
        self.root.minsize(820,620)
        self.events = queue.Queue()
        self.busy = False
        self.proc = None
        self.cancel_requested = threading.Event()
        self.history: list[str] = []
        self.last_stage: Path | None = None
        self.controls: list[ttk.Button] = []
        self.status = tk.StringVar(value='Prêt — 22 Kristals, 0 originaux modifiés')
        self.vars = {k:tk.StringVar(value=v) for k,v in {
            'source': str(DEFAULT_SOURCE), 'lot': str(DEFAULT_LOT),
            'cli': str(DEFAULT_CLI), 'kit': str(DEFAULT_KIT),
            'index': str(DEFAULT_INDEX), 'staging': ''}.items()}
        self.build_ui()
        try:
            p=paths_from_settings(self.settings())
            if latest_stage(p):
                self.vars['staging'].set(str(latest_stage(p)))
        except Exception:pass
        self.root.after(120, self.poll)
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def build_ui(self):
        top=ttk.Frame(self.root, padding=(16,14,16,9));top.pack(fill='x')
        ttk.Label(top,text='KRISTALIZER  ·  LOT K22',font=('Segoe UI',17,'bold')).pack(anchor='w')
        ttk.Label(top,text='Une seule interface : vérifier les 50 dossiers, préparer les copies v11, lancer le Kit et exporter le rapport. Aucun GitHub, aucune activation.',
                  wraplength=970).pack(anchor='w',pady=(3,0))
        options=ttk.LabelFrame(self.root,text='Chemins de travail',padding=11);options.pack(fill='x',padx=16,pady=(0,8))
        fields=[('source','Kristals originaux (locals)','dir'),('lot','Dossier du lot K22','dir'),
                ('cli','Kristalizer — kristalizer.py','file'),('kit','Kit — tools/kristal.py','file'),
                ('index','Index EncyK (facultatif pour analyse)','file'),
                ('staging','Copie STAGING (choisie après préparation)','dir')]
        for r,(key,label,kind) in enumerate(fields):
            ttk.Label(options,text=label).grid(row=r,column=0,sticky='w',pady=3)
            ttk.Entry(options,textvariable=self.vars[key]).grid(row=r,column=1,sticky='ew',padx=(10,6),pady=3)
            ttk.Button(options,text='...',width=4,command=lambda k=key,t=kind:self.choose(k,t)).grid(row=r,column=2)
        options.columnconfigure(1,weight=1)
        flow=ttk.LabelFrame(self.root,text='Traitement',padding=10);flow.pack(fill='x',padx=16,pady=3)
        row=ttk.Frame(flow);row.pack(fill='x')
        self.make_button(row,'Vérifier les 22 chemins','check')
        self.make_button(row,'Analyser si nécessaire','scan')
        self.make_button(row,'2. Préparer les copies','stage')
        self.make_button(row,'3. Vérifier + construire','build')
        self.make_button(row,'Exporter le ZIP','export')
        primary=ttk.Frame(flow);primary.pack(fill='x',pady=(9,4))
        self.make_button(primary,'LANCER LE LOT COMPLET  ·  COPIES + BUILD + ZIP','all',style='Accent.TButton')
        self.stopbutton=ttk.Button(primary,text='Arrêter',command=self.stop,state='disabled')
        self.stopbutton.pack(side='right',padx=4)
        ttk.Label(flow,text='Le lot complet réutilise le scan existant, sinon lance « scan ». Les 22 migrations manuelles restent signalées, pas inventées. Aucun « Publier et activer ».',
                  wraplength=980).pack(anchor='w',pady=(4,1))
        bar=ttk.Frame(self.root,padding=(16,6,16,0));bar.pack(fill='x')
        ttk.Label(bar,textvariable=self.status).pack(side='left')
        self.progress=ttk.Progressbar(bar,mode='indeterminate',length=200)
        self.progress.pack(side='right')
        frame=ttk.LabelFrame(self.root,text='Journal d’exécution',padding=8);frame.pack(fill='both',expand=True,padx=16,pady=(6,9))
        self.logbox=tk.Text(frame,wrap='word',font=('Consolas',10),state='disabled',undo=False)
        scroll=ttk.Scrollbar(frame,orient='vertical',command=self.logbox.yview)
        self.logbox.configure(yscrollcommand=scroll.set)
        self.logbox.pack(side='left',fill='both',expand=True)
        scroll.pack(side='right',fill='y')
        bottom=ttk.Frame(self.root,padding=(16,0,16,12));bottom.pack(fill='x')
        ttk.Button(bottom,text='Ouvrir le dossier du lot',command=lambda:self.open_folder('lot')).pack(side='left')
        ttk.Button(bottom,text='Ouvrir les rapports STAGING',command=lambda:self.open_folder('staging')).pack(side='left',padx=8)
        ttk.Label(bottom,text='Lecture des sources, écriture uniquement dans le dossier du lot / STAGING.',foreground='#586575').pack(side='right')
        self.append('Prêt. Utilise « LANCER LE LOT COMPLET » pour effectuer les étapes 2 et 3 et produire le ZIP.\n')

    def make_button(self, row, label, mode, style=None):
        kwargs={'style':style} if style else {}
        b=ttk.Button(row,text=label,command=lambda m=mode:self.start(m),**kwargs)
        b.pack(side='left',padx=4,pady=2)
        self.controls.append(b)

    def append(self,message):
        self.logbox.configure(state='normal')
        self.logbox.insert('end',message)
        self.logbox.see('end')
        self.logbox.configure(state='disabled')

    def choose(self,key,kind):
        current=self.vars[key].get()
        if kind=='dir':
            result=filedialog.askdirectory(initialdir=current if Path(current).is_dir() else str(Path(current).parent))
        else:
            result=filedialog.askopenfilename(initialdir=str(Path(current).parent))
        if result:self.vars[key].set(result)

    def settings(self) -> dict:
        return {k:self.vars[k].get().strip() for k in ('source','lot','cli','kit','index')}

    def emit(self, text):
        stamp = dt.datetime.now().strftime('%H:%M:%S')
        message=f'[{stamp}] {text}'
        self.history.append(message)
        self.events.put(('log', message))

    def set_status(self, text):
        self.events.put(('status', text))

    def run_cmd(self, argv: list[str], cwd: Path, label: str) -> None:
        if self.cancel_requested.is_set(): raise InterruptedError('Arrêt demandé.')
        self.set_status(label)
        self.emit(f'{label}\n> '+subprocess.list2cmdline(argv)+'\n')
        env=os.environ.copy()
        env.update({'PYTHONIOENCODING':'utf-8:replace','PYTHONUTF8':'1',
                    'PYTHONUNBUFFERED':'1','KRISTALIZER_UTF8':'1'})
        proc=subprocess.Popen(argv,cwd=str(cwd),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
              text=True,encoding='utf-8',errors='replace',bufsize=1,env=env,
              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.proc=proc
        try:
            for line in proc.stdout:
                self.emit(line)
            rc=proc.wait()
        finally:
            self.proc=None
        if self.cancel_requested.is_set(): raise InterruptedError('Arrêt demandé; aucune phase suivante lancée.')
        if rc:
            raise RuntimeError(f'{label} : commande échouée (code {rc}). Voir journal et rapport ZIP.')
        self.emit(f'[OK] {label}\n')

    def command(self, p: dict, *args: str) -> list[str]:
        return [interpreter(),str(p['cli']),*args]

    def ensure_links(self,p):
        self.set_status('Création / contrôle des jonctions K22…')
        self.emit('Vérification des 22 workspaces originaux…\n')
        validate_base(p)
        link_targets(p, lambda s:self.emit(s))

    def scan(self,p,force=False):
        if valid_scan(p) and not force:
            self.emit('Scan K22 existant cohérent : réutilisé sans recommencer.\n')
            return
        self.ensure_links(p)
        cmd=self.command(p,'scan','--source',str(p['links']),'--output',str(p['out']))
        if p['index'] and p['index'].is_file():cmd.extend(['--index',str(p['index'])])
        else:self.emit('Index EncyK absent : scan local sans index Wikidata.\n')
        self.run_cmd(cmd,p['cli'].parent,'Étape 1 — Analyse K22')
        if not valid_scan(p):raise RuntimeError('Le scan ne correspond pas exactement aux 22 Kristals attendus.')

    def stage(self,p):
        # Ne jamais réutiliser un ancien staging si cette tentative échoue.
        self.last_stage=None
        self.ensure_links(p)
        self.scan(p)
        stats=decisions_summary(p)
        self.emit('Décisions Wikidata : ' + ', '.join(f'{k}={v}' for k,v in stats.items())+'\n')
        if stats['approved']:
            raise RuntimeError(f'{stats["approved"]} correspondance(s) Wikidata déjà approuvée(s) : arrêt préventif. '
                               'Ce lot automatique ne promeut aucune identité; désapprouver ou traiter ces décisions séparément.')
        if stats['other']:
            raise RuntimeError('Statuts de décisions inconnus : arrêt préventif.')
        old={s.name for s in (p['out']/'STAGING').iterdir()} if (p['out']/'STAGING').is_dir() else set()
        self.run_cmd(self.command(p,'stage','--source',str(p['links']),'--output',str(p['out'])),
                     p['cli'].parent,'Étape 2 — Préparer les copies (50)')
        new=latest_stage(p)
        if not new or new.name in old or not valid_stage(new):
            raise RuntimeError('Le rapport de staging attendu est absent ou ne concerne pas les 22 projets.')
        self.last_stage=new
        self.events.put(('staging',str(new)))
        report=read_json(new/'KRISTALIZER_STAGE_REPORT.json')
        counts={}
        for rec in report.get('projects',[]):
            key=rec.get('status','INCONNU');counts[key]=counts.get(key,0)+1
        self.emit('COPIES PRÊTES : ' + ', '.join(f'{v} {k}' for k,v in counts.items())+'\n')
        return new

    def build(self,p,staging:Path):
        validate_kit(p)
        validate_base(p)
        no_redirect(staging)
        staging=staging.resolve()
        if not valid_stage(staging):raise RuntimeError('Staging sélectionné invalide ou incomplet : '+str(staging))
        if not staging.is_relative_to((p['out']/'STAGING').resolve()):
            raise RuntimeError('Le staging doit se trouver dans SORTIE_K22/STAGING, hors des originaux.')
        for name in NAMES:
            no_redirect(staging / name)
        self.last_stage=staging
        self.run_cmd(self.command(p,'kit-status','--kit',str(p['kit'])),p['cli'].parent,
                     'Contrôle du Kit externe')
        # Intentionnellement sans --publish / --activate.
        self.run_cmd(self.command(p,'build','--staging',str(staging),'--kit',str(p['kit'])),
                     p['cli'].parent,'Étape 3 — Vérifier et construire les COPIES')
        self.emit('Aucune publication, aucune activation, aucun GitHub.\n')

    def export(self,p,staging:Path|None,error=''):
        self.set_status('Création du ZIP des rapports…')
        dest, stats=report_zip(p,staging,self.history,error)
        self.emit('[RAPPORT] '+str(dest)+'\n')
        self.emit('RÉSUMÉ : '+', '.join(f'{k}={v}' for k,v in sorted(stats.items()))+'\n')
        self.events.put(('zip',str(dest)))
        return dest

    def worker(self,mode:str,settings:dict,staging_path:str):
        p=None
        error=''
        staged=None
        before_stages=set()
        try:
            p=paths_from_settings(settings)
            if mode in ('all','stage'):
                validate_base(p)
                stage_parent=p['out']/'STAGING'
                before_stages={x.name for x in stage_parent.iterdir() if x.is_dir()} if stage_parent.is_dir() else set()
                self.stage(p)
                staged=self.last_stage
            elif mode in ('scan','check'):
                validate_base(p)
                if mode=='scan': self.scan(p,force=True)
                else:
                    self.emit('Chemins des 22 Kristals valides.\n')
                    self.emit('Scan disponible : '+str(valid_scan(p))+'\n')
                    self.emit('Dernier staging : '+str(latest_stage(p))+'\n')
            elif mode in ('build','export'):
                staged=Path(staging_path).expanduser().resolve() if staging_path.strip() else latest_stage(p)
                if mode=='build':
                    if not staged:raise RuntimeError('Staging absent : lance d’abord « Préparer les copies ».')
                    self.build(p,staged)
            else:raise ValueError('Action non reconnue')
            if mode=='all':
                self.build(p,staged)
                self.export(p,staged)
            elif mode=='export':self.export(p,staged)
            elif mode=='build':self.export(p,staged)
            self.events.put(('done',('ok',mode)))
        except Exception as exc:
            error = f'{type(exc).__name__} : {exc}'
            self.emit('[ERREUR] '+error+'\n')
            # Exporter un rapport même si un ou plusieurs projets ont échoué.
            if p and mode in ('all','stage','build'):
                try:
                    if not staged and mode in ('all','stage'):
                        stage_parent=p['out']/'STAGING'
                        if stage_parent.is_dir():
                            new_dirs=[x for x in stage_parent.iterdir() if x.is_dir() and x.name not in before_stages]
                            if new_dirs:staged=max(new_dirs,key=lambda x:x.name)
                    staged = staged or self.last_stage
                    self.export(p,staged,error)
                except Exception as export_exc:
                    self.emit('[EXPORT ÉCHOUÉ] '+str(export_exc)+'\n')
            self.events.put(('done',('error',error)))

    def start(self,mode):
        if self.busy:return
        if mode in ('all','stage'):
            if not messagebox.askokcancel('Copies K22 — confirmation',
                    'Kristalizer va copier les 50 dossiers vers SORTIE_K22/STAGING.\n'
                    'Cela peut demander beaucoup d’espace disque.\n\n'
                    'Les originaux ne sont pas modifiés. Aucun GitHub, aucune publication, aucune activation.\n\nContinuer ?'):
                return
        self.busy=True
        self.history=[]
        self.cancel_requested.clear()
        for b in self.controls:b.configure(state='disabled')
        self.stopbutton.configure(state='normal')
        self.progress.start(12)
        threading.Thread(target=self.worker,args=(mode,self.settings(),self.vars['staging'].get()),daemon=True).start()

    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='log':self.append(value)
                elif kind=='status':self.status.set(value)
                elif kind=='staging':self.vars['staging'].set(value)
                elif kind=='zip':
                    self.latest_zip=value
                elif kind=='done':
                    self.busy=False
                    self.progress.stop()
                    self.stopbutton.configure(state='disabled')
                    for b in self.controls:b.configure(state='normal')
                    state,payload=value
                    if state=='ok':
                        self.status.set('Terminé — aucune activation des originaux')
                        if payload=='all':
                            messagebox.showinfo('Lot K22 terminé', 'Traitement terminé.\n\nZIP à envoyer :\n'+str(getattr(self,'latest_zip','(non disponible)')))
                    else:
                        self.status.set('Échec — consulter le journal et le rapport ZIP')
                        messagebox.showerror('Traitement incomplet',str(payload)[:1400]+'\n\nLe ZIP de diagnostic, s’il a pu être créé, se trouve dans le dossier LOT-K22-Kristalizer.')
        except queue.Empty:pass
        self.root.after(120,self.poll)

    def stop(self):
        if not self.busy:return
        if not messagebox.askyesno('Arrêter', 'Arrêter le traitement ?\nLes copies partielles de STAGING seront conservées pour diagnostic.'):return
        self.cancel_requested.set()
        proc=self.proc
        if proc and proc.poll() is None:
            try:proc.terminate()
            except OSError:pass
        self.append('Arrêt demandé; ne pas utiliser le staging incomplet.\n')

    def open_folder(self,key):
        path=Path(self.vars[key].get()) if self.vars[key].get().strip() else None
        if not path or not path.is_dir():
            messagebox.showinfo('Dossier','Dossier inexistant ou non sélectionné.')
            return
        if os.name=='nt':os.startfile(str(path))
        else:subprocess.Popen(['xdg-open',str(path)])

    def close(self):
        if self.busy:
            messagebox.showwarning('Traitement en cours','Arrête le traitement avant de quitter afin de conserver un rapport fiable.')
            return
        self.root.destroy()


if __name__ == '__main__':
    try:
        app=K22UI()
        app.root.mainloop()
    except Exception as error:
        # pythonw.exe ne possède pas toujours de console pour afficher le traceback.
        try:
            tk.messagebox.showerror('Erreur de démarrage K22',f'{type(error).__name__}: {error}\n\n{traceback.format_exc()[-1000:]}')
        except Exception:pass
        raise
