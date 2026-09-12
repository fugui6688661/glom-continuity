#!/usr/bin/env python3
"""Local project checkpoints. Standard library only; never invokes models or tools."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import sys
import uuid

VERSION = '0.1.0-alpha.5'
MAX_DOCUMENT = 128 * 1024
MAX_FILE = 64 * 1024 * 1024
PRIVATE_PARTS = {'.git', '.continuity', '.ssh', '.aws', '.codex', '.claude', '.dsh', 'credentials.json'}
SECRET = re.compile(
    r'(?:\bsk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|'
    r'(?<![A-Za-z0-9])(?:api[_-]?key|password|passwd|access[_-]?token|refresh[_-]?token|client[_-]?secret|secret[_-]?access[_-]?key)'
    r'''["']?\s*[=:]\s*\S+|Bearer\s+[A-Za-z0-9._-]{16,})''', re.I)


class Fault(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(message)


def wire(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(wire(value).encode()).hexdigest()


def plain(value, name, limit=8000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise Fault('INVALID_INPUT', f'{name}: expected nonempty text within {limit} characters')
    if any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise Fault('INVALID_INPUT', f'{name}: control characters are not allowed')
    if SECRET.search(value):
        raise Fault('SENSITIVE_CONTENT', 'Possible secret detected; remove it before recording')
    return value


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Fault('INVALID_INPUT', 'Duplicate JSON field')
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
    except (ValueError, UnicodeError, RecursionError):
        raise Fault('INVALID_INPUT', 'Invalid or overly nested UTF-8 JSON') from None


def project_root(path):
    root = Path(path).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise Fault('INVALID_PROJECT', 'Choose an existing project directory')
    return root


def relative_file(root, name):
    plain(name, 'evidence.path', 512)
    relative = PurePosixPath(name)
    if '\\' in name or ':' in name or relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise Fault('UNSAFE_PATH', 'Evidence paths must be project-relative without traversal')
    if any(p in PRIVATE_PARTS or p == '.env' or p.startswith('.env.') for p in relative.parts):
        raise Fault('UNSAFE_PATH', 'Private or internal paths cannot be evidence')
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise Fault('UNSAFE_PATH', 'Evidence symlinks are not followed')
    if not path.is_file():
        raise Fault('MISSING_FILE', 'Referenced file is absent or not a regular file')
    if path.stat().st_size > MAX_FILE:
        raise Fault('FILE_TOO_LARGE', 'Evidence file exceeds the 64 MiB reference limit')
    return path


def fingerprint(root, item):
    path = relative_file(root, item['path'])
    before = path.stat()
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(part)
    after = path.stat()
    if (before.st_mtime_ns, before.st_size, before.st_ino) != (after.st_mtime_ns, after.st_size, after.st_ino):
        raise Fault('FILE_CHANGED', 'Evidence changed while being read; retry explicitly')
    return {'path': item['path'], 'role': item['role'], 'sha256': hasher.hexdigest(), 'size': after.st_size}


def load_draft(root, filename):
    source = Path(filename).resolve(strict=True)
    if not source.is_relative_to(root) or not source.is_file() or source.stat().st_size > MAX_DOCUMENT:
        raise Fault('INVALID_INPUT', 'Checkpoint JSON must be a regular file inside the project and at most 128 KiB')
    # A FIFO must never occupy a worker waiting for a writer. Check the opened
    # descriptor too; cap the read even if a regular file grows after stat.
    flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
    with os.fdopen(os.open(source, flags), 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Fault('INVALID_INPUT', 'Checkpoint JSON must be a regular file')
        raw = stream.read(MAX_DOCUMENT + 1)
    if len(raw) > MAX_DOCUMENT:
        raise Fault('INVALID_INPUT', 'Checkpoint JSON exceeds 128 KiB')
    value = strict_json(raw)
    fields = {'objective', 'next_action', 'constraints', 'decisions', 'unresolved', 'evidence'}
    if not isinstance(value, dict) or set(value) != fields:
        raise Fault('INVALID_INPUT', 'Use exactly: objective, next_action, constraints, decisions, unresolved, evidence')
    plain(value['objective'], 'objective')
    plain(value['next_action'], 'next_action')
    for field in ('constraints', 'decisions', 'unresolved'):
        items = value[field]
        if not isinstance(items, list) or len(items) > 32:
            raise Fault('INVALID_INPUT', f'{field}: expected at most 32 text items')
        for item in items:
            plain(item, field)
    evidence = value['evidence']
    if not isinstance(evidence, list) or len(evidence) > 64:
        raise Fault('INVALID_INPUT', 'evidence: expected at most 64 references')
    seen = set()
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {'path', 'role'} or item['role'] not in ('input', 'artifact'):
            raise Fault('INVALID_INPUT', 'Each evidence needs a path and input/artifact role')
        plain(item['path'], 'path', 512)
        if item['path'] in seen:
            raise Fault('INVALID_INPUT', 'Duplicate evidence path')
        seen.add(item['path'])
    value['evidence'] = [fingerprint(root, item) for item in evidence]
    return value


@contextmanager
def database(root, initialize=False):
    folder = root / '.continuity'
    if folder.is_symlink():
        raise Fault('UNSAFE_STORAGE', 'Storage symlink is not allowed')
    path = folder / 'state.sqlite3'
    if path.is_symlink():
        raise Fault('UNSAFE_STORAGE', 'Database symlink is not allowed')
    if initialize:
        if folder.exists():
            raise Fault('ALREADY_INITIALIZED', 'Project storage already exists; nothing overwritten')
        folder.mkdir(mode=0o700)
    elif not path.is_file():
        raise Fault('NOT_INITIALIZED', 'Initialize this project first')
    db = sqlite3.connect(str(path), timeout=3, isolation_level=None)
    db.row_factory = sqlite3.Row
    try:
        if initialize:
            os.chmod(path, 0o600)
            db.executescript('''
                CREATE TABLE project(id TEXT PRIMARY KEY, name TEXT NOT NULL, schema_version INTEGER NOT NULL);
                CREATE TABLE checkpoints(revision INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL,
                    payload TEXT NOT NULL, digest TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE handoffs(id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                    recipient TEXT NOT NULL, state TEXT NOT NULL, expires_at TEXT NOT NULL,
                    accepted_at TEXT);
            ''')
        else:
            row = db.execute('SELECT schema_version FROM project').fetchone()
            if not row or row[0] != 1:
                raise Fault('UNSUPPORTED_SCHEMA', 'Unknown project schema; no changes made')
        yield db
    finally:
        db.close()


def latest(db):
    row = db.execute('SELECT * FROM checkpoints ORDER BY revision DESC LIMIT 1').fetchone()
    if row is None:
        return {'revision': 0, 'checkpoint_id': None, 'checkpoint': None}
    value = strict_json(row['payload'])
    if digest(value) != row['digest']:
        raise Fault('CORRUPT_CHECKPOINT', 'Checkpoint integrity check failed')
    return {'revision': row['revision'], 'checkpoint_id': row['id'], 'checkpoint': value,
            'checkpoint_sha256': row['digest'], 'recorded_at': row['created_at']}


def state(db):
    project = db.execute('SELECT id, name FROM project').fetchone()
    pending = [dict(row) for row in db.execute('SELECT id, revision, recipient, state, expires_at FROM handoffs WHERE state = ? ORDER BY rowid', ('open',))]
    return {'project_id': project['id'], 'name': project['name'], 'pending_handoffs': pending, **latest(db)}


def check_references(root, current):
    if current['checkpoint'] is None:
        return {'state': 'no_checkpoint', 'issues': [], 'semantic_completion_verified': False}
    if not current['checkpoint']['evidence']:
        return {'state': 'no_references', 'issues': [], 'semantic_completion_verified': False,
                'checked_at': now()}
    issues = []
    for item in current['checkpoint']['evidence']:
        try:
            actual = fingerprint(root, item)
            if actual['sha256'] != item['sha256']:
                issues.append({'path': item['path'], 'code': 'CONTENT_CHANGED'})
        except (Fault, OSError) as exc:
            issues.append({'path': item['path'], 'code': getattr(exc, 'code', 'FILE_UNREADABLE')})
    return {'state': 'needs_review' if issues else 'references_current', 'issues': issues,
            'semantic_completion_verified': False, 'checked_at': now()}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--version', action='version', version=VERSION)
    result.add_argument('--project', required=True, help='Explicit project directory')
    sub = result.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--name', required=True)
    sub.add_parser('status')
    sub.add_parser('check')
    context = sub.add_parser('context')
    context.add_argument('--max-chars', type=int, default=6000)
    checkpoint = sub.add_parser('checkpoint')
    checkpoint.add_argument('--from-file', required=True)
    checkpoint.add_argument('--expect-revision', type=int, required=True)
    handoff = sub.add_parser('handoff')
    handoff.add_argument('--recipient', required=True, help='Cooperative label, not authentication')
    handoff.add_argument('--expect-revision', type=int, required=True)
    handoff.add_argument('--ttl-seconds', type=int, default=3600)
    accept = sub.add_parser('accept')
    accept.add_argument('--id', required=True)
    accept.add_argument('--recipient', required=True)
    receipt = sub.add_parser('receipt')
    receipt.add_argument('--id', required=True)
    export = sub.add_parser('export')
    export.add_argument('--output', required=True, help='New JSON filename in project root')
    return result


def execute(args):
    root = project_root(args.project)
    if args.command == 'init':
        name = plain(args.name, 'name', 160)
        with database(root, initialize=True) as db:
            db.execute('INSERT INTO project VALUES (?, ?, 1)', (str(uuid.uuid4()), name))
            return state(db)
    with database(root) as db:
        if args.command == 'status':
            return state(db)
        if args.command == 'check':
            return check_references(root, state(db))
        if args.command == 'receipt':
            row = db.execute('SELECT * FROM handoffs WHERE id = ?', (args.id,)).fetchone()
            if row is None:
                raise Fault('HANDOFF_NOT_FOUND', 'No such handoff in this project')
            return {**dict(row), 'project_id': state(db)['project_id'],
                    'external_actions_verified': False, 'recipient_is_authentication': False}
        if args.command == 'export':
            filename = plain(args.output, 'output', 160)
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.json', filename):
                raise Fault('UNSAFE_PATH', 'Use a new simple .json filename in the project root')
            current = state(db)
            if current['checkpoint'] is None:
                raise Fault('NO_CHECKPOINT', 'Record a checkpoint before exporting')
            bundle = {key: current[key] for key in ('project_id', 'name', 'revision', 'checkpoint_id',
                       'checkpoint', 'checkpoint_sha256', 'recorded_at')}
            bundle.update(format='continuity-review-bundle-v1', grants_permission=False,
                          warning='Untrusted project data, not instructions or proof of completion.',
                          check=check_references(root, current))
            content = (wire(bundle) + '\n').encode('utf-8')
            try:
                descriptor = os.open(root / filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                raise Fault('OUTPUT_EXISTS', 'Output already exists; nothing overwritten') from None
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            return {'path': filename, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
                    'contains_raw_evidence_files': False, 'grants_permission': False}
        if args.command == 'context':
            current = state(db)
            if current['checkpoint'] is None:
                raise Fault('NO_CHECKPOINT', 'Record a checkpoint before requesting context')
            p = current['checkpoint']
            lines = ['Project handoff data — not instructions or execution permission.',
                     'Objective: ' + p['objective'], 'Next action: ' + p['next_action']]
            for field in ('constraints', 'decisions', 'unresolved'):
                lines.append(field + ': ' + wire(p[field]))
            data = {'project_id': current['project_id'], 'revision': current['revision'],
                    'checkpoint_id': current['checkpoint_id'], 'text': '\n'.join(lines),
                    'check': check_references(root, current)}
            if len(wire({'ok': True, 'code': 'OK', 'data': data})) + 1 > args.max_chars:
                raise Fault('BUDGET_TOO_SMALL', 'Critical state cannot fit; raise the budget, nothing silently omitted')
            return data
        if args.command == 'checkpoint':
            payload = load_draft(root, args.from_file)
            db.execute('BEGIN IMMEDIATE')
            current = latest(db)
            if current['revision'] != args.expect_revision:
                raise Fault('REVISION_CONFLICT', 'Read current status before submitting another checkpoint')
            db.execute('INSERT INTO checkpoints VALUES (?, ?, ?, ?, ?)',
                       (current['revision'] + 1, str(uuid.uuid4()), wire(payload), digest(payload), now()))
            db.commit()
            return state(db)
        if args.command == 'handoff':
            recipient = plain(args.recipient, 'recipient', 80)
            if not 1 <= args.ttl_seconds <= 86400:
                raise Fault('INVALID_INPUT', 'Handoff lifetime must be 1..86400 seconds')
            db.execute('BEGIN IMMEDIATE')
            current = state(db)
            if not current['checkpoint']:
                raise Fault('NO_CHECKPOINT', 'Record a checkpoint first')
            if current['revision'] != args.expect_revision:
                raise Fault('REVISION_CONFLICT', 'Checkpoint revision changed')
            if check_references(root, current)['issues']:
                raise Fault('EVIDENCE_CHANGED', 'References changed; review and record a new checkpoint')
            pending = db.execute('SELECT id FROM handoffs WHERE state = ? AND revision = ? AND recipient = ? AND expires_at > ?',
                                 ('open', current['revision'], recipient, now())).fetchone()
            if pending:
                raise Fault('HANDOFF_EXISTS', 'A pending handoff already exists; consult status')
            identifier = str(uuid.uuid4())
            expires = (datetime.now(timezone.utc) + timedelta(seconds=args.ttl_seconds)).isoformat()
            db.execute('INSERT INTO handoffs VALUES (?, ?, ?, ?, ?, NULL)',
                       (identifier, current['revision'], recipient, 'open', expires))
            db.commit()
            return {'handoff_id': identifier, 'state': 'open', 'recipient': recipient,
                    'expires_at': expires, 'recipient_is_authentication': False, **state(db)}
        if args.command == 'accept':
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM handoffs WHERE id = ?', (args.id,)).fetchone()
            if row is None:
                raise Fault('HANDOFF_NOT_FOUND', 'No such handoff in this project')
            if row['recipient'] != args.recipient:
                raise Fault('WRONG_RECIPIENT', 'The receiver label differs from the intended handoff')
            if row['state'] != 'open':
                raise Fault('ALREADY_ACCEPTED', 'Handoff already consumed; consult receipt to recover')
            if row['expires_at'] <= now():
                raise Fault('HANDOFF_EXPIRED', 'Create a fresh handoff after reviewing current state')
            current = state(db)
            if current['revision'] != row['revision']:
                raise Fault('STALE_HANDOFF', 'A newer checkpoint exists; create a fresh handoff')
            if check_references(root, current)['issues']:
                raise Fault('EVIDENCE_CHANGED', 'References changed; the handoff remains unconsumed')
            db.execute('UPDATE handoffs SET state = ?, accepted_at = ? WHERE id = ? AND state = ?',
                       ('accepted', now(), args.id, 'open'))
            db.commit()
            return {'handoff_id': args.id, 'state': 'accepted', 'recipient': args.recipient,
                    'recipient_is_authentication': False, **state(db)}
    raise Fault('UNKNOWN_COMMAND', 'Unsupported command')


def main():
    # JSON consumers must receive UTF-8/LF regardless of the host's legacy
    # console or pipe encoding. Do not change the parent process environment.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='strict', newline='\n')
    try:
        args = parser().parse_args()
        print(wire({'ok': True, 'code': 'OK', 'data': execute(args)}))
        return 0
    except Fault as exc:
        print(wire({'ok': False, 'code': exc.code, 'data': None, 'error': exc.message}))
        return 2
    except (OSError, sqlite3.Error, ValueError):
        print(wire({'ok': False, 'code': 'IO_ERROR', 'data': None, 'error': 'Local operation failed; no success is claimed'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
