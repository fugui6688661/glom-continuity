# Managed Harness: tested scope

Local development candidate, tested 2026-09-25. **Not included in published Alpha.6.**

The development runtime is now `0.1.0-alpha.7`; it is not yet published. The
historical UI checks below concern the earlier fixed runtime, not a fresh UI
acceptance of every later CI/documentation change. See the [CI lane split](platform-validation.md)
for the required fresh-SDK checks and the remaining hosted-platform validation.

## What was exercised

The tested runtime was the official DeepSeek Harness 0.1.5-rc.1 with Cordis 4.0.2,
Schemastery 3.18.2, Node 26.6.0 and Python 3.12.14 on macOS. A fresh virtual
environment installed the candidate wheel. Tests invoked the installed commands
from a directory unrelated to the source checkout.

The synthetic managed home contained no model key or imported private profile.
Host processes were restricted to loopback and Unix sockets by an OS-level test
sandbox. That test containment is not a sandbox feature supplied by this product.

| Layer | Observed result | What this does not prove |
| --- | --- | --- |
| Fixed-source checks | 141 Python and 34 Node tests passed, no skips in the configured local run | These counts overlap; not evidence of hosted multi-platform CI or competitive superiority |
| Installed command lifecycle | Create, readiness, duplicate-run refusal, wrong-run refusal, stop, terminal interrupt, detached restart and launcher loss checked against the official profile | Power-loss durability, arbitrary third-party runtimes or a Windows process-control adapter |
| Public browser entry | Installed `run --open` reached the authenticated official page; in-page project selection worked | Ordinary-profile migration or an Electron desktop installer |
| Native controls | Status, resume, pause and invalid-command feedback were visible without model calls | A model actually understanding or using recovered memory |
| Normal restart | Bound project remained; paused preference survived a new host process | Crash-atomic permission persistence |
| Detachment | Commands disappeared on restart; project records remained; folder picker still worked | Data deletion or an in-place reattachment workflow |

Separate earlier production-AgentLoop tests used a synthetic model to exercise
awaited recovery and refusal when input evidence changed. Those are host contract
tests, not paid-model quality benchmarks. The public-entry UI run did not send a
model prompt or save a new checkpoint.

## A failure that changed the implementation

The default local macOS picker started a native dialog that was not operable in
the observed session. The managed profile now disables the official auto-picker
and inserts the official browse server/client pair. This applies to fresh homes;
it does not rewrite existing homes or modify installed SDK packages.

An initial attempted overlay replacement did not work: the composition system
treats `name` as a matching guard. A failing runtime capability assertion caught
the still-native picker before the corrected disable/insert composition passed.
The capability field alone is not visual proof; project selection was checked
separately in the browser.

## Open limits

- After a normal process restart, the sidebar can retain a project while the
  central selector still shows “Select workspace”. Native controls display the
  bound project, but this UI inconsistency remains open. Do not infer successful
  model recovery from the sidebar or from the status command alone.
- The in-page picker uses the host user's filesystem access. A bound recovery
  project is not a filesystem sandbox for all other Harness features.
- The first attachment is paused. Resume enables bounded project reads, not
  automatic conversation saving or external-action permission.
- No ordinary-profile migration, background service, automatic update or
  reattach command is supplied. A new candidate must not overwrite a running home.
- Real host/UI checks are macOS-only. Codex, Claude Code, WorkBuddy, Doubao and
  other hosts require their own lifecycle adapters and acceptance records.
- The observed window was checked at 100% and 125% browser zoom, not across a
  full responsive/mobile matrix. Screenshots were inspected during the run but
  this repository does not include a durable screenshot set for this test.

The final public host status was stopped and the last process exited normally.
The synthetic project retained its initial revision with no checkpoint or pending
handoff. The owned browser tabs were closed. No ordinary user profile, private
chat, credential or GLOM application was changed by these checks.

## Reproduction entry points

Follow [managed host setup](../adapters/harness/managed-host.md) with a fresh
synthetic project and private parent directory. Source test commands and SDK
requirements are listed there and in [native controls](../adapters/harness/native-plugin.md).
The optional installed-SDK test must actually run to support a host claim; a
skipped test on a machine without that SDK is not a pass.

Hashes detect changed files; they do not establish semantic correctness or a
publisher's identity. This document records a bounded local result, not stable
release approval.
