"""Bounded, read-only exact-ID lookups; never decode a Wikidata dump."""
import json, os, re, sqlite3, stat, time
from pathlib import Path
from contextlib import closing
ID=re.compile(r'[QP][1-9][0-9]*\Z')
def need(ok,msg):
    if not ok: raise ValueError(msg)
def safe(p):
    p=Path(p).absolute()
    for q in (*reversed(p.parents),p):
        if q.exists() or q.is_symlink():
            s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'Linked path: '+str(q))
    return p
def ro(p):
    p=safe(p);need(p.is_file(),'Missing DB: '+str(p))
    c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=2);c.execute('PRAGMA query_only=ON');return c
def fingerprint(p):
    p=safe(p);s=p.stat();return {'path':str(p),'size':s.st_size,'mtime_ns':s.st_mtime_ns,'source_authenticated':False}
def stable(p,fp):need(fingerprint(p)==fp,'Source changed: '+str(p))
def columns(c,t):return {r[1]:r for r in c.execute('SELECT * FROM pragma_table_info(?)',(t,))}
def indexed(c,t,col):
    cs=columns(c,t)
    if col in cs and cs[col][5]==1 and sum(bool(r[5]) for r in cs.values())==1:return True
    for ix in c.execute('SELECT * FROM pragma_index_list(?)',(t,)):
        if ix[4]:continue
        f=c.execute('SELECT * FROM pragma_index_info(?)',(ix[1],)).fetchone()
        if f and f[2]==col:return True
    return False
def inspect(p):
    with closing(ro(p)) as c:
        e=columns(c,'entity');n=columns(c,'name')
        if not {'id','wid','kind','label_fr','label_en','description_fr','description_en'}<=set(e):return None
        mode='wid' if indexed(c,'entity','wid') else ('id' if indexed(c,'entity','id') else None)
        if not mode:return None
        return {'lookup':mode,'names_indexed':{'entity_id','lang','name_kind','value'}<=set(n) and indexed(c,'name','entity_id')}
def discover(root):
    root=safe(root);result=[];skipped=[]
    if not root.is_dir():return result,[{'path':str(root),'status':'FAST_DIRECTORY_MISSING'}]
    # Only a bounded directory inventory; never open non-SQLite or unindexed data files.
    count=0
    for current,dirs,fs in os.walk(root,followlinks=False):
        rel=Path(current).relative_to(root);dirs[:]=sorted(d for d in dirs if not d.startswith('.') and len(rel.parts)<2 and not (Path(current)/d).is_symlink() and not getattr((Path(current)/d).lstat(),'st_file_attributes',0)&0x400)
        for f in sorted(fs):
            count+=1
            if count>512:return result,skipped+[{'status':'DISCOVERY_LIMIT_512_FILES'}]
            p=Path(current)/f
            if p.suffix.lower() not in ('.sqlite','.sqlite3','.db'):
                if len(skipped)<40:skipped.append({'path':str(p),'status':'UNSUPPORTED_FILE_FORMAT'})
                continue
            try:
                p=safe(p);s=inspect(p)
                if s:result.append((p,s))
                else:skipped.append({'path':str(p),'status':'UNSUPPORTED_OR_UNINDEXED_SCHEMA'})
            except (OSError,ValueError,sqlite3.Error) as e:skipped.append({'path':str(p),'status':'UNAVAILABLE','reason':str(e)})
            if len(result)>=8:return result,skipped+[{'status':'DISCOVERY_LIMIT_8_DATABASES'}]
    return result,skipped

def query(p,ids,progress=lambda *a:None):
    p=safe(p);fp=fingerprint(p);contract=inspect(p);need(contract,'Unsupported or unindexed entity schema')
    ids=sorted(set(ids));found={};start=time.monotonic()
    with closing(ro(p)) as c:
        c.row_factory=sqlite3.Row
        # No unbounded table scans: each query uses a checked leading index or primary key.
        for i,wid in enumerate(ids,1):
            need(ID.fullmatch(wid),'Invalid target: '+wid)
            mode=contract['lookup'];key=wid if mode=='wid' else int(wid[1:])+(1000000000 if wid[0]=='P' else 0)
            rows=c.execute('SELECT id,wid,kind,label_fr,label_en,description_fr,description_en FROM entity WHERE '+mode+'=? LIMIT 2',(key,)).fetchall()
            if len(rows)==1 and rows[0]['wid']==wid and rows[0]['kind']==('item' if wid[0]=='Q' else 'property'):
                d=dict(rows[0]);eid=d.pop('id');d['name_observations']=[];d['name_status']='NO_ENTITY_INDEX'
                if contract['names_indexed']:
                    d['name_observations']=[list(r) for r in c.execute('SELECT lang,name_kind,value FROM name WHERE entity_id=? ORDER BY 1,2,3',(eid,))];d['name_status']='RAW_KIND_UNINTERPRETED'
                found[wid]=d
            if i%250==0 or i==len(ids):progress(i,len(ids),len(found),time.monotonic()-start)
    stable(p,fp);return found,fp,contract

def recover_partial(p,dump,ids):
    """Copy committed observations, checking the exact checkpoint binding; no source re-decompression."""
    p=safe(p);dump=safe(dump);fp=fingerprint(dump);targets=sorted(set(ids));found={};errors=[]
    with closing(ro(p)) as c:
        ck=dict(c.execute('SELECT k,v FROM dump_checkpoint'));binding=json.loads(ck['binding']);need(binding==[fp,targets],'Partial dump fingerprint or target set mismatch')
        offset=int(ck.get('offset','0'));need(offset>=0,'Invalid checkpoint offset')
        for wid,raw in c.execute('SELECT wid,record_json FROM dump_record ORDER BY wid'):
            try:
                d=json.loads(raw);need(wid in targets and ID.fullmatch(wid) and d['external_id']==wid,'Wrong identity');need(type(d['source_revision']) is int and d['source_revision']>0,'Missing revision');need(type(d['uncompressed_offset']) is int and 0<=d['uncompressed_offset']<offset,'Outside committed checkpoint');need(re.fullmatch('[0-9a-f]{64}',d['line_sha256']),'Bad line digest');need(d['source_authenticated'] is False and d['historical_equivalence_claimed'] is False,'Unexpected authority')
                def exact(x,lang):return isinstance(x,dict) and x.get('language')==lang and isinstance(x.get('value'),str)
                need(isinstance(d['labels'],dict) and all(exact(x,l) for l,x in d['labels'].items()),'Bad labels');need(isinstance(d['aliases'],dict) and all(isinstance(v,list) and all(exact(x,l) for x in v) for l,v in d['aliases'].items()),'Bad aliases');found[wid]=d
            except (KeyError,TypeError,ValueError) as e:errors.append({'wid':wid,'reason':str(e)})
    stable(dump,fp);return found,{'dump_fingerprint':fp,'committed_uncompressed_offset':offset,'checkpoint_complete':ck.get('complete')=='1','invalid_records':errors,'source_lines_rechecked':False}
