"""Noncanonical DaAT observation guard: no owner authority inferred from snapshot markers."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "integrations" / "daat" / "owner-observation.json"


class DaATOwnerObservationTests(unittest.TestCase):
    def test_marker_inventory_is_readonly_and_real(self):
        obj = json.loads(OBS.read_text(encoding="utf-8"))
        self.assertEqual(obj["schema"], "koa.daat-owner-observation/0.1.0-local")
        self.assertEqual(obj["evidence_status"], "OBSERVED_SNAPSHOT")
        self.assertIs(obj["read_only"], True)
        for key in ("prototype_consumer_adopted", "ik_ingress_approved",
                    "canonical_write_authorized", "publication_authorized"):
            self.assertIs(obj[key], False, key)
        self.assertGreater(len(obj["markers"]), 0)
        for name in obj["markers"]:
            self.assertNotIn("..", Path(name).parts)
            self.assertFalse(Path(name).is_absolute())
            self.assertTrue((ROOT / name).is_file(), name)
        self.assertTrue(obj["acceptance_gate"].strip())


if __name__ == "__main__":
    unittest.main()
