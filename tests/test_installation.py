"""Acceptance through the packaged install/command/uninstall boundary only."""
import importlib.util
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HAS_BUILDER = all(importlib.util.find_spec(name) for name in ('pip', 'setuptools', 'wheel'))


@unittest.skipUnless(HAS_BUILDER, 'Install pip, setuptools>=77, wheel to verify installation')
class Installation(unittest.TestCase):
    def command(self, args, cwd, ok=True, input=None):
        env = dict(os.environ, PYTHONUTF8='1', PIP_DISABLE_PIP_VERSION_CHECK='1')
        env.pop('PYTHONPATH', None)
        result = subprocess.run(args, cwd=cwd, env=env, input=input, capture_output=True,
                                text=True, encoding='utf-8', timeout=60)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def test_sdist_rebuild_preserves_canonical_guide_links_and_wheel_record(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / 'source'
            source.mkdir()
            for relative in json.loads((ROOT / 'release-files.json').read_text()):
                dest = source / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, dest)
            sdists = base / 'sdists'
            self.command([sys.executable, '-c',
                          'from setuptools.build_meta import build_sdist; '
                          'import sys; build_sdist(sys.argv[1])', str(sdists)], source)
            archive, = sdists.glob('*.tar.gz')
            wheels = base / 'from-sdist'
            self.command([sys.executable, '-m', 'pip', 'wheel', '--no-index', '--no-deps',
                          '--no-build-isolation', '--wheel-dir', str(wheels), str(archive)], base)
            wheel, = wheels.glob('*.whl')
            prefix = 'glom_continuity/_guide/'
            with zipfile.ZipFile(wheel) as built:
                entries = set(built.namelist())
                self.assertIn(prefix + 'skills/project-continuity/SKILL.md', entries)
                record_name, = (name for name in entries if name.endswith('.dist-info/RECORD'))
                record = {row[0]: row[1:] for row in csv.reader(io.StringIO(built.read(record_name).decode()))}
                for name in sorted(entries):
                    if not name.startswith(prefix) or name.endswith('/'):
                        continue
                    with self.subTest(resource=name):
                        content = built.read(name)
                        if not name.endswith('/GUIDE-MANIFEST.json'):
                            self.assertEqual(content, (source / name.removeprefix(prefix)).read_bytes())
                        expected = 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip('=')
                        self.assertEqual(record[name], [expected, str(len(content))])
                        if name.endswith('.md'):
                            for target in re.findall(r'\]\(([^)]+)\)', content.decode()):
                                ref = urllib.parse.urlsplit(target)
                                if ref.scheme or not ref.path:
                                    continue
                                linked = posixpath.normpath(posixpath.join(posixpath.dirname(name), ref.path))
                                self.assertIn(linked, entries, 'Offline guide link is missing: ' + target)

    def test_rebuilding_cannot_retain_a_guide_removed_from_the_allowlist(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / 'source'
            source.mkdir()
            for relative in json.loads((ROOT / 'release-files.json').read_text()):
                dest = source / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, dest)
            build = [sys.executable, '-m', 'pip', 'wheel', '--no-index', '--no-deps', '--no-build-isolation']
            self.command(build + ['--wheel-dir', str(base / 'first'), str(source)], base)
            names = json.loads((source / 'guide-files.json').read_text(encoding='utf-8'))
            names.remove('docs/review.md')
            (source / 'guide-files.json').write_text(json.dumps(names), encoding='utf-8')
            second = self.command(build + ['--wheel-dir', str(base / 'second'), str(source)], base)
            self.assertEqual(second.returncode, 0)
            rebuilt, = (base / 'second').glob('*.whl')
            with zipfile.ZipFile(rebuilt) as archive:
                self.assertNotIn('glom_continuity/_guide/docs/review.md', archive.namelist())

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
            prepared = self.command([sys.executable, '-I', '-B', str(source / 'scripts/runtime_env.py'),
                                     'create', '--directory', str(runtime)], base)
            self.assertEqual(json.loads(prepared.stdout)['code'], 'RUNTIME_READY')
            binaries = runtime / ('Scripts' if os.name == 'nt' else 'bin')
            python = binaries / ('python.exe' if os.name == 'nt' else 'python')
            cli = binaries / ('glom-continuity.exe' if os.name == 'nt' else 'glom-continuity')
            self.command([sys.executable, '-m', 'pip', '--python', str(python), 'install',
                          '--no-index', '--no-deps', str(artifacts[0])], base)
            shutil.rmtree(source)  # Test-owned staging tree: runtime must not borrow its files.
            self.command([str(python), '-c', 'import importlib.util; '
                          'assert importlib.util.find_spec("setuptools") is None'], base)
            version = self.command([str(cli), '--version'], base).stdout.strip()
            self.assertRegex(version, r'^0\.1\.0(?:(?:-alpha\.|a|\.dev|rc)[0-9]+)?$')
            self.assertEqual(self.command([str(python), '-m', 'glom_continuity', '--version'], base).stdout.strip(), version)
            project = base / '中文 project'
            project.mkdir()
            diagnosed = json.loads(self.command([str(cli), '--project', str(project), 'doctor'], base).stdout)
            guide = diagnosed['data'].get('usage')
            self.assertIsInstance(guide, dict, 'Installed users need the matching Skill without fetching a second source tree')
            self.assertEqual(guide['state'], 'available')
            self.assertEqual(guide['tool_version'], version)
            self.assertFalse(guide['host_configuration_checked'])
            skill = Path(guide['skill_path'])
            self.assertTrue(skill.is_absolute())
            self.assertTrue(skill.is_relative_to(runtime.resolve()))
            self.assertIn('name: project-continuity', skill.read_text(encoding='utf-8'))
            self.assertTrue((skill.parent / '../../docs/project-memory.md').resolve().is_file())
            self.assertFalse((project / '.continuity').exists())
            empty_setup = json.loads(self.command([str(cli), '--project', str(project), 'setup'], base).stdout)
            self.assertEqual(empty_setup['data']['setup_state'], 'requires_initialization')
            self.assertIsNone(empty_setup['data']['binding'])
            # An existing but altered guide must not be presented as matching this runtime.
            original_skill = skill.read_bytes()
            skill.write_text('Unrelated instructions from another package', encoding='utf-8')
            changed = json.loads(self.command([str(cli), '--project', str(project), 'doctor'], base).stdout)
            self.assertEqual(changed['data']['usage']['state'], 'unavailable')
            self.assertIsNone(changed['data']['usage']['skill_path'])
            self.assertIn('GUIDE_CHANGED', changed['data']['usage']['issues'])
            self.assertEqual(skill.read_text(encoding='utf-8'), 'Unrelated instructions from another package')
            self.assertFalse((project / '.continuity').exists())
            refused_setup = json.loads(self.command([str(cli), '--project', str(project), 'setup'],
                                                    base, ok=False).stdout)
            self.assertEqual(refused_setup['code'], 'GUIDE_UNAVAILABLE')
            self.assertIsNone(refused_setup['data'])
            skill.write_bytes(original_skill)
            related = (skill.parent / '../../docs/project-memory.md').resolve()
            kept = related.with_suffix('.held')
            related.rename(kept)
            try:
                missing_guide = json.loads(self.command([str(cli), '--project', str(project), 'doctor'], base).stdout)
                self.assertEqual(missing_guide['data']['usage']['state'], 'unavailable')
                self.assertIsNone(missing_guide['data']['usage']['skill_path'])
                self.assertIn('GUIDE_MISSING', missing_guide['data']['usage']['issues'])
                self.assertFalse(related.exists())
            finally:
                kept.rename(related)
            restored = json.loads(self.command([str(cli), '--project', str(project), 'doctor'], base).stdout)
            self.assertEqual(restored['data']['usage']['state'], 'available')
            result = self.command([str(cli), '--project', str(project), 'init', '--name', '安装测试'], base)
            self.assertTrue(json.loads(result.stdout)['ok'])
            setup = json.loads(self.command([str(cli), '--project', str(project), 'setup'], base).stdout)['data']
            self.assertEqual(setup['setup_state'], 'ready_for_manual_binding')
            self.assertFalse(setup['host_integrated'])
            binding = setup['binding']
            self.assertEqual(binding['guide_state'], 'available')
            bound_diagnosis = json.loads(self.command(binding['doctor_argv'], base).stdout)['data']
            self.assertEqual(bound_diagnosis['usage']['state'], 'available')
            self.assertEqual(bound_diagnosis['runtime']['program_sha256'], binding['program_sha256'])
            bound_resume = json.loads(self.command(binding['resume_argv'], base).stdout)['data']
            self.assertEqual(bound_resume['project_id'], json.loads(result.stdout)['data']['project_id'])
            self.assertEqual(bound_resume['recovery_state'], 'no_checkpoint')
            recovered = self.command([str(cli), '--project', str(project), 'resume'], base)
            self.assertEqual(json.loads(recovered.stdout)['data']['recovery_state'], 'no_checkpoint')
            suffix = '.exe' if os.name == 'nt' else ''
            recovery = binaries / ('glom-continuity-recovery' + suffix)
            bound = [str(recovery), '--project', str(project), '--project-id',
                     json.loads(result.stdout)['data']['project_id'], '--session-id', 'install-session',
                     '--generation', 'install-epoch']
            event = dict(event='session_start', cwd=str(project.resolve()),
                         session_id='install-session', generation='install-epoch', query='')
            prepared = self.command(bound + ['prepare'], base, input=json.dumps(event))
            receipt = json.loads(prepared.stdout)['data']['receipt']
            delivered = self.command(bound + ['deliver'], base, input=json.dumps(receipt))
            self.assertEqual(json.loads(delivered.stdout)['data']['delivery_state'], 'empty')
            demo = binaries / ('glom-continuity-demo' + suffix)
            replay = self.command([str(demo), '--output', str(base / 'demo')], base)
            self.assertEqual(json.loads(replay.stdout)['state'], 'protocol_demo_passed')
            self.assertFalse(json.loads(replay.stdout)['real_model_handoff_verified'])
            mcp = binaries / ('glom-continuity-mcp' + suffix)
            missing = self.command([str(mcp), '--project', str(project)], base, ok=False)
            self.assertIn('optional dependency', missing.stderr)
            self.assertNotIn('Traceback', missing.stderr)
            # Disconnect through the installed consumer, not an import from the source tree.
            draft = project / 'reviewed-progress.json'
            draft.write_text(json.dumps({
                'objective': 'Prepare an event for 50 people', 'next_action': 'Confirm the venue',
                'constraints': ['Budget is 5000'], 'decisions': [],
                'unresolved': ['Venue is not selected'], 'evidence': [],
            }), encoding='utf-8')
            self.command([str(cli), '--project', str(project), 'checkpoint',
                          '--from-file', str(draft), '--expect-revision', '0'], base)
            saved = self.command([str(cli), '--project', str(project), 'status'], base).stdout
            user_rule = project / 'AGENTS.md'
            user_bytes = b'\xef\xbb\xbf# Existing instructions\r\nKeep user decisions.\r\n'
            user_rule.write_bytes(user_bytes)
            entry = [str(cli), '--project', str(project), 'entry']
            preview = json.loads(self.command(entry + ['integrate', '--host', 'codex'], base).stdout)['data']
            apply = entry + ['integrate', '--host', 'codex', '--apply',
                '--expect-sha256', preview['upgrade']['old_sha256'],
                '--expect-new-sha256', preview['upgrade']['new_sha256'],
                '--expect-state', preview['state']]
            if sys.platform in ('darwin', 'linux'):
                self.command(apply, base)
                installed_rule = user_rule.read_bytes()
                removal = json.loads(self.command(entry + ['detach', '--host', 'codex'], base).stdout)['data']
                detached = json.loads(self.command(entry + ['detach', '--host', 'codex', '--apply',
                    '--expect-state', removal['state'], '--expect-sha256', removal['sha256']], base).stdout)['data']
                self.assertEqual(detached['state'], 'detached')
                self.assertEqual(detached['removal']['outcome'], 'exchange_observed')
                self.assertEqual(user_rule.read_bytes(), user_bytes)
                retained = project / detached['removal']['retained_path']
                self.assertEqual(retained.read_bytes(), installed_rule)
            else:
                refusal = json.loads(self.command(apply, base, ok=False).stdout)
                self.assertEqual(refusal['code'], 'ENTRY_EXCHANGE_UNSUPPORTED')
                self.assertEqual(user_rule.read_bytes(), user_bytes)
            self.assertEqual(self.command([str(cli), '--project', str(project), 'status'], base).stdout, saved)
            storage = project / '.continuity' / 'state.sqlite3'
            before = storage.read_bytes()
            self.command([sys.executable, '-m', 'pip', '--python', str(python), 'uninstall',
                          '--yes', 'glom-continuity'], base)
            self.assertFalse(cli.exists())
            self.assertFalse(recovery.exists())
            self.assertFalse(skill.exists())
            self.assertEqual(storage.read_bytes(), before)
            self.command([str(python), '-m', 'glom_continuity', '--version'], base, ok=False)
