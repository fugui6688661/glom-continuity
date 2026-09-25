"""Validate the explicit CI test inventory before selecting a lane."""
import argparse
import json
from pathlib import Path
import re
import stat
import sys
import unittest


LANES = ('portable_py', 'harness_py', 'harness_node')


class PlanError(Exception):
    """Only fixed public reason codes are allowed in a check report."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise PlanError('INVALID_ARGUMENTS')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def valid_name(name, suffix=None):
    return (isinstance(name, str)
            and re.fullmatch(r'tests/test_[A-Za-z0-9_]+\.(py|mjs)', name) is not None
            and (suffix is None or name.endswith(suffix)))


def read_plan(root):
    try:
        plan = json.loads((root / 'ci/test-plan.json').read_text(encoding='utf-8'),
                          object_pairs_hook=unique_object)
    except (OSError, ValueError, RecursionError):
        raise PlanError('INVALID_MANIFEST') from None
    if (not isinstance(plan, dict) or set(plan) != {*LANES, 'exclusions', 'schema_version'}
            or type(plan['schema_version']) is not int or plan['schema_version'] != 1):
        raise PlanError('INVALID_MANIFEST')
    for lane in LANES:
        suffix = '.mjs' if lane == 'harness_node' else '.py'
        if not isinstance(plan[lane], list) or not all(valid_name(name, suffix) for name in plan[lane]):
            raise PlanError('INVALID_MANIFEST')
    if not isinstance(plan['exclusions'], list):
        raise PlanError('INVALID_MANIFEST')
    for item in plan['exclusions']:
        if (not isinstance(item, dict) or set(item) != {'file', 'reason'}
                or not valid_name(item['file']) or not isinstance(item['reason'], str)
                or not item['reason'].strip()):
            raise PlanError('INVALID_MANIFEST')
    return plan


def check(root):
    plan = read_plan(root)
    assigned = [name for lane in LANES for name in plan[lane]]
    assigned.extend(item['file'] for item in plan['exclusions'])
    if len(assigned) != len(set(assigned)):
        return plan, {'state': 'failed', 'reason': 'DUPLICATE_TESTS'}
    directory = root / 'tests'
    if directory.is_symlink() or not directory.is_dir():
        raise PlanError('UNSAFE_TEST_TARGET')
    found = set()
    for path in directory.iterdir():
        if not (path.name.startswith('test_') and path.suffix in ('.py', '.mjs')):
            continue
        if not stat.S_ISREG(path.lstat().st_mode):
            raise PlanError('UNSAFE_TEST_TARGET')
        found.add('tests/' + path.name)
    if set(assigned) - found:
        return plan, {'state': 'failed', 'reason': 'MISSING_TESTS'}
    if found - set(assigned):
        return plan, {'state': 'failed', 'reason': 'UNASSIGNED_TESTS'}
    return plan, {'state': 'passed', 'reason': 'OK',
                  'counts': {**{lane: len(plan[lane]) for lane in LANES},
                             'exclusions': len(plan['exclusions']), 'inventory': len(found)}}


def run_portable(root, plan):
    # Import only validated, explicitly assigned module names, never a wildcard.
    # Keep the caller's normal environment; it is never serialized into reports.
    sys.path.insert(0, str((root / 'tests').resolve()))
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    if not plan['portable_py']:
        raise PlanError('EMPTY_PORTABLE_SUITE')
    for name in plan['portable_py']:
        selected = loader.loadTestsFromName(Path(name).stem)
        if selected.countTestCases() == 0:
            raise PlanError('EMPTY_PORTABLE_SUITE')
        suite.addTests(selected)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main():
    parser = Parser(prog='ci_plan.py', description=__doc__, allow_abbrev=False)
    parser.add_argument('action', choices=('check', 'portable'))
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    try:
        args = parser.parse_args()
        plan, report = check(args.root)
        if args.action == 'portable' and report['state'] == 'passed':
            return run_portable(args.root, plan)
    except PlanError as error:
        report = {'state': 'failed', 'reason': str(error)}
    except OSError:
        report = {'state': 'failed', 'reason': 'INVENTORY_UNREADABLE'}
    print(json.dumps(report))
    return 0 if report['state'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
