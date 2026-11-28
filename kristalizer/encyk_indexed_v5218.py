"""Read-only bridge to the existing EncyK worker. No index construction or fallback scan."""
import gzip, hashlib, json, re, subprocess, sys, time
from pathlib import Path
from .maintenance_fast_v52171 import safe, need, fingerprint

PINS={
 'wikidata_reader_worker.py':'5d0daef24ab1964dc5d5bfc1400a2e6d6959e3bc006e598963cfa00ee56e00a9',
 'vendor/wikidata_skope/fastio.py':'e6bc9a7203ec2f2916db90ba2d991f5b0e920bf06545f849b3adc58583fe8c07',
 'vendor/wikidata_skope/scope_common.py':'67b0c62b79847c294510cb75883b6ff886197aa7cdd93ca1e63b442af2ddbb4e',
 'vendor/wikidata_skope/__init__.py':'e8896b0758a586381eb0068b2a24fbce5225620676fcccbc957297d11790db45',
}
QID=re.compile(r'Q[1-9][0-9]*\Z')
FAST_ID='sha1-c5bfd59f16c6cdf906ead1190d99729108e961be'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(o):return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def load(raw):
    def pairs(items):
        d={}
        for k,v in items:
            need(k not in d,'Duplicate JSON key');d[k]=v
        return d
    def invalid(v):raise ValueError('Non-finite JSON: '+v)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
def check_code(factory):
    factory=safe(factory)
    for rel,h in PINS.items():need(sha(safe(factory/rel))==h,'EncyK code drift: '+rel)
    # vendor is a namespace package in the inspected snapshot.
    need(not (factory/'vendor/__init__.py').exists(),'Unexpected vendor initializer')
def binding(factory,root,dump,index):
    factory,root,dump,index=map(safe,(factory,root,dump,index));check_code(factory)
    need(index==root/'30_working/wikidata/wikidata.compact.sqlite','Unexpected compact path')
    need(dump==root/'10_sources/wikidata/dumps/current/wikidata-20260922-all.json.bz2','Unexpected dump path')
    manifest=safe(root/'20_evidence/manifests/wikidata-dump-verified.json');m=load(manifest.read_bytes().decode('utf-8-sig'))
    need(str(m.get('sha1') or m.get('expected_sha1') or '').lower()==FAST_ID[5:],'Dump descriptor changed')
    name=Path(str(m.get('file') or m.get('filename') or '')).name
    need(not name or name==dump.name,'Manifest file mismatch')
    loc=safe(root/'30_working/wikidata-fast'/FAST_ID/'qid-locator.bin');comp=loc.with_name('compression.bz2blocks.pkl');im=loc.with_name('manifest.json')
    paths=[dump,index,loc,comp,manifest,im]
    need(all(safe(p).is_file() for p in paths),'Missing existing EncyK source or index')
    # Source identity is not cryptographically authenticated; only small manifests/code hashed.
    return {'factory':str(factory),'code_pins':PINS,'files':{str(p):fingerprint(p) for p in paths},'manifest_sha256':sha(manifest),'index_manifest_sha256':sha(im),'dump':str(dump),'compact':str(index),'locator':str(loc),'compression':str(comp),'source_authenticated':False}
def lexical(obj,wid):
    need(isinstance(obj,dict) and obj.get('id')==wid and QID.fullmatch(wid) and obj.get('type')=='item','Entity ID/type mismatch')
    rev=obj.get('lastrevid');need(type(rev) is int and rev>0,'Missing source revision')
    def values(key,multi):
        src=obj.get(key)
        if src is None:return None
        need(isinstance(src,dict),'Bad '+key);out={}
        for lang,value in src.items():
            need(isinstance(lang,str) and bool(lang),'Invalid language');items=value if multi else [value]
            need(isinstance(items,list),'Bad aliases')
            for row in items:need(isinstance(row,dict) and row.get('language')==lang and isinstance(row.get('value'),str),'Language/value mismatch')
            out[lang]=[r['value'] for r in items] if multi else items[0]['value']
        return out
    return {'wid':wid,'revision':rev,'labels':values('labels',False),'aliases':values('aliases',True),'descriptions':values('descriptions',False),'entity_sha256':hashlib.sha256(canonical(obj).encode()).hexdigest(),'source_authenticated':False}
def validate_batch(folder,ids,b):
    folder=safe(folder);ids=set(ids);p=safe(folder/'entities.jsonl.gz');m=load(safe(folder/'entities.jsonl.gz.reader.json').read_bytes())
    need(m['format']=='kristal.wikidata-indexed-reader/1.0' and m['scan_entire_dump'] is False and m['source_modified'] is False,'Worker contract mismatch')
    need(m['backend']['random_access'] is True and m['backend']['backend']=='indexed_bzip2','Not indexed bzip2')
    for key,bkey in [('source_dump','dump'),('index_locator','locator'),('compression_index','compression')]:need(Path(m[key])==Path(b[bkey]),'Worker source mismatch: '+key)
    need(m['requested']==len(ids) and m['sha256']==sha(p),'Worker output digest/scope mismatch')
    out={}
    with gzip.open(p,'rb') as f:
        for raw in f:
            obj=load(raw);wid=obj.get('id');need(wid in ids and wid not in out,'Unexpected or duplicate entity');out[wid]=lexical(obj,wid)
    missing=m['unlocated_qids'];rejected=[r['qid'] for r in m['rejected']]
    need(len(set(missing))==len(missing) and len(set(rejected))==len(rejected),'Duplicate failure ID')
    need(not(set(missing)&set(rejected) or set(missing)&out.keys() or set(rejected)&out.keys()),'Overlapping outcomes')
    need(set(out)|set(missing)|set(rejected)==ids and m['found']==len(out) and m['located']==len(out)+len(rejected),'Incomplete batch accounting')
    return out,{ 'requested':sorted(ids),'found':len(out),'unlocated':sorted(missing),'rejected':m['rejected'],'gzip_sha256':m['sha256'],'worker_manifest_sha256':sha(folder/'entities.jsonl.gz.reader.json')}
def worker(factory,root,dump,index,folder,ids,b,timeout):
    check_code(factory);need(binding(factory,root,dump,index)==b,'Source changed before batch')
    need(all(QID.fullmatch(w) for w in ids),'Worker only supports QIDs')
    req=folder/'request.json';req.write_text(canonical({'qids':ids}),encoding='utf8')
    subprocess.run([sys.executable,'-B',str(factory/'wikidata_reader_worker.py'),'--dump',str(dump),'--index',str(index),'--request',str(req),'--out',str(folder/'entities.jsonl.gz')],cwd=factory,timeout=timeout,check=True)
    need(binding(factory,root,dump,index)==b,'Source changed during batch')
    return validate_batch(folder,ids,b)
