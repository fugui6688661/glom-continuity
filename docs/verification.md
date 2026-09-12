# Verification record / 实测记录

Date: 2026-09-12. This records distinct tests, not a universal compatibility badge. Source, protocol, real model behavior, package validation, and public distribution are separate claims.

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

## Still unverified

- A full real-agent save→handoff→different vendor→continue→save cycle.
- Other MCP hosts, automatic Skill discovery, Windows/Linux physical machines.
- Competitor outcome comparisons, external-user onboarding, retention, or token savings.
- Abrupt power loss, full-disk behavior, Windows ACL/crash recovery, hostile same-user filesystem races, remote authentication and synchronization. The bounded macOS corruption/backup/SIGKILL cases above are tested, not universal recovery.
- Public release and marketplace/PyPI installation.

Only promote a row when its specific test has a result. A protocol pass does not fill a model-behavior row; a real-model result does not authorize release or prove overall superiority.

## Release decision (not a runtime test)

On 2026-09-12 the owner confirmed `fugui6688661/glom-continuity` as the public repository target and approved the [MIT License](../LICENSE). This resolves the owner/license decision only. It does not establish repository availability, publication, or any of the unverified behavior above. Earlier archives and their test provenance remain unchanged.
