"""Read-only explicit migration anchors and native label observations. No approvals."""
import re
LANG=re.compile(r'^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$')
def anchors(doc,namespace,identities):
    if doc.get('namespace_id')!=namespace or doc.get('format')!='dik.bulk-secondpass/2':
        raise ValueError('Migration map scope or format mismatch')
    result={}
    for prefix,kind in [('Q','entity'),('P','property')]:
        for native,sid in doc['by_kind'][prefix].items():
            if identities.get(sid)==kind:
                result.setdefault(native,[]).append(sid)
    # No bridge if the same native string points to more than one target.
    return {n:v[0] for n,v in result.items() if len(set(v))==1}
def labels(row):
    values=[]
    for key in ('label_fr','label_en'):
        values.append((key[-2:],row.get(key),'/'+key))
    ls=row.get('labels')
    if isinstance(ls,list):
        for i,x in enumerate(ls):
            if isinstance(x,dict): values.append((x.get('lang',x.get('language')),x.get('text',x.get('value')),f'/labels/{i}'))
    elif isinstance(ls,dict):
        for lang,val in ls.items():
            if isinstance(val,str): values.append((lang,val,'/labels/'+lang.replace('~','~0').replace('/','~1')))
    return [(l,t,p) for l,t,p in values if isinstance(l,str) and LANG.fullmatch(l) and isinstance(t,str) and t.strip()]
def observations(doc):
    if not isinstance(doc,dict):return
    if doc.get('artifact_type')=='kristall_lexicon':
        for i,row in enumerate(doc.get('entries',[])):
            if not isinstance(row,dict):continue
            ref=row.get('semantic_ref',{})
            lang,term=doc.get('language'),row.get('preferred_term')
            if isinstance(ref,dict) and ref.get('identity_space')=='kristal_v6' and isinstance(ref.get('id'),str) and isinstance(lang,str) and LANG.fullmatch(lang) and isinstance(term,str) and term.strip():
                yield ref['id'],lang,term,f'/entries/{i}/preferred_term','LEGACY_V8'
        return
    # Only a named registry, or the conventional referents.json accepted by caller.
    for i,row in enumerate(doc.get('referents',[])):
        if not isinstance(row,dict):continue
        keys=[row[k] for k in ('ref','id','referent_id') if isinstance(row.get(k),str) and row[k]]
        if len(set(keys))!=1:continue
        for lang,term,p in labels(row):yield keys[0],lang,term,f'/referents/{i}'+p,'NATIVE_REGISTRY'
