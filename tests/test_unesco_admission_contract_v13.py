import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'tools'/'unesco_admission_contract_v13.py'
sys.path.insert(0,str(SCRIPT.parent))
spec=importlib.util.spec_from_file_location('unesco_admission_contract_v13',SCRIPT)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class ContractTests(unittest.TestCase):
 def test_validated_unsigned_review_does_not_approve(self):
  result={'status':'KRISTALIZER_PRIVATE_REVIEW_VALIDATED_CANON_BLOCKED',
          'reviewed_proposals':85,'intake_kind':'UNSIGNED_EDITORIAL_RECOMMENDATIONS_NOT_RAW_AI_AND_NOT_KA'}
  with patch.object(mod,'validate',return_value=result):
   r=mod.inspect(Path('private'))
  self.assertEqual(r['approved_KS'],0)
  self.assertEqual(r['human_decisions_verified'],0)
  self.assertEqual(r['status'],'INTEGRITY_PASSED_CONTENT_NOT_ADMITTED')
 def test_wrong_gate_status_rejected(self):
  with patch.object(mod,'validate',return_value={'status':'WRONG'}):
   with self.assertRaises(ValueError):mod.inspect(Path('private'))

if __name__=='__main__':unittest.main()
