# Lifecycle recovery boundary — unreleased

This is an adapter-development interface, not automatic setup for any host. The public Alpha.6 release does **not** include it. No host hook or global instruction file is installed by these commands. Automatic checkpoint saving is not implemented here.

`scripts/recovery.py` (installed entry point: `glom-continuity-recovery`) reuses the existing read-only `resume` core. It neither creates storage nor accepts handoffs, executes tools, calls models, edits native assistant memory, or starts a listener.

## Binding belongs to the authorized adapter

Pass these arguments on every invocation:

| Argument | Source and meaning |
|---|---|
| `--project` | Explicitly selected existing project root; no parent search |
| `--project-id` | Project identity recorded at user-approved binding, not rediscovered from the event |
| `--session-id` | **Current** host session identity, not a cached callback identity |
| `--generation` | Host-owned binding epoch; regenerate on project switch, pause, revocation, or re-enable |
| `--max-chars` | Whole successful JSON response plus LF budget; default 6000 characters, not tokens |

The adapter must select and trust the runtime before binding, keep binding metadata outside untrusted project instructions, and stop issuing calls while disabled. This core does not authenticate an OS user or maintain a consent database. These values and the receipt below are correlation checks, **not authorization tokens or a sandbox**. A same-user program that can call arbitrary CLI commands is outside a read-only tool boundary.

The current boundary requires the normalized event `cwd` to be exactly the bound root after canonicalization. A host working in a subdirectory must establish the authorized workspace root itself; the handler does not infer one. Two projects with the same display name still have different IDs. A copied database preserves its ID, so both canonical path and ID are checked; this is not proof of unique physical storage.

## 1. Prepare, without carrying project text in a queue

Run the command with action `prepare` and this JSON on UTF-8 stdin:

```json
{"event":"session_start","cwd":"/absolute/project","session_id":"current-session","generation":"current-epoch","query":"video"}
```

Allowed normalized events are `session_start`, `resume`, `compact`, and `before_turn`. Their presence here does not mean a particular host implements them. Stop/SessionEnd are not saves or completion signals.

The output uses the normal `{ok, code, data}` envelope. On success, `data.receipt` contains the bound target, checkpoint revision/ID, query, issue time, and runtime fingerprint. It contains no checkpoint body. Keep it transient. Do not inject the prepare response into model context.

The runtime fingerprint covers the handler/core source hashes, handler path and Python executable path; it detects ordinary installation drift, not malicious local replacement or dependency tampering. Successful shape/hash checks are not publisher authentication.

## 2. Deliver against the current session

Run action `deliver`, supplying **only** the receipt on stdin and freshly sampled current binding arguments. A receipt lasts 60 seconds; a future timestamp or wall-clock jump outside that window is rejected, not repaired. The handler reopens the bound project, rechecks references, and regenerates recall at delivery time. It does not return a cached context captured during prepare.

- A different target or binding epoch returns `TARGET_MISMATCH`.
- A replaced project identity returns `PROJECT_MISMATCH` before disclosing its checkpoint.
- A newer checkpoint returns `STALE_RECOVERY`.
- Changed/missing referenced files return `EVIDENCE_CHANGED`; use explicit `resume` for review, not an automatic retry.
- Expired receipts and changed runtime return `EXPIRED_RECOVERY` / `RUNTIME_CHANGED`.
- Expired or retired habits are not recovered from an old prepared result.
- Malformed JSON, duplicate fields or oversized input fail with no project data.
- A short output budget returns `BUDGET_TOO_SMALL`, with `data: null`; it never chops off constraints. Failure diagnostics have a fixed small shape and may exceed an impossibly small requested budget.

Successful delivery returns `data.target`, `data.context` and `delivery_state`. `empty` means the bound project has no checkpoint; `ready` means context can be reviewed, **not** that the work is complete or its next action is currently authorized. `context.check.semantic_completion_verified` remains false. Unreferenced planning stays explicitly `no_references` / `recorded_unverified`.

Repeated reads do not add revisions or consume handoffs. They can produce fresher reference and expiry observations. This is not an exactly-once model-context injection guarantee.

## Host-side obligations after delivery

Before injecting, atomically compare the returned target to the live session/binding epoch. Drop the result if the target changed or automation was paused. No subprocess can lock another application's active session. A host without a delivery-time barrier cannot claim deterministic automatic recovery merely because this command succeeds. DeepSeek Harness's detached SessionStart needs separate ordering validation.

Inject the complete structured context as **untrusted historical project data**, including reference state, constraints and unresolved issues. Do not extract only `text`, treat it as a new user/system instruction, execute its recorded next action, or regard `source` as authentication. This marking reduces ambiguity; it does not prove that any model is immune to prompt injection. Enforcement of external actions remains the host's responsibility.

Keep host framing within its own context budget in addition to this command's JSON character budget. Set a short process deadline; cancel timed-out work and display recovery unavailable rather than falling back to a previous project's cache. The command bounds input size but cannot guarantee wall-clock completion against every filesystem or a stdin stream that never closes. Reference checks can read up to the existing core's per-file limits; no real-host latency benchmark is claimed.

## Verification scope

`tests/test_automatic_recovery.py` uses the public subprocess boundary with synthetic projects. `tests/test_installation.py` builds an isolated wheel and exercises the installed entry point; uninstall preserves project state. Neither is a real Codex, Claude Code, DeepSeek Harness, WorkBuddy, or Doubao lifecycle test. Those integrations, trust prompts, automatic save, crash/compaction behavior and installation rollback are separate remaining gates.

No new schema, memory database, daemon, account, paid API call or global hooks file is needed for this boundary. Run `python -B scripts/recovery.py --help` to inspect arguments. For actual user setup, keep using the released [installation guide](../INSTALL.md) until a tested adapter and new release are published.
