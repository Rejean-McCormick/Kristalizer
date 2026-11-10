"""Strict, opt-in real Kit/Framework source checks for v11 draft.4."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from kristalizer.kit_reference import inspect_kit

KIT=Path(os.environ.get('KRISTALIZER_TEST_KIT_SOURCE','/missing-kit'))
FW=Path(os.environ.get('KRISTALIZER_TEST_FRAMEWORK_SOURCE','/missing-fw'))

class StrictExternalDraft4Tests(unittest.TestCase):
    @unittest.skipUnless(KIT.is_dir() and FW.is_dir(),'Require explicit independent source checkout fixtures')
    def test_actual_sources_are_pinned_and_read_only(self):
        info=inspect_kit(KIT,framework=FW)
        self.assertTrue(info['framework_source_checked'])
        self.assertEqual(info['version'],'4.0.0-draft.4')
        self.assertEqual(info['framework_pin'],'11.0.0-draft.4')
        self.assertFalse(info['bundled'])

    @unittest.skipUnless(KIT.is_dir(),'Require Kit source checkout')
    def test_kit_without_framework_is_only_self_declared(self):
        self.assertFalse(inspect_kit(KIT)['framework_source_checked'])

    @unittest.skipUnless(KIT.is_dir() and FW.is_dir(),'Require explicit independent source checkout fixtures')
    def test_corrupted_upstream_framework_is_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fw';shutil.copytree(FW,path)
            target=path/'schemas/v11/kristal-semantic-graph.schema.json'
            target.write_bytes(target.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'pin drift'):
                inspect_kit(KIT,framework=path)

    @unittest.skipUnless(KIT.is_dir(),'Require Kit source checkout')
    def test_future_unapproved_kit_draft_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'kit';shutil.copytree(KIT,path)
            (path/'VERSION').write_text('4.0.0-draft.5\n')
            with self.assertRaisesRegex(ValueError,'not qualified'):
                inspect_kit(path)

    @unittest.skipUnless(KIT.is_dir(),'Require Kit source checkout')
    def test_forged_pin_entry_denied_before_kit_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'kit';shutil.copytree(KIT,path)
            pin=path/'contracts/v11-framework-pin.json'
            data=json.loads(pin.read_text())
            data['files']['schemas/v11/kristal-semantic-graph.schema.json']='ab'
            pin.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'pin entry'):
                inspect_kit(path)

if __name__=='__main__':unittest.main()
