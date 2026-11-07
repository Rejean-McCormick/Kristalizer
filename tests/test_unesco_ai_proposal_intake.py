import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).resolve().parents[1]/'tools/unesco_ai_proposal_intake.py'
s=importlib.util.spec_from_file_location('aiintake',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class TestAiIntake(unittest.TestCase):
 def setUp(self):
  self.d={'profile':'skope.unesco-mt1-10-local-source-dossier/1.0','branch':'unesco-mt1-10',
  'private':True,'not_canonical':True,'public_upload_authorized':False,
  'entries':[{'unesco_id':f'concept{i+1}','unesco_source_uri':f'https://unesco.test/{i+1}',
              'wikipedia_en':([{'page_id':42,'local_text':{'sha256':'x','text_sha256':'a'*64,'revision_id':'17','title_agrees':True,'revision_agrees':True,'ai_context_eligible':True,'source_integrity_status':'CANDIDATE_MATCHED'}}] if i==0 else [])} for i in range(41)]}
  self.p={'format':'kristalizer.unesco-mt1-10-raw-ai-proposals/1.0', 'branch':'unesco-mt1-10',
  'dossier_sha256':'d'*64,'proposals':[{'proposal_ref':'p1','unesco_id':'concept1','statement_text':'A test proposal, not a fact.','model_id':'demo-model','generation_ref':'demo-run-1',
   'evidence_refs':[{'source_type':'wikipedia_en','page_id':42,'sha256':'a'*64,'revision_id':'17'}]}]}
 def test_proposal_is_unapproved_and_provenance_preserved(self):
  x=m.accept(self.d,self.p,dossier_sha256='d'*64)
  self.assertEqual(x['proposed_count'],1)
  self.assertIsNone(x['proposals'][0]['canonical_KA'])
  self.assertEqual(x['proposals'][0]['canonical_KS'],[])
  self.assertFalse(x['publication_authorized'])
 def test_invalid_sha_rejected(self):
  self.p['proposals'][0]['evidence_refs'][0]['sha256']='b'*64
  with self.assertRaises(m.ProposalError):m.accept(self.d,self.p,dossier_sha256='d'*64)
 def test_revision_mismatch_dossier_rejected(self):
  t=self.d['entries'][0]['wikipedia_en'][0]['local_text']
  t['revision_agrees']=False;t['ai_context_eligible']=False;t['source_integrity_status']='INVENTORY_MISMATCH_UNUSABLE'
  with self.assertRaisesRegex(m.ProposalError,'ineligible'):
   m.accept(self.d,self.p,dossier_sha256='d'*64)
 def test_different_evidence_revision_rejected(self):
  self.p['proposals'][0]['evidence_refs'][0]['revision_id']='18'
  with self.assertRaisesRegex(m.ProposalError,'revision ID'):
   m.accept(self.d,self.p,dossier_sha256='d'*64)
 def test_missing_eligibility_flags_rejected(self):
  t=self.d['entries'][0]['wikipedia_en'][0]['local_text']
  t.pop('ai_context_eligible')
  with self.assertRaises(m.ProposalError):
   m.accept(self.d,self.p,dossier_sha256='d'*64)
 def test_qid_cannot_serve_as_source_evidence(self):
  self.p['proposals'][0]['evidence_refs']=[{'source_type':'wikidata_qid','qid':'Q123'}]
  with self.assertRaises(m.ProposalError):m.accept(self.d,self.p,dossier_sha256='d'*64)
 def test_prompt_provenance_mandatory(self):
  self.p['proposals'][0]['model_id']=''
  with self.assertRaises(m.ProposalError):m.accept(self.d,self.p,dossier_sha256='d'*64)
if __name__=='__main__':unittest.main()
