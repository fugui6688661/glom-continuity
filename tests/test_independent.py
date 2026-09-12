#!/usr/bin/env python3
"""Independent, public-CLI acceptance checks; no implementation or SQLite imports."""

from __future__ import annotations

import json
import hashlib
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


CLI = Path(__file__).resolve().parents[1] / "scripts" / "continuity.py"
REVIEWED_SHA256 = ""


def setUpModule():
    global REVIEWED_SHA256
    REVIEWED_SHA256 = hashlib.sha256(CLI.read_bytes()).hexdigest()
    print(f"IMPLEMENTATION_SHA256={REVIEWED_SHA256}", flush=True)


def tearDownModule():
    if hashlib.sha256(CLI.read_bytes()).hexdigest() != REVIEWED_SHA256:
        raise AssertionError("Implementation changed during this run; rerun against a stable revision")


class IndependentContinuityTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="continuity-independent-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / "Orchid 工作簿"
        self.project.mkdir()
        self.env = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}

    def cli(self, *args: str, project: Path | None = None):
        return subprocess.run(
            [sys.executable, "-B", str(CLI), "--project", str(project or self.project), *args],
            capture_output=True, text=True, encoding="utf-8", env=self.env,
            cwd=self.root, timeout=15,
        )

    def ok(self, *args: str, project: Path | None = None):
        result = self.cli(*args, project=project)
        self.assertEqual(result.returncode, 0, f"{args}: {result.stderr or result.stdout}")
        return result

    def initialize(self):
        return self.ok("init", "--name", "Orchid continuity review")

    def document(self, **overrides):
        evidence = self.project / "menu-ptBR.csv"
        if not evidence.exists():
            evidence.write_text("item,label\ntea,Chá\nRAW_SOURCE_DO_NOT_EXPORT\n", encoding="utf-8")
        document = {
            "objective": "Verify the Portuguese tea menu before release",
            "next_action": "Ask the next reviewer to inspect the accent in Chá",
            "constraints": ["Do not publish", "Do not upload original files"],
            "decisions": ["Tea label selected: Chá"],
            "unresolved": ["Second reviewer has not approved the menu"],
            "evidence": [{"path": "menu-ptBR.csv", "role": "input"}],
        }
        document.update(overrides)
        return document

    def save(self, document=None, revision=0):
        draft = self.project / "checkpoint-input.json"
        draft.write_text(json.dumps(document or self.document(), ensure_ascii=False), encoding="utf-8")
        return self.cli("checkpoint", "--from-file", str(draft), "--expect-revision", str(revision))

    def seeded(self, **overrides):
        self.initialize()
        document = self.document(**overrides)
        saved = self.save(document)
        self.assertEqual(saved.returncode, 0, saved.stdout + saved.stderr)
        return document

    def configuration_note(self, value):
        return {"objective": "Review configuration", "next_action": "Await review",
                "constraints": [], "decisions": [value], "unresolved": [], "evidence": []}

    def test_new_process_recognizes_initialized_project(self) -> None:
        created = self.initialize()
        status = self.ok("status")
        self.assertIn("Orchid continuity review", status.stdout)
        self.assertEqual(json.loads(created.stdout)["data"]["project_id"],
                         json.loads(status.stdout)["data"]["project_id"])
        self.assertIsNone(json.loads(status.stdout)["data"]["checkpoint"])
        self.assertNotEqual(self.cli("context").returncode, 0)

    def test_saved_work_resumes_in_fresh_process_without_exporting_source_body(self) -> None:
        document = self.seeded()
        restored = self.ok("context", "--max-chars", "4000")
        for field in ("objective", "next_action"):
            self.assertIn(document[field], restored.stdout)
        self.assertIn(document["unresolved"][0], restored.stdout)
        self.assertNotIn("RAW_SOURCE_DO_NOT_EXPORT", restored.stdout)
        self.assertLessEqual(len(restored.stdout), 4000)
        checked = json.loads(self.ok("check").stdout)["data"]
        self.assertEqual(checked["state"], "references_current")
        self.assertIs(checked["semantic_completion_verified"], False)
        exported = json.loads(self.ok("export", "--output", "review-bundle.json").stdout)["data"]
        self.assertIs(exported["contains_raw_evidence_files"], False)
        bundle = (self.project / "review-bundle.json").read_text(encoding="utf-8")
        self.assertNotIn("RAW_SOURCE_DO_NOT_EXPORT", bundle)
        self.assertIn(document["objective"], bundle)

    def test_same_size_same_mtime_source_change_is_flagged_and_blocks_offer(self) -> None:
        self.seeded()
        source = self.project / "menu-ptBR.csv"
        before = source.stat()
        source.write_bytes(source.read_bytes().replace(b"tea", b"pea"))
        os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(source.stat().st_size, before.st_size)
        current = json.loads(self.ok("context").stdout)["data"]
        self.assertEqual(current["check"]["state"], "needs_review")
        self.assertIs(current["check"]["semantic_completion_verified"], False)
        self.assertIn({"code": "CONTENT_CHANGED", "path": "menu-ptBR.csv"}, current["check"]["issues"])
        offered = self.cli("handoff", "--recipient", "reviewer-b", "--expect-revision", "1")
        self.assertNotEqual(offered.returncode, 0, offered.stdout)
        self.assertNotIn("Tea label selected: Chá", offered.stdout)

    def test_quoted_json_credential_is_rejected_before_becoming_recoverable(self) -> None:
        self.initialize()
        value = 'Configuration sample: {"password": "review-only-not-a-real-secret"}'
        result = self.save(self.configuration_note(value))
        details = ""
        if result.returncode == 0:
            recovered = json.loads(self.ok("context").stdout)["data"]["text"]
            self.ok("export", "--output", "credential-review.json")
            bundle = (self.project / "credential-review.json").read_text(encoding="utf-8")
            marker = "review-only-not-a-real-secret"
            details = (f"; recoverable={marker in recovered}; exported={marker in bundle}; "
                       f"revision={json.loads(self.ok('status').stdout)['data']['revision']}")
        self.assertNotEqual(result.returncode, 0, "Quoted JSON password accepted" + details)
        self.assertEqual(json.loads(self.ok("status").stdout)["data"]["revision"], 0)

    def test_credential_assignment_guard_control(self) -> None:
        self.initialize()
        result = self.save(self.configuration_note("password=review-only-not-a-real-secret"))
        self.assertNotEqual(result.returncode, 0, "Unquoted password assignment was accepted")
        self.assertEqual(json.loads(self.ok("status").stdout)["data"]["revision"], 0)

    def test_handoff_is_claimable_from_a_new_assistant_process(self) -> None:
        document = self.seeded()
        offered = self.ok("handoff", "--recipient", "reviewer-b", "--expect-revision", "1")
        offer = json.loads(offered.stdout)["data"]
        received = json.loads(self.ok("accept", "--id", offer["handoff_id"],
                                      "--recipient", "reviewer-b").stdout)["data"]
        self.assertEqual(received["state"], "accepted")
        self.assertIs(received["recipient_is_authentication"], False)
        self.assertEqual(received["checkpoint"]["objective"], document["objective"])
        receipt = json.loads(self.ok("receipt", "--id", offer["handoff_id"]).stdout)["data"]
        self.assertEqual(receipt["state"], "accepted")
        self.assertIs(receipt["external_actions_verified"], False)

    def test_small_budget_never_silently_loses_constraints(self) -> None:
        document = self.seeded(constraints=["Keep the full restriction: " + "约束🙂" * 160])
        for budget in (1, 512, 1600, 5000):
            with self.subTest(budget=budget):
                result = self.cli("context", "--max-chars", str(budget))
                if result.returncode == 0:
                    self.assertLessEqual(len(result.stdout), budget)
                    text = json.loads(result.stdout)["data"]["text"]
                    self.assertIn(document["constraints"][0], text)
                    self.assertIn(document["next_action"], text)
                else:
                    self.assertNotIn("text", json.loads(result.stdout).get("data") or {})

    def test_two_writers_cannot_silently_overwrite_or_mix_their_checkpoints(self) -> None:
        self.seeded()
        documents = [self.document(objective=f"Writer {name} objective", next_action=f"Next from {name}",
                                   constraints=[f"Only {name} constraint"]) for name in ("A", "B")]
        paths = []
        for number, document in enumerate(documents):
            path = self.project / f"writer-{number}.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            paths.append(path)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda path: self.cli("checkpoint", "--from-file", str(path),
                                                        "--expect-revision", "1"), paths))
        self.assertEqual(sorted(r.returncode for r in results), [0, 2])
        winner = next(i for i, result in enumerate(results) if result.returncode == 0)
        loser = results[1 - winner]
        self.assertEqual(json.loads(loser.stdout)["code"], "REVISION_CONFLICT")
        current = json.loads(self.ok("status").stdout)["data"]
        self.assertEqual(current["revision"], 2)
        for field in ("objective", "next_action", "constraints", "decisions", "unresolved"):
            self.assertEqual(current["checkpoint"][field], documents[winner][field])

    def test_old_offer_cannot_claim_a_new_checkpoint(self) -> None:
        self.seeded()
        offer = json.loads(self.ok("handoff", "--recipient", "b", "--expect-revision", "1").stdout)["data"]
        newer = self.document(objective="Review the coffee menu instead", next_action="Verify café accent")
        saved = self.save(newer, revision=1)
        self.assertEqual(saved.returncode, 0, saved.stdout)
        stale = self.cli("accept", "--id", offer["handoff_id"], "--recipient", "b")
        self.assertNotEqual(stale.returncode, 0, stale.stdout)
        self.assertEqual(json.loads(stale.stdout)["code"], "STALE_HANDOFF")
        fresh = json.loads(self.ok("handoff", "--recipient", "b", "--expect-revision", "2").stdout)["data"]
        accepted = json.loads(self.ok("accept", "--id", fresh["handoff_id"], "--recipient", "b").stdout)["data"]
        self.assertEqual(accepted["checkpoint"]["objective"], newer["objective"])

    def test_accepted_receipt_remains_history_after_progress_and_file_loss(self) -> None:
        self.seeded()
        offer = json.loads(self.ok("handoff", "--recipient", "b", "--expect-revision", "1").stdout)["data"]
        self.ok("accept", "--id", offer["handoff_id"], "--recipient", "b")
        saved = self.save(self.document(objective="Now review page two"), revision=1)
        self.assertEqual(saved.returncode, 0, saved.stdout)
        (self.project / "menu-ptBR.csv").unlink()
        receipt = json.loads(self.ok("receipt", "--id", offer["handoff_id"]).stdout)["data"]
        self.assertEqual((receipt["state"], receipt["revision"]), ("accepted", 1))
        self.assertIs(receipt["external_actions_verified"], False)
        current = json.loads(self.ok("context").stdout)["data"]
        self.assertEqual(current["revision"], 2)
        self.assertEqual(current["check"]["state"], "needs_review")

    def test_expired_offer_is_not_claimed_using_real_clock(self) -> None:
        self.seeded()
        offer = json.loads(self.ok("handoff", "--recipient", "b", "--expect-revision", "1",
                                  "--ttl-seconds", "1").stdout)["data"]
        time.sleep(1.1)
        result = self.cli("accept", "--id", offer["handoff_id"], "--recipient", "b")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(json.loads(result.stdout)["code"], "HANDOFF_EXPIRED")
        renewed = self.ok("handoff", "--recipient", "b", "--expect-revision", "1")
        self.assertNotEqual(json.loads(renewed.stdout)["data"]["handoff_id"], offer["handoff_id"])

    def test_missing_input_and_changed_artifact_are_reported_together(self) -> None:
        self.initialize()
        output = self.project / "review-result.txt"
        output.write_text("unchecked", encoding="utf-8")
        document = self.document(evidence=[{"path": "menu-ptBR.csv", "role": "input"},
                                           {"path": "review-result.txt", "role": "artifact"}])
        self.assertEqual(self.save(document).returncode, 0)
        (self.project / "menu-ptBR.csv").unlink()
        output.write_text("changed after checkpoint", encoding="utf-8")
        checked = json.loads(self.ok("check").stdout)["data"]
        issues = {(item["path"], item["code"]) for item in checked["issues"]}
        self.assertEqual(issues, {("menu-ptBR.csv", "MISSING_FILE"), ("review-result.txt", "CONTENT_CHANGED")})
        self.assertIs(checked["semantic_completion_verified"], False)

    def test_invalid_draft_does_not_advance_revision_or_poison_next_save(self) -> None:
        self.seeded()
        draft = self.project / "invalid.json"
        invalid = self.document(objective="This value must not replace current work")
        encoded = json.dumps(invalid)
        encoded = encoded[:-1] + ', "objective": "duplicate field"}'
        draft.write_text(encoded, encoding="utf-8")
        rejected = self.cli("checkpoint", "--from-file", str(draft), "--expect-revision", "1")
        self.assertEqual(rejected.returncode, 2, rejected.stdout)
        current = json.loads(self.ok("status").stdout)["data"]
        self.assertEqual(current["revision"], 1)
        self.assertNotEqual(current["checkpoint"]["objective"], invalid["objective"])
        saved = self.save(self.document(next_action="Explicit new review step"), revision=1)
        self.assertEqual(saved.returncode, 0, saved.stdout)
        self.assertEqual(json.loads(self.ok("status").stdout)["data"]["revision"], 2)

    def test_binary_and_instruction_like_file_bodies_stay_out_of_review_bundle(self) -> None:
        self.initialize()
        marker = self.root / "must-not-exist"
        raw = self.project / "raw-media.bin"
        raw.write_bytes(b"\x00\xffBINARY_PAYLOAD_NOT_FOR_EXPORT\x00" * 128)
        instruction = self.project / "instructions.txt"
        instruction.write_text(f"RAW_INSTRUCTION_NOT_FOR_EXPORT\ntouch '{marker}'\n", encoding="utf-8")
        document = self.document(evidence=[{"path": raw.name, "role": "input"},
                                           {"path": instruction.name, "role": "input"}])
        self.assertEqual(self.save(document).returncode, 0)
        restored = self.ok("context")
        self.ok("export", "--output", "binary-review.json")
        bundle = json.loads((self.project / "binary-review.json").read_text(encoding="utf-8"))
        self.assertEqual({item["path"] for item in bundle["checkpoint"]["evidence"]}, {raw.name, instruction.name})
        all_output = restored.stdout + json.dumps(bundle)
        self.assertNotIn("BINARY_PAYLOAD_NOT_FOR_EXPORT", all_output)
        self.assertNotIn("RAW_INSTRUCTION_NOT_FOR_EXPORT", all_output)
        self.assertFalse(marker.exists())
        self.assertIs(bundle["grants_permission"], False)

    def test_oauth_client_secret_is_rejected_before_recovery(self) -> None:
        self.initialize()
        document = self.configuration_note("client_secret=synthetic-review-fixture-only")
        result = self.save(document)
        details = ""
        if result.returncode == 0:
            restored = self.ok("context").stdout
            details = f"; recoverable={'synthetic-review-fixture-only' in restored}"
        self.assertNotEqual(result.returncode, 0, "OAuth client_secret accepted" + details)

    def test_accidental_outside_draft_or_reference_cannot_change_this_project(self) -> None:
        self.initialize()
        outside = self.root / "other-project-note.json"
        outside.write_text(json.dumps(self.document()), encoding="utf-8")
        result = self.cli("checkpoint", "--from-file", str(outside), "--expect-revision", "0")
        self.assertEqual(result.returncode, 2, result.stdout)
        reference = self.document(evidence=[{"path": "../other-project-note.json", "role": "input"}])
        result = self.save(reference)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(json.loads(self.ok("status").stdout)["data"]["revision"], 0)

    def test_named_credential_files_are_not_collected_as_evidence(self) -> None:
        self.initialize()
        for name in (".env", "credentials.json", ".ssh/id_rsa"):
            with self.subTest(path=name):
                source = self.project / name
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("SYNTHETIC_PRIVATE_FILE_MARKER", encoding="utf-8")
                result = self.save(self.document(evidence=[{"path": name, "role": "input"}]))
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertNotIn("SYNTHETIC_PRIVATE_FILE_MARKER", result.stdout + result.stderr)
                self.assertEqual(json.loads(self.ok("status").stdout)["data"]["revision"], 0)


if __name__ == "__main__":
    unittest.main()
