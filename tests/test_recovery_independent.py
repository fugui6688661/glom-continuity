#!/usr/bin/env python3
"""Bounded recovery checks through nine public CLI commands, synthetic data only.

No implementation imports or SQLite connections. Storage bytes are touched only
to inject faults/copy stopped backups; application truth comes from the CLI.
Run this file directly with -B; optional unittest names select individual cases.
CONTINUITY_RECOVERY_EXPECTED_SHA256 optionally pins one review run; by default
only source stability during the run is required, not a historical source hash.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest


CLI = Path(__file__).resolve().parents[1] / "scripts" / "continuity.py"
START_SHA256 = None
PUBLIC_COMMANDS = {"init", "status", "check", "context", "checkpoint",
                   "handoff", "accept", "receipt", "export"}
FIELDS = ("objective", "next_action", "constraints", "decisions", "unresolved")
INPUT = "inputs/茶单.csv"


def emit(event, **data):
    print("RECOVERY_EVENT " + json.dumps({"event": event, **data}, ensure_ascii=False,
                                       sort_keys=True), flush=True)


def setUpModule():
    global START_SHA256
    START_SHA256 = hashlib.sha256(CLI.read_bytes()).hexdigest()
    expected = os.environ.get("CONTINUITY_RECOVERY_EXPECTED_SHA256") or None
    emit("implementation", sha256=START_SHA256, expected_sha256=expected, python=sys.version.split()[0])
    if expected is not None and START_SHA256 != expected:
        raise AssertionError("Implementation differs from explicitly requested review hash")


def tearDownModule():
    final = hashlib.sha256(CLI.read_bytes()).hexdigest()
    emit("implementation_end", sha256=final, unchanged=final == START_SHA256)
    if final != START_SHA256:
        raise AssertionError("Implementation changed during review")


class RecoveryIndependentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="continuity-recovery-independent-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / "原始 合成项目"
        self.project.mkdir()
        self.env = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONIOENCODING": "utf-8"}
        if os.name == "nt":
            # Allowlist OS startup/temp variables; never copy the whole environment
            # (API keys, provider tokens, proxy credentials, PYTHONPATH, etc.).
            required = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
            self.env.update({key: value for key, value in os.environ.items()
                             if key.upper() in required})
        self.calls = []
        self.addCleanup(lambda: emit("commands", test=self._testMethodName, results=self.calls))

    def argv(self, *args, project=None):
        self.assertIn(args[0], PUBLIC_COMMANDS)
        target = project or self.project
        self.assertTrue(target.resolve().is_relative_to(self.root.resolve()))
        return [sys.executable, "-B", str(CLI), "--project", str(target), *args]

    def cli(self, *args, project=None, code="OK"):
        result = subprocess.run(self.argv(*args, project=project), cwd=self.root,
                                env=self.env, capture_output=True, text=True,
                                encoding="utf-8", timeout=15)
        try:
            response = json.loads(result.stdout)
        except ValueError:
            self.fail(f"{args}: non-JSON rc={result.returncode}; {result.stdout!r}; {result.stderr!r}")
        self.calls.append([args[0], result.returncode, response.get("code")])
        self.assertEqual(result.stderr, "", f"{args}: {result.stderr}")
        self.assertEqual(result.returncode, 0 if code == "OK" else 2, str(response))
        self.assertEqual(response.get("code"), code, str(response))
        self.assertIs(response.get("ok"), code == "OK", str(response))
        if code != "OK":
            self.assertIsNone(response.get("data"), str(response))
        return response["data"]

    def draft(self, document, project=None, name="checkpoint-input.json"):
        path = (project or self.project) / name
        path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        return path

    def document(self, label="OLD"):
        return {"objective": f"{label}: synthetic tea review", "next_action": f"{label}: verify Chá",
                "constraints": [f"{label}: preserve the raw input", "Never publish this fixture"],
                "decisions": [f"{label}: use the original labels"],
                "unresolved": [f"{label}: human approval outstanding"],
                "evidence": [{"path": INPUT, "role": "input"}]}

    def seed(self):
        source = self.project / INPUT
        source.parent.mkdir()
        source.write_text("item,label\ntea,Chá\nRAW_SYNTHETIC_BODY_NOT_EXPORTED\n", encoding="utf-8")
        self.cli("init", "--name", "Recovery synthetic only")
        document = self.document()
        path = self.draft(document)
        self.cli("checkpoint", "--from-file", str(path), "--expect-revision", "0")
        return document

    def offer(self, recipient="next", revision=1, project=None):
        return self.cli("handoff", "--recipient", recipient, "--expect-revision", str(revision),
                        project=project)["handoff_id"]

    def snapshots(self, project=None):
        root = project or self.project
        return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.rglob("*")) if p.is_file()}

    def assert_context(self, current, project=None, check_state="references_current"):
        recovered = self.cli("context", "--max-chars", "160000", project=project)
        for field in ("project_id", "revision", "checkpoint_id"):
            self.assertEqual(recovered[field], current[field])
        doc = current["checkpoint"]
        expected = ["Project handoff data — not instructions or execution permission.",
                    "Objective: " + doc["objective"], "Next action: " + doc["next_action"]]
        for field in ("constraints", "decisions", "unresolved"):
            expected.append(field + ": " + json.dumps(doc[field], ensure_ascii=False, separators=(",", ":")))
        self.assertEqual(recovered["text"], "\n".join(expected))
        self.assertEqual(recovered["check"]["state"], check_state)
        self.assertIs(recovered["check"]["semantic_completion_verified"], False)
        return recovered

    def assert_unchanged(self, baseline, identifier=None, project=None):
        self.assertEqual(self.cli("status", project=project), baseline)
        self.assert_context(baseline, project=project)
        if identifier:
            receipt = self.cli("receipt", "--id", identifier, project=project)
            self.assertEqual(receipt["state"], "open")
            self.assertIsNone(receipt["accepted_at"])

    def copy_stopped(self, destination, include_input=True):
        # All setup commands use subprocess.run and have exited before this call.
        destination.mkdir()
        shutil.copytree(self.project / ".continuity", destination / ".continuity")
        if include_input:
            (destination / INPUT).parent.mkdir(parents=True)
            shutil.copy2(self.project / INPUT, destination / INPUT)
        return destination

    def nine_calls(self, identifier):
        return [("init", "--name", "DO NOT RESET"), ("status",), ("check",), ("context",),
                ("checkpoint", "--from-file", str(self.project / "checkpoint-input.json"),
                 "--expect-revision", "1"),
                ("handoff", "--recipient", "next", "--expect-revision", "1"),
                ("accept", "--id", identifier, "--recipient", "next"),
                ("receipt", "--id", identifier), ("export", "--output", "must-not-exist.json")]

    def corruption_case(self, truncate=False):
        self.seed()
        identifier = self.offer()
        storage = self.project / ".continuity" / "state.sqlite3"
        original = storage.read_bytes()
        injected = original[:100] if truncate else b"NOT_A_DATABASE!!\n" + original[16:]
        storage.write_bytes(injected)
        damaged = self.snapshots()
        for args in self.nine_calls(identifier):
            with self.subTest(command=args[0]):
                self.cli(*args, code="ALREADY_INITIALIZED" if args[0] == "init" else "IO_ERROR")
                self.assertEqual(self.snapshots(), damaged, "Failure changed damaged storage or input files")
        emit("corruption", test=self._testMethodName, original_bytes=len(original),
             damaged_bytes=len(injected), damaged_sha256=hashlib.sha256(injected).hexdigest())

    def test_01_corrupt_header_does_not_reset_memory(self):
        self.corruption_case()

    def test_02_truncated_database_does_not_reset_memory(self):
        self.corruption_case(truncate=True)

    def test_03_missing_database_rejects_and_stopped_backup_recovers(self):
        self.seed()
        identifier = self.offer()
        baseline = self.cli("status")
        backup = self.copy_stopped(self.root / "stopped-backup")
        storage = self.project / ".continuity" / "state.sqlite3"
        storage.rename(self.root / "removed-synthetic-database")
        damaged = self.snapshots()
        for args in self.nine_calls(identifier):
            with self.subTest(command=args[0]):
                self.cli(*args, code="ALREADY_INITIALIZED" if args[0] == "init" else "NOT_INITIALIZED")
                self.assertEqual(self.snapshots(), damaged)
        restored = self.root / "restored-new-location"
        shutil.copytree(backup, restored)
        self.assert_unchanged(baseline, identifier, project=restored)
        self.assertEqual(self.cli("check", project=restored)["state"], "references_current")

    def test_04_failed_operations_preserve_memory_and_allow_next_save(self):
        self.seed()
        identifier = self.offer()
        baseline = self.cli("status")
        self.cli("export", "--output", "existing.json")
        bad = self.project / "invalid.json"
        bad.write_text('{"objective":', encoding="utf-8")
        snapshot = self.snapshots()
        cases = [(("checkpoint", "--from-file", str(self.project / "missing.json"),
                   "--expect-revision", "1"), "IO_ERROR"),
                 (("checkpoint", "--from-file", str(bad), "--expect-revision", "1"), "INVALID_INPUT"),
                 (("export", "--output", "existing.json"), "OUTPUT_EXISTS")]
        for args, code in cases:
            with self.subTest(code=code):
                self.cli(*args, code=code)
                self.assert_unchanged(baseline, identifier)
                self.assertEqual(self.snapshots(), snapshot)
        next_doc = self.document("NEW")
        path = self.draft(next_doc)
        updated = self.cli("checkpoint", "--from-file", str(path), "--expect-revision", "1")
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(updated["project_id"], baseline["project_id"])
        self.assert_context(updated)

    def test_05_stopped_copy_restores_identity_history_and_continuation(self):
        self.seed()
        old_id = self.offer("previous")
        self.cli("accept", "--id", old_id, "--recipient", "previous")
        path = self.draft(self.document("NEW"))
        self.cli("checkpoint", "--from-file", str(path), "--expect-revision", "1")
        next_id = self.offer(revision=2)
        baseline = self.cli("status")
        old_receipt = self.cli("receipt", "--id", old_id)
        source_snapshot = self.snapshots()
        restored = self.copy_stopped(self.root / "新位置 restored")
        # Removing the old pathname rules out a hidden dependency on that path.
        self.project.rename(self.root / "offline-original-do-not-use")
        self.assertFalse(self.project.exists())
        self.assert_unchanged(baseline, next_id, project=restored)
        self.assertEqual(self.cli("receipt", "--id", old_id, project=restored), old_receipt)
        self.assertEqual(self.cli("check", project=restored)["state"], "references_current")
        self.cli("export", "--output", "restored-review.json", project=restored)
        bundle_text = (restored / "restored-review.json").read_text(encoding="utf-8")
        bundle = json.loads(bundle_text)
        for field in ("project_id", "revision", "checkpoint_id", "checkpoint", "checkpoint_sha256", "recorded_at"):
            self.assertEqual(bundle[field], baseline[field])
        self.assertNotIn("RAW_SYNTHETIC_BODY_NOT_EXPORTED", bundle_text)
        self.cli("accept", "--id", next_id, "--recipient", "next", project=restored)
        self.cli("accept", "--id", next_id, "--recipient", "next", project=restored, code="ALREADY_ACCEPTED")
        path = self.draft(self.document("CONTINUED"), project=restored)
        current = self.cli("checkpoint", "--from-file", str(path), "--expect-revision", "2", project=restored)
        self.assertEqual(current["revision"], 3)
        self.assertEqual(current["project_id"], baseline["project_id"])
        self.assert_context(current, project=restored)
        self.assertEqual(self.cli("receipt", "--id", old_id, project=restored), old_receipt)
        self.assertEqual(self.snapshots(self.root / "offline-original-do-not-use"), source_snapshot)

    def test_06_backup_without_input_blocks_accept_until_input_restored(self):
        self.seed()
        identifier = self.offer()
        baseline = self.cli("status")
        restored = self.copy_stopped(self.root / "incomplete-backup", include_input=False)
        self.assertEqual(self.cli("status", project=restored), baseline)
        checked = self.cli("check", project=restored)
        self.assertEqual(checked["state"], "needs_review")
        self.assertEqual(checked["issues"], [{"path": INPUT, "code": "MISSING_FILE"}])
        self.assert_context(baseline, project=restored, check_state="needs_review")
        self.cli("accept", "--id", identifier, "--recipient", "next", project=restored, code="EVIDENCE_CHANGED")
        self.cli("handoff", "--recipient", "other", "--expect-revision", "1", project=restored, code="EVIDENCE_CHANGED")
        receipt = self.cli("receipt", "--id", identifier, project=restored)
        self.assertEqual(receipt["state"], "open")
        self.assertIsNone(receipt["accepted_at"])
        self.assertEqual(self.cli("status", project=restored), baseline)
        (restored / INPUT).parent.mkdir()
        shutil.copy2(self.project / INPUT, restored / INPUT)
        self.assertEqual(self.cli("check", project=restored)["state"], "references_current")
        self.cli("accept", "--id", identifier, "--recipient", "next", project=restored)
        self.assertEqual(self.cli("receipt", "--id", identifier, project=restored)["state"], "accepted")

    @contextmanager
    def permissions(self, changes):
        if os.name != "posix" or os.geteuid() == 0:
            self.skipTest("Requires an ordinary POSIX user; skip is not a permission pass")
        saved = [(path, stat.S_IMODE(path.stat().st_mode)) for path, _ in changes]
        try:
            for path, mode in changes:
                path.chmod(mode)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode)
                if not mode & 0o200:
                    self.assertFalse(os.access(path, os.W_OK), "Write-denial precondition not established")
            yield
        finally:
            for path, mode in reversed(saved):
                path.chmod(mode)

    def denied_writes(self, target):
        self.seed()
        identifier = self.offer()
        baseline = self.cli("status")
        path = self.draft(self.document("SHOULD NOT SAVE"))
        before = self.snapshots()
        protected = self.project / ".continuity"
        if target == "database":
            protected = protected / "state.sqlite3"
        with self.permissions([(protected, 0o400 if target == "database" else 0o500)]):
            self.assert_unchanged(baseline, identifier)
            self.assertEqual(self.cli("check")["state"], "references_current")
            for args in [("checkpoint", "--from-file", str(path), "--expect-revision", "1"),
                         ("handoff", "--recipient", "other", "--expect-revision", "1"),
                         ("accept", "--id", identifier, "--recipient", "next")]:
                with self.subTest(command=args[0]):
                    self.cli(*args, code="IO_ERROR")
                    self.assert_unchanged(baseline, identifier)
                    self.assertEqual(self.snapshots(), before)
        self.cli("accept", "--id", identifier, "--recipient", "next")
        updated = self.cli("checkpoint", "--from-file", str(path), "--expect-revision", "1")
        self.assertEqual(updated["revision"], 2)
        self.assert_context(updated)

    @unittest.skipUnless(os.name == "posix", "POSIX permissions only; Windows ACLs not verified")
    def test_07_read_only_database_preserves_reads_and_rejects_writes(self):
        self.denied_writes("database")

    @unittest.skipUnless(os.name == "posix", "POSIX permissions only; Windows ACLs not verified")
    def test_08_read_only_storage_directory_rejects_writes(self):
        self.denied_writes("directory")

    @unittest.skipUnless(os.name == "posix", "POSIX permissions only; Windows ACLs not verified")
    def test_09_read_only_project_reads_but_export_fails_without_partial_file(self):
        self.seed()
        identifier = self.offer()
        baseline = self.cli("status")
        before = self.snapshots()
        changes = [(p, 0o400) for p in self.project.rglob("*") if p.is_file()]
        changes += [(p, 0o500) for p in self.project.rglob("*") if p.is_dir()]
        changes.append((self.project, 0o500))
        with self.permissions(changes):
            self.assert_unchanged(baseline, identifier)
            self.assertEqual(self.cli("check")["state"], "references_current")
            self.cli("export", "--output", "no-permission.json", code="IO_ERROR")
            self.assertFalse((self.project / "no-permission.json").exists())
            self.assertEqual(self.snapshots(), before)
        self.cli("export", "--output", "permissions-restored.json")

    @unittest.skipUnless(os.name == "posix", "POSIX permissions only; Windows ACLs not verified")
    def test_10_unreadable_input_never_claims_current_or_consumes_handoff(self):
        self.seed()
        identifier = self.offer()
        baseline = self.cli("status")
        before = self.snapshots()
        with self.permissions([(self.project / INPUT, 0o000)]):
            self.assertFalse(os.access(self.project / INPUT, os.R_OK))
            checked = self.cli("check")
            self.assertEqual(checked["state"], "needs_review")
            self.assertEqual(checked["issues"], [{"path": INPUT, "code": "FILE_UNREADABLE"}])
            self.assert_context(baseline, check_state="needs_review")
            self.cli("handoff", "--recipient", "other", "--expect-revision", "1", code="EVIDENCE_CHANGED")
            self.cli("accept", "--id", identifier, "--recipient", "next", code="EVIDENCE_CHANGED")
            self.cli("checkpoint", "--from-file", str(self.project / "checkpoint-input.json"),
                     "--expect-revision", "1", code="IO_ERROR")
            self.assertEqual(self.cli("status"), baseline)
            receipt = self.cli("receipt", "--id", identifier)
            self.assertEqual(receipt["state"], "open")
            self.assertIsNone(receipt["accepted_at"])
        self.assertEqual(self.snapshots(), before)
        self.assertEqual(self.cli("check")["state"], "references_current")
        self.cli("accept", "--id", identifier, "--recipient", "next")

    def large_document(self):
        doc = self.document("NEW")
        doc["decisions"] = [f"NEW-{n:02d}-" + chr(65 + n) * 7890 for n in range(15)]
        return doc

    def killed_checkpoint(self, trigger, attempts):
        if os.name != "posix":
            self.skipTest("SIGKILL experiment is POSIX-only; not a cross-platform pass")
        self.seed()
        old = self.cli("status")
        document = self.large_document()
        for attempt in range(1, attempts + 1):
            candidate = self.copy_stopped(self.root / f"kill-{trigger}-{attempt}")
            draft = self.draft(document, project=candidate)
            self.assertLess(draft.stat().st_size, 128 * 1024)
            journal = candidate / ".continuity" / "state.sqlite3-journal"
            started = time.monotonic_ns()
            process = subprocess.Popen(self.argv("checkpoint", "--from-file", str(draft),
                                                 "--expect-revision", "1", project=candidate),
                                       cwd=self.root, env=self.env, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            observed_ns = signal_ns = signal_utc = journal_size = None
            poll_at_signal = None
            try:
                deadline = time.monotonic() + 5
                while process.poll() is None and time.monotonic() < deadline:
                    if trigger == "journal":
                        try:
                            journal_size = journal.stat().st_size
                            seen = True
                        except FileNotFoundError:
                            seen = False
                    else:
                        seen = bool(select.select([process.stdout], [], [], 0.001)[0])
                    if seen:
                        observed_ns = time.monotonic_ns()
                        poll_at_signal = process.poll()
                        if poll_at_signal is None:
                            signal_utc = datetime.now(timezone.utc).isoformat(timespec="microseconds")
                            signal_ns = time.monotonic_ns()
                            try:
                                os.kill(process.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                        break
                    if trigger == "journal":
                        time.sleep(0.0001)
                stdout, stderr = process.communicate(timeout=5)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)
            record = {"test": self._testMethodName, "attempt": attempt, "trigger": trigger,
                      "pid": process.pid, "signal": "SIGKILL" if signal_ns else None,
                      "signal_utc": signal_utc, "poll_at_signal": poll_at_signal,
                      "observed_after_start_ms": None if observed_ns is None else round((observed_ns - started) / 1e6, 3),
                      "signal_after_start_ms": None if signal_ns is None else round((signal_ns - started) / 1e6, 3),
                      "observation_to_signal_ms": None if signal_ns is None else round((signal_ns - observed_ns) / 1e6, 3),
                      "journal_bytes_observed": journal_size, "returncode": process.returncode,
                      "stdout_bytes": len(stdout), "stderr_bytes": len(stderr),
                      "draft_bytes": draft.stat().st_size, "power_failure_test": False}
            emit("termination", **record)
            self.assertEqual(stderr, b"")
            current = self.cli("status", project=candidate)
            self.assertEqual(current["project_id"], old["project_id"])
            self.assertIn(current["revision"], (1, 2), "Lost, reset or impossible revision after termination")
            if current["revision"] == 1:
                self.assertEqual(current, old, "Old revision was partially changed")
            else:
                self.assertNotEqual(current["checkpoint_id"], old["checkpoint_id"])
                for field in FIELDS:
                    self.assertEqual(current["checkpoint"][field], document[field], f"Mixed payload: {field}")
                self.assertEqual(current["checkpoint"]["evidence"], old["checkpoint"]["evidence"])
            self.assert_context(current, project=candidate)
            self.assertEqual(self.cli("check", project=candidate)["state"], "references_current")
            actual_kill = signal_ns is not None and process.returncode == -signal.SIGKILL
            emit("recovered", test=self._testMethodName, attempt=attempt,
                 revision=current["revision"], actual_sigkill=actual_kill)
            if actual_kill:
                if trigger == "stdout":
                    self.assertGreater(len(stdout), 0, "No stdout was actually emitted")
                    with self.assertRaises((ValueError, UnicodeError), msg="Expected interrupted, incomplete JSON response"):
                        json.loads(stdout)
                    self.assertEqual(current["revision"], 2)
                    self.cli("checkpoint", "--from-file", str(draft), "--expect-revision", "1",
                             project=candidate, code="REVISION_CONFLICT")
                    self.assertEqual(self.cli("status", project=candidate), current)
                resumed_doc = self.document("RESUMED")
                resumed_path = self.draft(resumed_doc, project=candidate, name="resumed.json")
                resumed = self.cli("checkpoint", "--from-file", str(resumed_path), "--expect-revision",
                                   str(current["revision"]), project=candidate)
                self.assertEqual(resumed["revision"], current["revision"] + 1)
                self.assert_context(resumed, project=candidate)
                return
        self.fail(f"Coverage gap: did not actually SIGKILL at {trigger} within {attempts} bounded attempts")

    @unittest.skipUnless(os.name == "posix", "SIGKILL is POSIX-only; not verified on Windows")
    def test_11_sigkill_after_journal_observation_recovers_complete_revision(self):
        self.killed_checkpoint("journal", attempts=8)

    @unittest.skipUnless(os.name == "posix", "SIGKILL is POSIX-only; not verified on Windows")
    def test_12_sigkill_during_stdout_recovers_committed_revision(self):
        self.killed_checkpoint("stdout", attempts=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
