"""Optional host boundary suite; real DSH runtime is a separate opt-in test."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import unittest


class DshAdapterContract(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is an optional DSH adapter dependency')
    def test_read_only_host_contract(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([shutil.which('node'), '--test', str(root / 'tests/test_dsh_recovery.mjs')],
                                cwd=root, env={**os.environ, 'CONTINUITY_TEST_PYTHON': sys.executable},
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
