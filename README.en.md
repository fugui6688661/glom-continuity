# glom-continuity

**Keep the project. Change the assistant.**

A local checkpoint and handoff tool for AI-assisted projects. Save goals, decisions, constraints, and the next action. Check whether referenced files have changed before accepting a handoff.

“The currency is unconfirmed. Do not delete source records.” Save those details with the next step so a fresh session can recover them. Changed inputs block the old handoff until reviewed.

[中文](README.md) · [MCP setup](adapters/mcp.md) · [Verification](docs/verification.md) · [Security](SECURITY.md)

**0.1.0-alpha.5 · Developer preview, not a stable release.** The local CLI, optional MCP adapter and Python entry points are available for experimentation. A real synthetic Codex → DeepSeek Harness → fresh Codex recovery has been completed. This does not establish universal host compatibility, competitive superiority or token savings.

[Download preview](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.5) · [Install](INSTALL.md) · [Report an issue](https://github.com/fugui6688661/glom-continuity/issues)

Use the release's named ZIP asset for first use, not GitHub's automatic Source code archive. The asset preserves the tested candidate bytes. Its publication-status prose is a packaging-time snapshot; see the [release notes](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.5) and [verification record](docs/verification.md) for later evidence and limitations.

See [installation and first use](INSTALL.md) for the portable demo and local wheel installation. Installing the base wheel does not call a model; a cloud assistant still applies its own pricing and privacy rules.

## Try it without an account

Extract the portable package. In its directory, with Python 3.10+:

```sh
python3 -B scripts/continuity.py --version
python3 -B scripts/smoke_demo.py --output ./continuity-demo
python3 -B scripts/continuity.py --project ./continuity-demo context --max-chars 6000
```

The CLI needs no dependencies or model calls. The demo generates synthetic inputs only. Use a new output directory: an existing one is never overwritten. Read `continuity-demo/演示结果.md`, `events.json`, and `handoff-review.json` for the recovered state, changed-input rejection, and duplicate-acceptance rejection. **This demo replays the CLI protocol, not two live models.** The separate Codex trial is documented in [verification](docs/verification.md).

Windows users can substitute `py -3`. Protocol and installation checks ran on a GitHub-hosted Windows runner; that is not validation of every physical Windows workstation. No PyPI/Homebrew installation is advertised before a package exists there.

## Choose an interface

| Host capability | Route | Evidence so far |
|---|---|---|
| Authorized local commands and project access | Portable CLI, optionally with the generic Skill | Local public-interface tests |
| Local MCP stdio | [Optional adapter](adapters/mcp.md), read-only by default | Protocol tests and one live Codex 0.153.4 session; other hosts unverified |
| File upload or text only | Reviewed JSON snapshot | Manual handoff, not live checking or database writes |
| Remote HTTP / another device | Future authenticated bridge | Not implemented |

Agent-neutral, without a vendor allowlist. Tool discovery, tool calls, and correct task continuation are separate checks. [Contract](adapters/agent-neutral-contract.md) · [Version matrix](adapters/support-matrix.md)

## Track your own project

Select an existing project directory; the tool can live elsewhere.

```sh
python3 -B scripts/continuity.py --project /absolute/project init --name "My project"
```

Create `checkpoint.json` **inside that project before running the save command**:

```json
{
  "objective": "Prepare the report without changing the source accounting rules",
  "next_action": "Confirm how missing records should be handled",
  "constraints": ["Do not delete raw records"],
  "decisions": ["Aggregate by month"],
  "unresolved": ["Currency is unconfirmed"],
  "evidence": []
}
```

```sh
python3 -B scripts/continuity.py --project /absolute/project checkpoint --from-file /absolute/project/checkpoint.json --expect-revision 0
python3 -B scripts/continuity.py --project /absolute/project context --max-chars 6000
```

This planning example has `no_references`, not verified artifacts. For an existing input use `[{"path":"input.csv","role":"input"}]`; use `artifact` for outputs. Paths are project-relative; the tool calculates hashes. Read `status.data.revision` before each later save. Reconcile conflicts rather than blindly retrying.

The [generic Skill](skills/project-continuity/SKILL.md) explains the workflow. A Skill alone does not provide execution access. Included Codex metadata and project templates are not automatically installed; existing instructions and global configuration are not overwritten.

## Handoff, receipt, export

`handoff --recipient reviewer --expect-revision 1` returns an ID. An authorized receiver uses the same project and runs `accept --id ID --recipient reviewer`, then `context`. `receipt --id ID` recovers the acceptance record after a lost response. Labels are not authenticated identities; no messages or model sessions are launched.

Changed references, stale revisions, expiry, and duplicate acceptance are rejected. Acceptance does not prove a model participated, a task is complete, or an external action ran exactly once.

`export --output review.json` creates a new review file in the project root without raw evidence contents. Authored text and filenames may still be sensitive. It is not a permission token, database import, or full backup.

## Privacy and removal

State lives in `<project>/.continuity/state.sqlite3`. Sources remain in place. Do not publish private checkpoints, drafts, or exports. The tool makes no model calls or uploads, **but a connected cloud assistant may send recovered context to its model provider**.

With all writers stopped, back up the entire `.continuity/` directory and referenced files, preserving relative paths. Restore to a new location, then run `status` and `check`. Do not cloud-sync a live SQLite database with concurrent writers.

To stop using it, remove only your added Skill/client entry, close the associated MCP child process, and verify it no longer loads in a new session. Move the installed tool files if desired. Keep project data. No autostart daemon is installed.

## Tests and limits

```sh
python3 -B -m unittest discover -s tests -v
```

MCP tests explicitly skip without the optional SDK. A skipped test is not a verified MCP integration; see [setup and test instructions](adapters/mcp.md).

`BUDGET_TOO_SMALL` requires a larger character budget, not dropped constraints. CLI success-stdout and complete MCP-result budgets are different; neither measures tokens. Changed inputs require review; revision conflicts require reconciliation. Never repair a failure by deleting the database and pretending recovery succeeded. Full behavior is in the [interface guide](adapters/README.md).

This is not a scheduler, semantic memory model, sandbox, authenticated identity system, encrypted store, remote sync service, or completion authority. Hash equality is not semantic correctness. Same OS-user filesystem access is trusted. [Security](SECURITY.md)

The completed live handoff and hosted CI have bounded evidence in the [verification record](docs/verification.md). External human first use, complete matched-model comparison and ordinary Windows/Linux device experience remain unverified. No token-saving, market-success, or competitor-superiority claim is made. [Preview scope and license](PROVENANCE.md)

## License

[MIT](LICENSE). Third-party dependencies retain their own licenses.
