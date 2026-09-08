import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class MainCliTests(unittest.TestCase):
    def test_help_lists_export_mode_flags(self):
        env = os.environ.copy()
        env.update(
            {
                "TT_TOKEN": "x",
                "TT_DATE_FROM": "2026-07-16",
                "TT_DATE_TO": "2026-08-15",
                "ADO_TOKEN": "x",
                "ADO_ORG": "org",
                "ADO_PROJECT_ID": "proj",
                "ADO_QUERY_ID": "query",
            }
        )
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--ado-export-mode", result.stdout)
        self.assertIn("wiql_env", result.stdout)
        self.assertIn("saved_query", result.stdout)
        self.assertIn("--compare-modes", result.stdout)


if __name__ == "__main__":
    unittest.main()
