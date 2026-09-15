# Verification record / 实测记录

This records distinct tests, not a universal compatibility badge. Source, protocol, real model behavior, package validation, and public distribution are separate claims. Older sections below retain their original dates and limitations.

## One-call recovery — 2026-09-15 (development dev3)

Development `0.1.0.dev3` adds read-only `resume` / `continuity_resume`: first-save state, reference checking, task-matched memories and pending-handoff reminders are available through one interface call. Existing context/checkpoint/receipt semantics remain. It does not initialize tracking, accept a handoff, execute a task or load itself in a new host conversation. A database read transaction keeps the saved project snapshot consistent; file checks are observations, not locks on later filesystem changes.

The first source regression passed **94 tests, zero skips, 37.441 seconds** on macOS arm64 / Python 3.12.14 / MCP 2.2.0. Seven CLI recovery cases and one real-stdio MCP case were added; old first-save and changed-input behaviors remain covered. This measures protocol behavior, not reduced user effort or a successful full model benchmark. A subsequent installed-command assertion also requires the packaged executable to expose resume; later candidate/CI evidence must identify the tested revision.

Independent documentation review found four onboarding gaps, including the dev2 tutorial pointing to incompatible Alpha.5 installation instructions and the Skill assuming portable script layout after wheel installation. Documentation is being corrected with explicit release-versus-development and portable-versus-installed routes. That review did not test the new runtime. This source is not a stable release; Alpha.5 assets do not contain project-memory or resume. Full matched-model comparison and external human first use remain release gates, not claims implied by 94 tests.

## Single-assistant project memory — 2026-09-15 (local dev2)

Runtime `0.1.0.dev2` adds explicitly registered project habits/workflows to the existing checkpoint and context interfaces. No second assistant or handoff is needed. Retrieval is literal keyword matching, not semantic search or automatic chat learning. This increment is not a published stable release; older public Alpha.5 packages do not contain it.

The source regression on macOS arm64 / Python 3.12.14 / MCP SDK 2.2.0 passed **86 tests, zero skips** in 36.420 seconds. The original 69 remain; 16 new CLI cases and one new real-stdio MCP case cover scoped recall, lifecycle, changed references, duplicate identities, bounds, plain-text safety and the synthetic walkthrough. These are behavioral checks, not model-efficiency measurements. No new Windows/Linux run or live model session is claimed for dev2.

A separate AI reviewer designed a fresh synthetic project from the public documentation and invoked only the CLI in new processes. Its original matrix was 52/54: the two apparent failures were review-script assumptions that a legacy context always includes `data.memory`. Read-only follow-up confirmed both ordinary input/artifact bodies stayed out of context; the original errors were retained, not relabeled as fixed product defects. Additional tests found a real issue: JSON-escaped lone Unicode surrogates could be saved, then make context fail. Main-thread tests reproduced it before a save-time validation fix. Both surrogate ranges now reject with `INVALID_INPUT` and a field name, retaining the prior checkpoint; valid supplementary-plane characters round-trip. The review is not external human first use.

Fixed CLI SHA-256: `df6d12b54a07224cd935d181cf7ccbfb6c856f71bdd889ad7fa4b5f36599f64f`. MCP SHA-256: `0191971f033b20c20ac92c3828e37a0aa9d7654996254253e790b736c5749789`. The reviewer initially tested the pre-fix CLI `44ec9229d16cfd82c3283453c2ae19510925cbd44d2f188ab14c9e650077e473`; that result is not silently attributed to the fix. Build manifests identify exact distribution contents; an earlier local candidate also retained a dev1 plugin label and is not the final dev2 candidate.

Run `python3 -B scripts/memory_demo.py --output ./memory-demo` from a clean dev2 package to replay seven real CLI subprocess calls using synthetic records. The output folder must not exist. This does not install a host hook or demonstrate fewer forgotten requirements in a real model conversation. Automatic new-chat loading, measured single-assistant multi-session benefit, full matched-model comparison and external human first use remain open.

## Stable preparation — 2026-09-15 (unpublished)

Development runtime `0.1.0.dev1` was fixed at `fc34543450613cc43f0ff014789b6dbad0bddce9`. The public download remains alpha.5. Later onboarding/documentation changes do not rewrite the fixed experiment or certify a stable release.

