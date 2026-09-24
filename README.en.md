# Recaloom

For people who keep working on a project with an AI assistant across conversations. Save the goal, constraints, decisions and next step in the project, then read them back in a fresh session. Check changed references before continuing. One assistant is enough.

Version v0.1.0-alpha.6 packages the existing dev4 features into a new preview, not a stable release. Use the named assets and checksums for the matching Release; check source, package and invoked-runtime versions separately.

[Install and first use](INSTALL.md) · [中文](README.md)

On macOS/Linux, run from your tools directory. `.recaloom-alpha6` must be a new directory; do not overwrite an environment or install into system Python:

```sh
python3 -m venv .recaloom-alpha6
.recaloom-alpha6/bin/python -m pip install --no-index --no-deps "https://github.com/fugui6688661/glom-continuity/releases/download/v0.1.0-alpha.6/glom_continuity-0.1.0a6-py3-none-any.whl"
.recaloom-alpha6/bin/glom-continuity --version
```

Requires Python 3.10+; expect `0.1.0-alpha.6`. If the named asset is unavailable, check its Release rather than substituting an older package. INSTALL covers Windows paths, local wheels and removal.

Try the synthetic demo with a new output directory:

```sh
.recaloom-alpha6/bin/glom-continuity-demo --output ./recaloom-demo
```

Read `recaloom-demo/演示结果.md`. This is a CLI protocol replay with no model calls, not a live-model relay.

## Start with one assistant

Give an authorized local assistant the absolute project path, the matching Skill's absolute path and the executable command prefix:

> Save this project's goal, constraints, unresolved questions and next step. In a fresh session, recover it read-only and tell me whether the referenced files changed.

Installation does not automatically load the project in every new conversation. Wheel users need the matching Skill separately; do not assume the environment contains `skills/` or `scripts/`. Use the [first-use checklist](docs/first-use.md#english-checklist) to save a synthetic project and recover it in a new session.

Alpha.6 includes these existing dev4 capabilities:

- `resume` reads project state, reference checks, selected habits or workflows, and pending handoffs in one call. It does not initialize, save or accept a handoff.
- [Project memory](docs/project-memory.md) stores reviewed habits and workflows, selected by literal keywords. It does not scan chats, train a model or guarantee complete recall. The detailed walkthrough is in Chinese.
- `doctor` identifies the invoked version, runtime location and project storage state. Successful diagnosis does not certify compatible data or authenticate the publisher.
- [Result return](docs/result-return.md) links a receiver's actual artifacts to an accepted handoff with `return-work`. Ordinary single-assistant checkpoints need no handoff.

## Add a second assistant when needed

A saves a checkpoint and creates a handoff. B gets authorized access to the same local project, checks it, accepts and works. For a bounded, single-stage return, B can register artifacts with `return-work`; A then reads the receipt and actual files. Changed inputs or an intervening revision require reconciliation, not a forced link to the old handoff.

You deliver the instructions to the other assistant. The tool does not send messages or launch models. Acceptance does not prove task completion, model identity or exactly-once external actions. A reviewed snapshot can support a manual handoff when shared project access is unavailable, but it provides no live checking or automatic writes.

Use the CLI with authorized local command access, or optional [MCP](adapters/mcp.md) with a local stdio host. MCP is read-only by default. A Skill or plugin manifest neither grants permissions nor proves installation. See the [interface contract](adapters/agent-neutral-contract.md) and [version matrix](adapters/support-matrix.md).

## Privacy, cost and removal

The base CLI has no third-party runtime dependencies, makes no model calls or project uploads, and needs no model account. Downloading the wheel uses the network; MCP requires a separately installed optional SDK. A cloud assistant may send recovered context to its model provider and apply its own pricing and privacy rules.

State lives in the selected project's `.continuity/state.sqlite3`; source files stay in place. Drafts, databases and exports may contain private text. Do not publish them without review. Stop all writers before backing up `.continuity/` and referenced files together. Do not cloud-sync a live SQLite database with concurrent writers.

To stop using Recaloom, remove only the Skill/client entries you added and close the associated MCP child process. Uninstall the wheel from its dedicated virtual environment or move the portable tool. Keep project memory if you want it. No autostart daemon is installed. [INSTALL](INSTALL.md) covers removal, backup and errors; [Security](SECURITY.md) describes the trust boundary.

## Existing users and tested limits

Formerly glom-continuity, Recaloom keeps the repository, package, command, MCP and project-storage identifiers compatible. Do not run `init` again on an existing project. Alpha.5 remains usable within its original scope; updated documentation does not add memory, `resume`, `doctor` or `return-work` to an installed old package. Follow INSTALL to upgrade.

The [verification record](docs/verification.md) preserves version-specific Codex → DeepSeek Harness → fresh Codex synthetic recovery, protocol tests, hosted CI, failures and open checks. These do not automatically certify the alpha.6 package. One historical relay retained stale `next_action` prose; recovered records still require review against the current task and receipt.

External human first use, a complete matched-model comparison, ordinary Windows/Linux device experience and other MCP hosts remain incompletely tested. No token-saving, reduced-rework or competitive-superiority result has been measured. A scripted demo replays the protocol, not two live models. MCP tests skipped without the optional SDK are not MCP passes.

Hash equality is not semantic correctness. This tool provides no semantic search, scheduling, authenticated identity, encrypted storage, remote HTTP service or automatic cross-device sync. It is not a sandbox against malicious processes running as the same OS user. Recovery and artifact registration do not replace review of the work.

[Reviewed project workflows](docs/field-lessons.md#english-summary) · [Redacted trial feedback](https://github.com/fugui6688661/glom-continuity/issues/new?template=field_trial.yml) · [Provenance and preview scope](PROVENANCE.md) · [Implementation record](IMPLEMENTATION.md)

## License

[MIT](LICENSE). Third-party dependencies retain their own licenses.
