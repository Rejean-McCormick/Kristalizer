import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[1]/'tools/unesco_editorial_intake_v14.py'
s=importlib.util.spec_from_file_location('krv14',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_false_publication_not_accepted(self):
  with self.assertRaises(m.IntakeError):m.validate({'format':'kristal-manager.unesco-mt1-10-editorial-dispositions/1.0',
  'admission_to_canon_authorized':False,'publication_authorized':True,'human_authorization_verified':False}, {})
 def test_no_fake_human_approval(self):
  with self.assertRaises(m.IntakeError):m.validate({'format':'kristal-manager.unesco-mt1-10-editorial-dispositions/1.0',
  'admission_to_canon_authorized':False,'publication_authorized':False,'human_authorization_verified':False,
  'human_signed_approvals':1}, {})
 def test_exact_cardinality_required(self):
  with self.assertRaises(m.IntakeError):m.validate({'format':'kristal-manager.unesco-mt1-10-editorial-dispositions/1.0',
  'admission_to_canon_authorized':False,'publication_authorized':False,'human_authorization_verified':False,
  'human_signed_approvals':0,'actual_KS_qualified':0,'canonical_KQ_KP_KA_KS_created':0,'decisions':[]}, {})
if __name__=='__main__':unittest.main()
