import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPT=Path(__file__).resolve().parents[1]/'tools/unesco_local_provenance_v16.py'
spec=importlib.util.spec_from_file_location('pv16',SCRIPT);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class LocalProvenanceTests(unittest.TestCase):
    def test_redirect_recognition(self):
        self.assertTrue(m.REDIRECT.match('#REDIRECT [[Literacy]]'))
        self.assertTrue(m.REDIRECT.match(' #redirect [[Item]]'))
        self.assertFalse(m.REDIRECT.match('{{short description|Educational rights}}'))
    def test_missing_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.ProvenanceError):m.verify(Path(d),Path(d))
    def create_fixture(self,root):
        ext=root/'wikipedia_extract';ext.mkdir();s11=root/'stage11';s11.mkdir()
        pages=[]
        for i in range(14):
            raw=('#REDIRECT [[Other]]' if i>=12 else f'== Original article {i} ==\nSource context').encode()
            (ext/f'page-{i+1}.wikitext.txt').write_bytes(raw)
            pages.append({'page_id':i+1,'revision_id':str(100+i),'relative_path':f'page-{i+1}.wikitext.txt',
                          'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
        (ext/'manifest.json').write_text(json.dumps({'branch':'unesco-mt1-10','private':True,
            'public_upload_authorized':False,'extracted_pages':14,'pages':pages}))
        with (s11/'WIKIPEDIA_16_CONTEXTES_NON_KS.csv').open('w',newline='',encoding='utf-8') as file:
            w=csv.DictWriter(file,fieldnames=['proposal_ref','unesco_id','page_id','revision_id','local_text_sha256','usage','wikipedia_licence_cleared'])
            w.writeheader()
            for i in range(16):
                page=pages[i%10]
                w.writerow({'proposal_ref':f'P{i}','unesco_id':f'concept{i}','page_id':page['page_id'],
                    'revision_id':page['revision_id'],'local_text_sha256':page['sha256'],
                    'usage':'RESEARCH_CONTEXT_ONLY_NOT_KS','wikipedia_licence_cleared':'NO'})
        with (s11/'FILE_81_SOURCES_A_ATTESTER.csv').open('w',newline='',encoding='utf-8') as file:
            w=csv.DictWriter(file,fieldnames=['reference_id','approved_KS']);w.writeheader()
            for i in range(81):w.writerow({'reference_id':f'lead{i}','approved_KS':'NO'})
        return ext,s11
    def test_complete_synthetic_fixture_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            ext,s11=self.create_fixture(Path(d))
            result=m.verify(ext,s11)
            self.assertEqual((result['dump_pages_verified'],result['substantive_pages'],result['redirect_pages_excluded'],result['candidate_research_contexts_verified']),(14,12,2,16))
            (ext/'page-1.wikitext.txt').write_text('tampered')
            with self.assertRaises(m.ProvenanceError):m.verify(ext,s11)
    def test_reject_redirect_as_cited_source(self):
        with tempfile.TemporaryDirectory() as d:
            ext,s11=self.create_fixture(Path(d))
            p=s11/'WIKIPEDIA_16_CONTEXTES_NON_KS.csv'
            with p.open(newline='',encoding='utf-8') as file:rows=list(csv.DictReader(file))
            pages=m._json(ext/'manifest.json')['pages']
            rows[0].update({'page_id':'13','revision_id':pages[12]['revision_id'],'local_text_sha256':pages[12]['sha256']})
            with p.open('w',newline='',encoding='utf-8') as file:
                w=csv.DictWriter(file,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
            with self.assertRaises(m.ProvenanceError):m.verify(ext,s11)
    def test_real_archive_when_available(self):
        a=Path('/mnt/data/autopilot_concept10_puis_41.zip');b=Path('/mnt/data/semantic_stage_v11_global.zip')
        if not (a.is_file() and b.is_file()):self.skipTest('Conversation archives not present on Windows')
        with tempfile.TemporaryDirectory() as d,zipfile.ZipFile(a) as x,zipfile.ZipFile(b) as y:
            ext=Path(d)/'wikipedia_extract';ext.mkdir();s11=Path(d)/'stage11';s11.mkdir()
            for name in x.namelist():
                if name.startswith('autopilot_concept10_puis_41/wikipedia_extract/') and not name.endswith('/'):
                    (ext/Path(name).name).write_bytes(x.read(name))
            for name in ('WIKIPEDIA_16_CONTEXTES_NON_KS.csv','FILE_81_SOURCES_A_ATTESTER.csv'):
                (s11/name).write_bytes(y.read('semantic_stage_v11_global/'+name))
            self.assertEqual(m.verify(ext,s11)['candidate_research_contexts_verified'],16)

if __name__=='__main__':unittest.main()
