"""Tests offline, sans EncyK réel ni Kristal existant."""
import csv, hashlib, json, sqlite3, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kristalizer.core import scan, stage, discover, load, read_csv, EncyIndex, import_legacy_decisions


def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')

class KristalizerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.src=self.root/'input';self.proj=self.src/'Kristal-Futur'
        self.proj.mkdir(parents=True)
        write(self.proj/'kristal.workspace.json',{'slug':'futur'})
        reg={'artifact_type':'kristal_identity_registry','schema_version':'11.0','namespace_id':'urn:kristal:futur',
             'registry_id':'r','identities':[{'id':'KQ100','kind':'entity','status':'stable'},
                                           {'id':'KP100','kind':'property','status':'stable'},
                                           {'id':'KS100','kind':'source','status':'stable'}]}
        graph={'artifact_type':'kristal_semantic_graph','schema_version':'11.0','namespace_id':'urn:kristal:futur',
             'graph_id':'g','entities':['KQ100'],'properties':['KP100'],'sources':['KS100'],'assertions':[]}
        cross={'artifact_type':'kristal_external_crosswalk','schema_version':'11.0','crosswalk_id':'c','mappings':[]}
        words={'artifact_type':'kristal_curated_dictionary','schema_version':'11.0',
               'namespace_id':'urn:kristal:futur','language':'fr','entries':[{'semantic_id':'KQ100','preferred_term':'stratosphère'},
                                                                           {'semantic_id':'KP100','preferred_term':'partie de'}]}
        p=self.proj/'.kristal/v11';write(p/'identity-registry.json',reg)
        write(p/'semantic-graph.json',graph);write(p/'external-crosswalk.json',cross)
        write(p/'dictionaries/fr.json',words)
        checksum=hashlib.sha256((p/'dictionaries/fr.json').read_bytes()).hexdigest()
        write(p/'dictionaries/catalog.json',{'artifact_type':'kristal_dictionary_catalog',
          'schema_version':'11.0','namespace_id':'urn:kristal:futur','catalog_id':'l',
          'languages':[{'tag':'fr','fallbacks':[],'layers':[{'kind':'curated','layer_id':'fr','path':'fr.json','priority':90,'sha256':checksum}]}]})
        self.index=self.root/'index.sqlite'
        con=sqlite3.connect(self.index)
        con.executescript('CREATE TABLE entity(id INTEGER PRIMARY KEY,wid TEXT,kind TEXT,label_fr TEXT,label_en TEXT,description_fr TEXT,description_en TEXT);'
                          'CREATE TABLE name(entity_id INTEGER,lang TEXT,name_kind INTEGER,value TEXT,norm TEXT);'
                          'CREATE INDEX idx_name_norm ON name(norm);')
        con.execute('INSERT INTO entity VALUES(100,?,?,?,?,?,?)',('Q100','item','stratosphère','stratosphere','couche atmosphérique','atmospheric layer'))
        con.execute('INSERT INTO name VALUES(100,?,?,?,?)',('fr',0,'stratosphère','stratosphere'))
        con.commit();con.close()
        self.out=self.root/'output'

    def test_discover_one_and_many(self):
        self.assertEqual(discover(self.proj),[self.proj])
        self.assertEqual(discover(self.src),[self.proj])

    def test_scan_without_skope_and_preserve_decision(self):
        r=scan(self.src,self.out,self.index)
        self.assertEqual(r['projects'],1);self.assertTrue(r['indexed']['name_search_available']);self.assertEqual(r['candidates'],1)
        rows=read_csv(self.out/'ANALYSE/CANDIDATS.csv');self.assertEqual(rows[0]['external_id'],'Q100')
        decisions=self.out/'ANALYSE/DECISIONS.csv'
        d=read_csv(decisions);d[0]['decision']='rejected';d[0]['reviewer']='audit'
        with decisions.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=d[0]);w.writeheader();w.writerows(d)
        scan(self.src,self.out,self.index)
        self.assertEqual(read_csv(decisions)[0]['decision'],'rejected')

    def test_staging_revised_crosswalk_preserves_source(self):
        scan(self.src,self.out,self.index)
        decisions=self.out/'ANALYSE/DECISIONS.csv';rs=read_csv(decisions)
        rs[0].update(decision='approved',reviewer='expert',reason='test de provenance externe',evidence_refs='KS100')
        with decisions.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=rs[0]);w.writeheader();w.writerows(rs)
        report=stage(self.src,self.out)
        path=Path(report['staging'])/self.proj.name
        self.assertTrue((path/'KRISTALIZER_PENDING_ACTIVATION.json').exists())
        self.assertFalse((self.proj/'KRISTALIZER_PENDING_ACTIVATION.json').exists())
        file=next(path.glob('canon/domain/v11/kristalizer-staging-*/external-crosswalk.json'))
        self.assertEqual(load(file)['mappings'][0]['status'],'accepted')

    def test_invalid_evidence_fails_staging(self):
        scan(self.src,self.out,self.index)
        decisions=self.out/'ANALYSE/DECISIONS.csv';rs=read_csv(decisions)
        rs[0].update(decision='approved',reviewer='expert',reason='raison',evidence_refs='KS999')
        with decisions.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=rs[0]);w.writeheader();w.writerows(rs)
        with self.assertRaisesRegex(ValueError,'KS du graphe'):stage(self.src,self.out)

    def test_legacy_decisions_import(self):
        scan(self.src,self.out,self.index)
        old=self.root/'historique.csv'
        with old.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['project','local_id','external_id','decision','reviewer','reason','evidence_refs'])
            w.writeheader()
            w.writerow({'project':'Kristal-Futur','local_id':'KQ100','external_id':'Q100',
                        'decision':'rejected','reviewer':'revue','reason':'exclusion après audit','evidence_refs':''})
            w.writerow({'project':'Autre-Kristal','local_id':'KQ999','external_id':'Q999',
                        'decision':'rejected','reviewer':'revue','reason':'sans projet','evidence_refs':''})
        result=import_legacy_decisions(old,self.out)
        self.assertEqual(result['imported'],1);self.assertEqual(result['not_found'],1)
        self.assertEqual(read_csv(self.out/'ANALYSE/DECISIONS.csv')[0]['decision'],'rejected')
        self.assertEqual(len(read_csv(self.out/'ANALYSE/IMPORT_NON_RETROUVES.csv')),1)

    def test_without_v11_report(self):
        project=self.src/'Kristal-Legacy';project.mkdir();write(project/'kristal.workspace.json',{'slug':'legacy'})
        r=scan(self.src,self.out,self.index)
        self.assertEqual(r['projects'],2);self.assertEqual(r['migration_required'],1)

    def test_new_stage_report_and_compatibility(self):
        scan(self.src,self.out,self.index)
        info=stage(self.src,self.out)
        staging=Path(info['staging'])
        self.assertTrue((staging/'KRISTALIZER_STAGE_REPORT.json').is_file())
        self.assertFalse((staging/'BRIDGE_STAGE_REPORT.json').exists())
        self.assertEqual(load(staging/'KRISTALIZER_STAGE_REPORT.json')['source_modified'], False)

    def test_cli_and_new_module(self):
        import kristalizer
        self.assertEqual(kristalizer.__version__, '1.1.0')

    def test_missing_index_offline(self):
        r=scan(self.src,self.out,self.root/'absent.sqlite')
        self.assertEqual(r['candidates'],0);self.assertFalse(r['indexed']['connected'])

if __name__=='__main__':unittest.main()
