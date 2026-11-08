"""Kristalizer private review-only gate: no KQ/KA/KS mint or publication."""
import csv
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'tools'/'unesco_global_review_gate.py'
SPEC=importlib.util.spec_from_file_location('unesco_global_review_gate',SCRIPT)
GATE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)

def write_json(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')
 return sha256(path.read_bytes()).hexdigest()

def csv_file(path,rows):
 with path.open('w',encoding='utf-8',newline='') as file:
  wr=csv.DictWriter(file,fieldnames=rows[0].keys())
  wr.writeheader();wr.writerows(rows)
 return sha256(path.read_bytes()).hexdigest()

class GateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.work=Path(self.tmp.name)
  s11=self.work/'semantic_stage_v11_global'
  s12=self.work/'semantic_stage_v12_revue_chatgpt'
  s11.mkdir();s12.mkdir()
  sha11=write_json(s11/'MANIFESTE_PASSE_GLOBALE.json',{'branch':'unesco-mt1-10'})
  self.src=[{'proposal_ref':f'P{i:03}','unesco_id':'concept10','statement_en':f'Texte source {i}'} for i in range(85)]
  csv_file(s11/'TABLEAU_85_PROPOSITIONS.csv',self.src)
  self.review=[{'proposal_ref':r['proposal_ref'],'texte_propose_en':f"Proposition revisee {i}"} for i,r in enumerate(self.src)]
  csv_file(s12/'REVUE_85_PROPOSITIONS_NON_SIGNEE.csv',self.review)
  self.reviews=[{'proposal_ref':r['proposal_ref'],'unesco_id':'concept10',
    'statement_original_en':r['statement_en'],
    'editorial_suggestion_en':self.review[i]['texte_propose_en'],
    'review_status':'HUMAN_DECISION_REQUIRED','not_ks':True,
    'canonical_KQ':None,'canonical_KP':None,'canonical_KA':None,'canonical_KS':[]} for i,r in enumerate(self.src)]
  write_json(s12/'MANIFESTE_RECOMMANDATIONS.json',{'branch':'unesco-mt1-10','purpose':'test'})
  self.hand={
    'format':GATE.PROFILE,'branch':GATE.BRANCH,'one_branch_kristal':True,
    'source_stage11_manifest_sha256':sha11,
    'review_manifest_sha256':GATE.sha(s12/'MANIFESTE_RECOMMANDATIONS.json'),
    'recommendation_count':85,'human_decisions_written_by_tool':0,
    'canonical_identifiers_minted_by_tool':0,'approved_KS_by_tool':0,
    'canon_admission_authorized':False,'publication_authorized':False,
    'proposals':self.reviews,
  }
  self.handoff_path=s12/GATE.FILENAME
  self.manifest_path=s12/GATE.REVIEW_MANIFEST
  self.save_handoff()

 def tearDown(self):self.tmp.cleanup()

 def save_handoff(self):
  s12=self.work/'semantic_stage_v12_revue_chatgpt'
  write_json(self.handoff_path,self.hand)
  files={n:GATE.sha(s12/n) for n in ['REVUE_85_PROPOSITIONS_NON_SIGNEE.csv','MANIFESTE_RECOMMANDATIONS.json',GATE.FILENAME]}
  write_json(self.manifest_path,{'format':'koa.unesco-mt1-10-review-overlay-installation/1.0',
  'branch':GATE.BRANCH,'canonical_created':0,'publication_authorized':False,
  'stage11_manifest_sha256':self.hand['source_stage11_manifest_sha256'],'files_sha256':files})

 def test_valid_intake_read_only(self):
  self.assertEqual(GATE.validate(self.work)['reviewed_proposals'],85)

 def test_forbid_minted_ka_even_with_updated_hash(self):
  self.hand['proposals'][0]['canonical_KA']='KA123'
  self.save_handoff()
  with self.assertRaises(GATE.GateError):GATE.validate(self.work)

 def test_forbid_unapproved_status_change(self):
  self.hand['proposals'][0]['review_status']='APPROVED'
  self.save_handoff()
  with self.assertRaises(GATE.GateError):GATE.validate(self.work)

 def test_forbid_mismatched_text_even_with_updated_hash(self):
  self.hand['proposals'][0]['editorial_suggestion_en']='Changement non dans revue'
  self.save_handoff()
  with self.assertRaises(GATE.GateError):GATE.validate(self.work)

 def test_forbid_modified_file_without_manifest_update(self):
  self.handoff_path.write_bytes(self.handoff_path.read_bytes()+b' ')
  with self.assertRaises(GATE.GateError):GATE.validate(self.work)

 def test_forbid_canonical_admission_enabled(self):
  self.hand['canon_admission_authorized']=True
  self.save_handoff()
  with self.assertRaises(GATE.GateError):GATE.validate(self.work)

 def test_forbid_wrong_stage11_anchor(self):
  with (self.work/'semantic_stage_v11_global'/'MANIFESTE_PASSE_GLOBALE.json').open('ab') as s:s.write(b' ')
  with self.assertRaises(GATE.GateError):GATE.validate(self.work)

if __name__=='__main__':unittest.main()
