"""External authoring Kit resolution tests (no Kit code is bundled)."""
import json
import tempfile
import unittest
from pathlib import Path

from kristalizer.kit_reference import locate_kit, inspect_kit, ROOT


class CanonicalKitReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/"Kristalizer"
        self.root.mkdir()
        self.sibling = self.root.parent/"Kristal-Authoring-Kit"
        self.sibling.joinpath('tools').mkdir(parents=True)
        self.script = self.sibling/'tools/kristal.py'

    def test_falls_back_only_to_canonical_sibling(self):
        found = locate_kit(root=self.root, environ={})
        self.assertEqual(found, self.script)

    def test_explicit_path_takes_precedence(self):
        picked = self.root.parent/'IndependentKit'
        self.assertEqual(locate_kit(explicit=picked, root=self.root,
                                    environ={'KRISTAL_AUTHORING_KIT_HOME':str(self.sibling)}),
                         picked/'tools/kristal.py')

    def test_environment_before_saved_config(self):
        other=self.root.parent/'NewKit'
        cfg=self.root/'kristalizer-config.json'
        cfg.write_text(json.dumps({'kit':str(self.sibling)}))
        self.assertEqual(locate_kit(root=self.root,
                                    environ={'KRISTAL_AUTHORING_KIT_HOME':str(other)}),
                         other/'tools/kristal.py')

    def test_conflicting_environment_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            locate_kit(root=self.root,environ={
                'KRISTAL_AUTHORING_KIT_HOME':str(self.sibling),
                'KRISTAL_AUTHORING_KIT':str(self.root.parent/'OtherKit')})

    def test_no_fallback_from_invalid_saved_path(self):
        bad=self.root/'vendor/Kristal-Authoring-Kit/tools/kristal.py'
        (self.root/'kristalizer-config.json').write_text(json.dumps({'kit':str(bad)}))
        self.assertEqual(locate_kit(root=self.root,environ={}),bad)
        # It is intentionally not replaced by the sibling Kit.

    def test_missing_external_kit_fails_closed(self):
        with self.assertRaises(FileNotFoundError): inspect_kit(self.script)

    def test_reject_embedded_vendor(self):
        embedded=ROOT/'vendor/Kristal-Authoring-Kit/tools/kristal.py'
        with self.assertRaisesRegex(ValueError, 'vendor'):
            inspect_kit(embedded)

    def test_reject_incomplete_kit(self):
        self.script.write_text('KIT_VERSION="4.0.0-draft.4"')
        with self.assertRaisesRegex(ValueError, 'complete'):
            inspect_kit(self.script)

    def test_reject_outdated_kit(self):
        self.script.write_text('KIT_VERSION="4.0.0-draft.3"')
        (self.sibling/'VERSION').write_text('4.0.0-draft.3')
        (self.sibling/'contracts').mkdir()
        (self.sibling/'contracts/v11-framework-pin.json').write_text(json.dumps({'version':'11.0.0-draft.3'}))
        with self.assertRaisesRegex(ValueError, 'not qualified'):
            inspect_kit(self.script)


if __name__ == '__main__':
    unittest.main()