[CI run 34821893397](https://github.com/fugui6688661/glom-continuity/actions/runs/34821893397) tested that development commit: Linux Python 3.10/3.12 and macOS Python 3.12 each passed 69 tests, no skips; Windows Python 3.12 passed 61, with eight declared POSIX-only skips and no failures. All four dependency, preflight, test and smoke stages exited successfully. Independent local installation review also passed four delivery/installation cases and checked 79 packaged documentation links. Those are bounded automated checks, not human first use.

### Same-model pilot: incomplete, no winner

The pilot used manual Markdown, `agent-handoff-skill` at `ef01fa9db0ea0aab19141954644a1049da4da795`, and this development CLI. All used fresh DSH 0.1.5-rc.1 sdk-minimal sessions with official-provider alias `deepseek-flash`, low reasoning, synthetic order inputs, fixture-scoped local tools and no shell/network tools. Alias is not proof of the provider's hidden model revision. The fixture invoked real public CLI commands; this is not validation of the shipped MCP adapter in DSH.

Each session allowed at most 100,000 cumulative input tokens, 4,000 output tokens, 16 HTTP requests, 30 tool calls and 600 seconds, with no retries. The first segment stopped after manual D; the owner then explicitly authorized the previously unused slots. Only the outer stopping policy changed: failures stopped dependent sessions, not an unrelated arm. Prompts, data, runtime and per-session limits stayed frozen. The two segments and protocol deviations are retained, not presented as an unchanged or statistically conclusive benchmark.

| Arm | Actually attempted | Observed result | Not run |
| --- | --- | --- | --- |
| Manual Markdown | A, B, fresh A-return, changed-input D | Normal subtotal 74.20 and missing facts preserved; fresh A read the saved output. D saved a change/review report, then hit the 4,000-output cap before closeout. A had calculated totals early, departing from the planned save-only role. | None |
| agent-handoff-skill | A | Bootstrap ran, but the session exhausted its output allowance before completing the task-specific handoff. | B, A-return, D |
| Continuity CLI | A | Initialization succeeded. The assistant requested context before saving any checkpoint; the CLI correctly returned `NO_CHECKPOINT`. The fixture stopped further requests. | B, A-return, D |

The last client displayed a generic `TRANSPORT` error after the local stop. Its first failed receipt was `NO_CHECKPOINT`, followed by the test guard's `TRIAL_B_STOP`; this is not evidence that the Internet or provider was unavailable. No failed session was replayed and no dependent role was seeded with a maintainer-written answer.

Six sessions were attempted, not twelve completed: **157,291 input tokens, 17,145 output tokens, 46 HTTP requests, 41 tool calls, 110.95 seconds summed session time**. Actual billed amount is unknown. Short runtime and lower usage after an early failure are not efficiency wins. Raw logs include machine-local paths and remain private; these are maintainer-reported observations, not independently replayable public attestations.

This pilot did not establish a complete three-arm matched comparison, reduced re-explanation, token savings or superiority. The product Skill's first-save/restore routing was subsequently clarified; the frozen model pilot did not use that new Skill, so a later instruction check must be reported separately. External human first use and the stable-release decision remain open.

## Current alpha.5 evidence — 2026-09-14

The candidate's executable files are unchanged from commit `c3b9e4f75b530b9e061415672c503fbdf0a53253`. Later repository documentation is not a new model trial or a silently replaced archive.

- A maintainer-observed, synthetic Codex → DeepSeek Harness → fresh Codex recovery completed on macOS. B wrote an order summary, saved a new checkpoint and handed it back; a fresh A accepted and read the result. A separate AI reviewer recomputed the arithmetic. The known subtotal was 74.20; missing quantity, currency and tax remained unresolved, and original inputs stayed unchanged. Earlier startup/transport failures were retained: this was successful recovery, not an uninterrupted first attempt.
- Maintainer-recorded clients: Codex 0.154.0-alpha.6.2 / gpt-6-astra low; DSH 0.1.5-rc.1 / provider alias `deepseek-flash`, low. This does not attest a provider's hidden model revision. Raw local session logs are private, so this is a reported experiment, not publicly replayable client attestation.
- [CI run 34688280351](https://github.com/fugui6688661/glom-continuity/actions/runs/34688280351) tested that exact commit: Linux Python 3.10/3.12 and macOS Python 3.12 each passed 67 cases; Windows Python 3.12 passed 59 and explicitly skipped eight POSIX-only cases. All four also passed the synthetic smoke. No claim of Windows ACL, physical power-loss or all-workstation coverage.
- Independent AI review checked the fixed ZIP's 40 shipped files and reachable Git history against the distribution allowlist; 41 standard-library tests passed in a fresh local environment. Wheel RECORD entries and GitHub-redownloaded asset hashes were checked separately. AI review is not external human first use.
- Offline comparison exercised manual Markdown, this CLI and a fixed agent-handoff-skill revision with normal and changed-input cases. That measured protocol behavior only, not model quality, reduced re-explanation or token savings.

**Open:** external human first use, a complete matched-model comparison, ordinary Windows/Linux device experience, other MCP clients and automatic cross-computer synchronization. One real handoff retained stale prose in `next_action`; the receiver recovered using the current receipt and protocol. The tool cannot certify the truth or freshness of every saved sentence.

Use the [named release assets](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.5) and their SHA256SUMS. Public availability, when verified, does not promote any open test above to a pass.

## Historical record — 2026-09-12

## Real Codex trial: one resumed task

Environment: macOS 26.4.1 arm64; Python 3.12.14; official MCP Python SDK 2.2.0; Codex CLI 0.153.4. A new ephemeral Codex session used a project-bound stdio server with **read-only MCP tools**, a synthetic project, and a workspace-write sandbox for its output. No global MCP configuration was changed. The trial used the host's existing authorized login; the utility itself made no model calls.

The CLI first stored this task: prepare an order note from `source.txt`, preserve the source, and do not invent currency or tax. The real model then called `continuity_status`, `continuity_check`, and `continuity_context`, and wrote `order-note.md`.

Synthetic input:

```text
Units: 12
Unit price: 7
Currency: unconfirmed
```

Actual generated output, read back after the session:

```text
# Order note

Units: 12
Unit price: 7
Total: 12 × 7 = 84
Currency: explicitly unconfirmed.

Tax is not specified in the source; no tax has been assumed.
```

Observed: exit code 0; no timeout; three completed MCP tool calls; note exists; source hash unchanged. Elapsed 39.8 seconds includes model, host, and network overhead; it is not a benchmark or latency guarantee. This trial did **not** cover a second vendor, live-model checkpoint writes, acceptance, automatic Skill discovery, or the whole project lifecycle. The run's large host-context usage is not evidence of token savings.

Frozen provenance for that trial (before subsequent fixes/version changes):

| Item | SHA-256 |
|---|---|
| CLI source | `4c9ba687565ffa50b6298e4791f267da2fbe761002a3101a4955c0e8549d0751` |
| MCP source | `69715502d449254c7c6a39bebf3d4225798a478e785da9153eba5873f477cb97` |
| Synthetic source | `871e56254b8b9fba8a2066bbc06e29aa79aedf028aba7850f9db0475bc59ad37` |
| Produced order note | `fbf1fb2a93eb76572b95a0dc466459cae4b7156c54b8fa64c3693ef0f32e2842` |
| Retained private event log | `f3413a296bff443657d1b898dd6cffda6b09bbaacca7c9a0351f57bb2ef03248` |

Raw host logs stay with the maintainer; they contain local paths and are excluded from distribution. This sanitized record is a maintainer-reported experiment, not an independent host certification. The hashes distinguish tested source from later revisions; an unavailable private log is not presented as publicly reproducible evidence.

## Repeatable protocol tests

The existing 27 CLI public-interface tests cover state, bounded recovery, references, handoff/replay/conflict errors, secret-pattern regressions, package relocation, and the synthetic demo. MCP adds real stdio tests; the separate independent suite includes both SDK protocol modes, concurrency, lost responses, source drift, read-only exposure and hostile-shaped inputs. These tests do not call a model.

### Alpha.2 regression

On the environment above, the implementation thread ran **52 tests / 25.140 seconds / OK / no skips**: 27 CLI/delivery cases, 4 initial MCP cases, and 21 independently authored MCP cases. The independent reviewer then reran its unchanged 21 cases: **21 passed / 16.742 seconds / no skips**, against the same alpha.2 source hashes. Runtime is suite duration, not task speed. The original failed cases and report remain preserved locally.

Independent review initially produced 18 passes and 3 red cases among its 21 tests, representing two issues: nonregular JSON drafts could hang a writer (a burst also stalled status), and relative MCP draft paths depended on launch cwd and could save the wrong same-named draft. Both were reproduced before fixing. Alpha.2 rejects nonregular drafts with bounded reads and resolves MCP-relative draft paths from the bound project root. No red test was removed or marked expected-failure.

Tested alpha.2 source hashes:

- CLI: `4a2f98cca27dd7bd48641fd40f9aa92837cf21422fbc00cf4dd90c1c269b8324`
- MCP: `7037b78c4184888b3e420778e45172c11451473c7780aa2cb6396451045523db`

The earlier real-model trial used the pre-fix hashes listed above. This regression does not pretend that the new archive or another model received a new live trial.

From a clean extracted package, run:

```sh
python3 -B -m unittest discover -s tests -v
```

For MCP tests install the optional dependency first, as described in [MCP setup](../adapters/mcp.md). Without it, MCP cases skip and provide no MCP evidence. Package manifests fix which files were included; source-directory tests must not be attributed to an older archive.

### Alpha.3 installation and recovery regression

On 2026-09-12, the implementation thread ran **65 tests / 32.674 seconds / OK / no skips** on macOS arm64, Python 3.12.14, MCP SDK 2.2.0. This was the source tree, not yet an extracted release archive. The previous 52 cases are retained; one installation-lifecycle case and 12 independently authored recovery cases were added.

The installer case builds from the distribution allowlist, installs a wheel into a fresh virtual environment, invokes commands from outside the source directory, runs the synthetic demo, checks the clear optional-MCP-dependency failure, and uninstalls without deleting the project database. Before the fix it exposed an actual package-relative import failure in the MCP entry point. An installable command is not automatic registration with every assistant.

The independent recovery cases exercise truncated/corrupt storage rejection, incomplete and relocated stopped-write backups, write/read permission failures, and two observed SIGKILL windows. Both termination experiments actually killed a child process and reopened the project; they did not simulate a kill by simply closing a connection. Tests accept only a complete old or complete new revision at the journal window; a commit observed during partial stdout remains recoverable and a stale repeat save is rejected. This is not a power-loss or network-storage durability guarantee.

Frozen source for this 65-case regression:

- CLI: `74fe600e12d1e256927ed670dfb4499f908ce3a49907615a97c48a40a30a853f`
- MCP: `740a31e11d33ba1278a178e03eae136559fb1593f19a64485b270338bfa6697a`
- Recovery test: `3d9ee3ab4de8bf8cdf4ec359b01c4822dd186227d1353841740a9ead5b61f46d`

The independent reviewer first ran its 12 cases on the earlier alpha.2 CLI; the implementation thread subsequently reran all 65 on the hashes above. Neither run is a fresh model-behavior trial. [Private cross-platform CI design and exact skip policy](platform-validation.md) records the planned hosted-runner checks separately; no unrun platform is marked passed.

### First hosted matrix and alpha.4 fixes

Private [run 34687554263](https://github.com/fugui6688661/glom-continuity/actions/runs/34687554263), commit `6cbd4be5995df70bc4c0dde6dec5e73bcb290321`, tested alpha.3 in four hosted environments. Linux/Python3.12 and macOS/Python3.12 passed. Linux/Python3.10 failed one deep-JSON case; Windows/Python3.12 failed two raw-stdio cases, with eight explicitly reported POSIX skips. All four installed dependencies and passed the synthetic smoke. This is genuine platform evidence, including failures, not proof of all-platform readiness.

The alpha.4 candidate catches JSON recursion errors in the product, supplies the test wire peer's missing Windows system environment without forwarding credentials, uses the Python3.10-compatible timeout type, and fixes Git checkout line endings for byte-identical provenance. Original assertions and the eight-skip policy remain unchanged. A new matrix result is required before claiming these fixes passed.

### Second hosted matrix and legacy-encoding regression

Private [run 34687974481](https://github.com/fugui6688661/glom-continuity/actions/runs/34687974481), commit `7c911d5e23fb9d6789e7b39bdecbc27ecf8b39d8`, verified alpha.4: 65 passes each on Linux/Python3.10.21, Linux/Python3.12.14 and macOS/Python3.12.10; Windows/Python3.12.10 had 57 passes and the eight declared POSIX skips, no failures. All four summaries report identical CLI SHA-256 `e0fbc0eab770ee619ea4da46c3dd32d2b2f55c2657f17580566a2606eedc5dca`.

Subsequent two new public-boundary tests forced legacy pipe encodings: ASCII and CP1252 caused a Chinese-name initialization to report failure; GBK output was not UTF-8; the first demo also failed. Alpha.5 sets UTF-8/LF inside the CLI/demo process without changing OS settings. The two tests now pass locally (0.518s). The full suite contains 67 cases; alpha.5 still requires its own candidate and hosted regression. UTF-8/LF is the machine-output contract, not a promise that every terminal font can display every character.

## Still unverified at the 2026-09-12 snapshot

This preserves that date's status. See the dated sections above for later results; historical failures and open limits are retained.

- A full real-agent save→handoff→different vendor→continue→save cycle.
- Other MCP hosts, automatic Skill discovery, Windows/Linux physical machines.
- Competitor outcome comparisons, external-user onboarding, retention, or token savings.
- Abrupt power loss, full-disk behavior, Windows ACL/crash recovery, hostile same-user filesystem races, remote authentication and synchronization. The bounded macOS corruption/backup/SIGKILL cases above are tested, not universal recovery.
- Public release and marketplace/PyPI installation.

Only promote a row when its specific test has a result. A protocol pass does not fill a model-behavior row; a real-model result does not authorize release or prove overall superiority.

## Release decision (not a runtime test)

On 2026-09-12 the owner confirmed `fugui6688661/glom-continuity` as the public repository target and approved the [MIT License](../LICENSE). This resolves the owner/license decision only. It does not establish repository availability, publication, or any of the unverified behavior above. Earlier archives and their test provenance remain unchanged.
