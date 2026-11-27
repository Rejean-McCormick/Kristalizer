"""Read exact-language observations from the compact index. No source authenticity claim."""
import sqlite3,re
from pathlib import Path
from contextlib import closing

def lookup(index, ids):
    p=Path(index); before=p.stat(); result={}
    with closing(sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True)) as c:
        c.row_factory=sqlite3.Row
        cols={r['name'] for r in c.execute('pragma table_info(entity)')}
        if not {'id','wid','kind','label_fr','label_en','description_fr','description_en'}<=cols:raise ValueError('Unsupported compact entity schema')
        # name_kind meaning is not documented in the supplied index contract.
        # Retain raw typed observations, never infer which are aliases.
        names={r['name'] for r in c.execute('pragma table_info(name)')}
        indexed=False
        if {'entity_id','lang','name_kind','value'}<=names:
            for ix in c.execute('pragma index_list(name)'):
                fields=list(c.execute('SELECT name FROM pragma_index_info(?)',(ix['name'],)))
                if fields and fields[0][0]=='entity_id' and not ix['partial']:indexed=True
        for wid in sorted(set(ids)):
            if not re.fullmatch(r'[QP][1-9][0-9]*',wid):continue
            eid=int(wid[1:])+(1000000000 if wid[0]=='P' else 0)
            row=c.execute('SELECT wid,kind,label_fr,label_en,description_fr,description_en FROM entity WHERE id=?',(eid,)).fetchone()
            if not row or row['wid']!=wid:continue
            d=dict(row); d['name_observations']=[];d['name_status']='NO_ENTITY_INDEX' if not indexed else 'RAW_KIND_UNINTERPRETED'
            if indexed:
                d['name_observations']=[list(r) for r in c.execute('SELECT lang,name_kind,value FROM name WHERE entity_id=? ORDER BY 1,2,3',(eid,))]
            result[wid]=d
    after=p.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Compact index changed')
    return result,{'size':before.st_size,'mtime_ns':before.st_mtime_ns,'source_authenticated':False,'names_indexed':indexed}
