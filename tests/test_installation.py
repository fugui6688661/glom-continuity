"""Acceptance through the packaged install/command/uninstall boundary only."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]
HAS_BUILDER = all(importlib.util.find_spec(name) for name in ('pip', 'setuptools', 'wheel'))


@unittest.skipUnless(HAS_BUILDER, 'Install pip, setuptools>=77, wheel to verify installation')
class Installation(unittest.TestCase):
    def command(self, args, cwd, ok=True):
        env = dict(os.environ, PYTHONUTF8='1', PIP_DISABLE_PIP_VERSION_CHECK='1')
        env.pop('PYTHONPATH', None)
        result = subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                                text=True, encoding='utf-8', timeout=60)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def test_install_runs_from_another_directory_and_uninstall_preserves_project(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / 'source'
            source.mkdir()
            for relative in json.loads((ROOT / 'release-files.json').read_text()):
                dest = source / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, dest)
            wheels = base / 'wheels'
            self.command([sys.executable, '-m', 'pip', 'wheel', '--no-index', '--no-deps',
                          '--no-build-isolation', '--wheel-dir', str(wheels), str(source)], base)
            artifacts = list(wheels.glob('*.whl'))
            self.assertEqual(len(artifacts), 1)
            runtime = base / 'isolated'
            venv.EnvBuilder(with_pip=False).create(runtime)
            binaries = runtime / ('Scripts' if os.name == 'nt' else 'bin')
            python = binaries / ('python.exe' if os.name == 'nt' else 'python')
            cli = binaries / ('glom-continuity.exe' if os.name == 'nt' else 'glom-continuity')
            self.command([sys.executable, '-m', 'pip', '--python', str(python), 'install',
                          '--no-index', '--no-deps', str(artifacts[0])], base)
            version = self.command([str(cli), '--version'], base).stdout.strip()
            self.assertRegex(version, r'^0\.1\.0(?:-alpha\.[0-9]+|a[0-9]+)$')
            self.assertEqual(self.command([str(python), '-m', 'glom_continuity', '--version'], base).stdout.strip(), version)
            project = base / '中文 project'
            project.mkdir()
            result = self.command([str(cli), '--project', str(project), 'init', '--name', '安装测试'], base)
            self.assertTrue(json.loads(result.stdout)['ok'])
            suffix = '.exe' if os.name == 'nt' else ''
            demo = binaries / ('glom-continuity-demo' + suffix)
            replay = self.command([str(demo), '--output', str(base / 'demo')], base)
            self.assertEqual(json.loads(replay.stdout)['state'], 'protocol_demo_passed')
            self.assertFalse(json.loads(replay.stdout)['real_model_handoff_verified'])
            mcp = binaries / ('glom-continuity-mcp' + suffix)
            missing = self.command([str(mcp), '--project', str(project)], base, ok=False)
            self.assertIn('optional dependency', missing.stderr)
            self.assertNotIn('Traceback', missing.stderr)
            storage = project / '.continuity' / 'state.sqlite3'
            before = storage.read_bytes()
            self.command([sys.executable, '-m', 'pip', '--python', str(python), 'uninstall',
                          '--yes', 'glom-continuity'], base)
            self.assertFalse(cli.exists())
            self.assertEqual(storage.read_bytes(), before)
            self.command([str(python), '-m', 'glom_continuity', '--version'], base, ok=False)
