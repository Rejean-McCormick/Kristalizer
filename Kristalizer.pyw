"""Interface Windows Tkinter de Kristalizer.
Lancement par double-clic sur LANCER_KRISTALIZER.cmd. Aucun paquet pip requis.
"""
from pathlib import Path
import json, subprocess, sys, threading, queue, os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ROOT=Path(__file__).resolve().parent
CFG=ROOT/'kristalizer-config.json'
LEGACY_CFG=ROOT/'bridge-config.json'
KNOWN_SOURCE=Path(r'C:\mycode\Kristal\Kristal_Drafts\56kristals\KristalsToProcess')
DEFAULT_SOURCE=KNOWN_SOURCE if KNOWN_SOURCE.is_dir() else Path.home()/'Kristals'
DEFAULTS={
  'source':str(DEFAULT_SOURCE),
  'index':r'D:\EncyKlopedia\30_working\wikidata\wikidata.compact.sqlite',
  'output':str(ROOT/'SORTIE'),
  'kit':str(ROOT/'vendor/Kristal-Authoring-Kit/tools/kristal.py'),
  'staging':''}

class Window:
    def __init__(self):
        self.root=tk.Tk();self.root.title('Kristalizer 1.1');self.root.geometry('1040x710');self.root.minsize(790,580)
        conf=dict(DEFAULTS)
        conf_file=CFG if CFG.is_file() else LEGACY_CFG
        if conf_file.is_file():
            try:conf.update({k:v for k,v in json.loads(conf_file.read_text(encoding='utf-8')).items() if k in DEFAULTS})
            except (ValueError,OSError):pass
        if not Path(conf['kit']).is_file():conf['kit']=DEFAULTS['kit']
        self.values={k:tk.StringVar(value=conf[k]) for k in DEFAULTS}
        self.busy=False;self.messages=queue.Queue();self.process=None
        self.header();self.inputs();self.actions();self.console()
        self.root.after(100,self.poll)
        self.root.protocol('WM_DELETE_WINDOW',self.close)

    def header(self):
        top=ttk.Frame(self.root,padding=14);top.pack(fill='x')
        ttk.Label(top,text='KRISTALIZER',font=('Segoe UI',17,'bold')).pack(anchor='w')
        ttk.Label(top,text='Pour un nouveau Kristal ou un ensemble de projets. Aucune écriture dans EncyK ni dans les Kristals source.',
                  wraplength=980).pack(anchor='w',pady=(3,0))

    def inputs(self):
        frame=ttk.LabelFrame(self.root,text='Configuration',padding=10);frame.pack(fill='x',padx=14,pady=4)
        specs=[('source','Kristal(s) — dossier parent ou projet'),('index','Index Wikidata EncyK (SQLite)'),
               ('output','Dossier de sortie et décisions'),('kit','Authoring Kit (tools/kristal.py)'),('staging','Copie de staging à construire')]
        for i,(key,text) in enumerate(specs):
            ttk.Label(frame,text=text).grid(row=i,column=0,sticky='w',pady=4)
            ttk.Entry(frame,textvariable=self.values[key]).grid(row=i,column=1,sticky='ew',padx=8,pady=3)
            ttk.Button(frame,text='...',width=4,command=lambda k=key:self.choose(k)).grid(row=i,column=2)
        frame.columnconfigure(1,weight=1)

    def actions(self):
        outer=ttk.LabelFrame(self.root,text='Parcours simple',padding=12);outer.pack(fill='x',padx=14,pady=9)
        buttons=[('1. Analyser',self.analyse),('2. Préparer les copies',self.stage),
                 ('3. Vérifier et construire',lambda:self.build(False)),('4. Publier et activer',lambda:self.build(True))]
        for i,(name,cb) in enumerate(buttons):
            button=ttk.Button(outer,text=name,command=cb);button.grid(row=0,column=i,sticky='ew',padx=4,pady=3)
            self.__dict__.setdefault('buttons',[]).append(button)
            outer.columnconfigure(i,weight=1)
        ttk.Label(outer,text='Après l’analyse : examiner ANALYSE/DECISIONS.csv. Seules les approbations explicites avec KS valide peuvent entrer dans un nouveau crosswalk.',
                  wraplength=970).grid(row=1,column=0,columnspan=4,sticky='w',pady=8)
        row=ttk.Frame(outer);row.grid(row=2,column=0,columnspan=4,sticky='ew')
        ttk.Button(row,text='Ouvrir la sortie',command=lambda:self.openfolder('output')).pack(side='left',padx=4)
        ttk.Button(row,text='Ouvrir le staging',command=lambda:self.openfolder('staging')).pack(side='left',padx=4)
        ttk.Button(row,text='Importer anciennes décisions',command=self.import_old).pack(side='left',padx=4)
        self.savebutton=ttk.Button(row,text='Sauvegarder les chemins',command=self.save);self.savebutton.pack(side='left',padx=4)
        self.stopbutton=ttk.Button(row,text='Arrêter',command=self.cancel,state='disabled');self.stopbutton.pack(side='right',padx=4)

    def console(self):
        panel=ttk.LabelFrame(self.root,text='Journal d’exécution',padding=8);panel.pack(fill='both',expand=True,padx=14,pady=(0,12))
        self.log=tk.Text(panel,wrap='word',height=13,font=('Consolas',10),state='disabled')
        scroll=ttk.Scrollbar(panel,command=self.log.yview);self.log.config(yscrollcommand=scroll.set)
        self.log.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self.put('Prêt. Commence par « 1. Analyser ».\n')

    def choose(self,key):
        path=self.values[key].get()
        if key in ('index','kit'):chosen=filedialog.askopenfilename(initialdir=str(Path(path).parent))
        else:chosen=filedialog.askdirectory(initialdir=path if Path(path).is_dir() else None)
        if chosen:self.values[key].set(chosen);self.save()

    def save(self):
        CFG.write_text(json.dumps({k:v.get() for k,v in self.values.items()},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        self.put('Configuration enregistrée.\n')

    def put(self,text):
        self.log.configure(state='normal');self.log.insert('end',text);self.log.see('end');self.log.configure(state='disabled')

    def submit(self,params):
        if self.busy:return
        self.save();self.busy=True
        for b in self.buttons:b.config(state='disabled')
        self.stopbutton.config(state='normal')
        self.put('\n> '+ ' '.join(map(str,params)) +'\n')
        def work():
            try:
                creationflags=0x08000000 if os.name=='nt' else 0
                self.process=subprocess.Popen([sys.executable,str(ROOT/'kristalizer.py'),*params],cwd=str(ROOT),
                   stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True,encoding='utf-8',errors='replace',
                   bufsize=1,creationflags=creationflags)
                for line in self.process.stdout:self.messages.put(('line',line))
                code=self.process.wait();self.messages.put(('finish',code))
            except Exception as e:self.messages.put(('error',repr(e)))
        threading.Thread(target=work,daemon=True).start()

    def poll(self):
        try:
            while True:
                action,value=self.messages.get_nowait()
                if action=='line':self.put(value)
                else:
                    self.busy=False;self.process=None
                    for b in self.buttons:b.config(state='normal')
                    self.stopbutton.config(state='disabled')
                    if action=='finish':
                        self.put('FIN : '+('succès' if value==0 else f'erreur (code {value})')+'\n')
                        if value==0:
                            base=Path(self.values['output'].get())/'STAGING'
                            stages=sorted(list(base.glob('*/KRISTALIZER_STAGE_REPORT.json'))+list(base.glob('*/BRIDGE_STAGE_REPORT.json')))
                            if stages:self.values['staging'].set(str(stages[-1].parent))
                    else:self.put('Erreur de lancement: '+value+'\n')
        except queue.Empty:pass
        self.root.after(100,self.poll)

    def analyse(self):
        self.submit(['scan','--source',self.values['source'].get(),'--index',self.values['index'].get(),
                     '--output',self.values['output'].get()])
    def import_old(self):
        filename=filedialog.askopenfilename(title='Choisis l’ancien 02_DECISIONS.csv',filetypes=[('CSV','*.csv')])
        if filename:self.submit(['import-decisions','--file',filename,'--output',self.values['output'].get()])

    def stage(self):
        if messagebox.askyesno('Préparation', 'Créer des copies complètes des Kristals, sans toucher aux originaux ?'):
            self.submit(['stage','--source',self.values['source'].get(),'--output',self.values['output'].get()])
    def build(self,activate):
        staging=self.values['staging'].get()
        if not (Path(staging).joinpath('KRISTALIZER_STAGE_REPORT.json').is_file() or Path(staging).joinpath('BRIDGE_STAGE_REPORT.json').is_file()):
            messagebox.showerror('Staging manquant','Lance « 2. Préparer les copies » ou sélectionne un staging existant.')
            return
        if activate and not messagebox.askyesno('Confirmation','Publier et activer le canal current DANS LES COPIES seulement ?\nLes projets originaux resteront intacts.'):
            return
        self.submit(['build','--staging',staging,'--kit',self.values['kit'].get()] +
                    (['--publish','--activate'] if activate else []))
    def cancel(self):
        if self.process is not None:
            self.process.terminate();self.put('Arrêt demandé. Un build en cours peut laisser une copie partielle dans STAGING.\n')
    def openfolder(self,key):
        path=Path(self.values[key].get())
        if not path.is_dir():messagebox.showinfo('Dossier','Le dossier n’existe pas encore.');return
        if os.name=='nt':os.startfile(str(path))
        else:subprocess.Popen(['xdg-open',str(path)])
    def close(self):
        if self.busy and not messagebox.askyesno('Quitter','Un traitement est en cours. Quitter quand même ?'):return
        self.save();self.root.destroy()

if __name__=='__main__':Window().root.mainloop()
