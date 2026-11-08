import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).resolve().parents[1]/'tools/unesco_ai_proposal_intake.py'
s=importlib.util.spec_from_file_location('ai_rfix',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class TestRedirectQuarantine(unittest.TestCase):
 def test_legacy_eligible_redirect_is_rejected(self):
  entries=[{'unesco_id':f'concept{i+1}','unesco_source_uri':f'https://unesco.test/concept{i+1}',
       'wikipedia_en':[{'page_id':42,'local_text':{'text_sha256':'a'*64,'revision_id':'17',
                   'ai_context_eligible':True,'source_integrity_status':'CANDIDATE_MATCHED',
                   'title_agrees':True,'revision_agrees':True,
                   'context_excerpt_unverified':'#REDIRECT [[Literacy]]'}}] if i==0 else []} for i in range(41)]
  dossier={'profile':'skope.unesco-mt1-10-local-source-dossier/1.0','branch':'unesco-mt1-10',
         'private':True,'not_canonical':True,'public_upload_authorized':False,'entries':entries}
  proposed={'format':'kristalizer.unesco-mt1-10-raw-ai-proposals/1.0','branch':'unesco-mt1-10',
         'dossier_sha256':'f'*64,'proposals':[{'proposal_ref':'test','unesco_id':'concept1',
         'statement_text':'test','model_id':'actual-model-name','generation_ref':'example-generation',
         'evidence_refs':[{'source_type':'wikipedia_en','page_id':42,'sha256':'a'*64,'revision_id':'17'}]}]}
  with self.assertRaisesRegex(m.ProposalError,'redirect'):
   m.accept(dossier,proposed,dossier_sha256='f'*64)
if __name__=='__main__':unittest.main()
