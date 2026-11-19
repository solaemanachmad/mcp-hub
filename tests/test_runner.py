"""Tests for Windows 11 PC experiment runner."""

import json
import tempfile
import unittest
from pathlib import Path

from pc.runner import execute_job, resolve_script


class TestRunner(unittest.TestCase):
    def test_path_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                resolve_script(Path(tmp), "../outside.py")

    def test_execute_job_collects_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "demo.py"
            script.write_text(
                "import json, os\n"
                "cfg = json.load(open(os.environ['EXP_CONFIG']))\n"
                "out = {'f1': 0.95, 'lr': cfg['lr']}\n"
                "json.dump(out, open(os.environ['EXP_METRICS'], 'w'))\n"
                "print('ok')\n",
                encoding="utf-8",
            )
            job = {"id": "exp-test01", "script": "demo.py", "config": {"lr": 0.001}}
            res = execute_job(job, work_dir=tmp, timeout=30)
            self.assertEqual(res["status"], "completed")
            self.assertEqual(res["metrics"], {"f1": 0.95, "lr": 0.001})
            self.assertIn("ok", res["logs"])


if __name__ == "__main__":
    unittest.main()
