"""Optional resumable targeted extraction from a line-oriented Wikidata JSON dump.
The local file fingerprint is NOT an authenticated Wikidata source signature.
"""
import bz2,hashlib,json,re
from pathlib import Path
ID=re.compile(rb'"id"\s*:\s*"([QP][1-9][0-9]*)"')
def encoded(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def extract(path,db,wids):
    path=Path(path);st=path.stat();fingerprint={'path':str(path),'size':st.st_size,'mtime_ns':st.st_mtime_ns,'source_authenticated':False};wids=set(wids);keys={x.encode('ascii') for x in wids}
    db.executescript('CREATE TABLE IF NOT EXISTS dump_checkpoint(k TEXT PRIMARY KEY,v TEXT);CREATE TABLE IF NOT EXISTS dump_record(wid TEXT PRIMARY KEY,record_json TEXT);')
    binding=encoded([fingerprint,sorted(wids)]);old=db.execute("SELECT v FROM dump_checkpoint WHERE k='binding'").fetchone()
    if old and old[0]!=binding:raise ValueError('Dump or target set changed; start new run')
    db.execute("INSERT OR IGNORE INTO dump_checkpoint VALUES ('binding',?)",(binding,));db.commit()
    if db.execute("SELECT v FROM dump_checkpoint WHERE k='complete'").fetchone():return fingerprint
    row=db.execute("SELECT v FROM dump_checkpoint WHERE k='offset'").fetchone();offset=int(row[0]) if row else 0
    with bz2.open(path,'rb') as f:
        if offset:f.seek(offset)
        n=0
        while True:
            pos=f.tell();raw=f.readline()
            if not raw:break
            n+=1
            if any(m.group(1) in keys for m in ID.finditer(raw)):
                b=raw.strip().rstrip(b',');d=json.loads(b);wid=d.get('id')
                if wid in wids:
                    if d.get('type')!=('item' if wid.startswith('Q') else 'property'):raise ValueError('Dump type mismatch: '+wid)
                    rev=d.get('lastrevid');labels=d.get('labels',{});aliases=d.get('aliases',{})
                    if type(rev) is not int or rev<=0:raise ValueError('Missing source revision: '+wid)
                    if not isinstance(labels,dict) or not isinstance(aliases,dict):raise ValueError('Unexpected lexical fields')
                    def exact(v,lang):return isinstance(v,dict) and v.get('language')==lang and isinstance(v.get('value'),str)
                    if any(not exact(v,k) for k,v in labels.items()) or any(not isinstance(v,list) or any(not exact(x,k) for x in v) for k,v in aliases.items()):raise ValueError('Malformed lexical record: '+wid)
                    record={'external_id':wid,'source_revision':rev,'labels':labels,'aliases':aliases,'line_sha256':hashlib.sha256(raw).hexdigest(),'uncompressed_offset':pos,'source_authenticated':False,'historical_equivalence_claimed':False}
                    prior=db.execute('SELECT record_json FROM dump_record WHERE wid=?',(wid,)).fetchone();v=encoded(record)
                    if prior and prior[0]!=v:raise ValueError('Duplicate dump identity: '+wid)
                    db.execute('INSERT OR IGNORE INTO dump_record VALUES (?,?)',(wid,v))
            if n%10000==0:
                db.execute("INSERT OR REPLACE INTO dump_checkpoint VALUES ('offset',?)",(str(f.tell()),));db.commit()
                if n%500000==0:print('DUMP LINES THIS SESSION',n,flush=True)
        end=f.tell()
    st2=path.stat()
    if (st.st_size,st.st_mtime_ns)!=(st2.st_size,st2.st_mtime_ns):raise ValueError('Dump changed during scan')
    db.execute("INSERT OR REPLACE INTO dump_checkpoint VALUES ('offset',?)",(str(end),));db.execute("INSERT INTO dump_checkpoint VALUES ('complete','1')");db.commit();return fingerprint
