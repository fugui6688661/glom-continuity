# Recaloom XS

**Continue a project in a fresh conversation, from the progress you actually saved.**

Recaloom XS is a local CLI for individuals and engineering teams. Save reviewed goals, constraints, decisions and next steps; let an authorized assistant restore them in a new session. Changed reference files require review before continuing. One assistant is enough—Harness and MCP are optional.

> **This page covers XS v0.2.0.** Download the assets from that named Release; if they are absent, do not substitute an older package. The stable product scope is project-level CLI saving and recovery. Optional host loading and event-save integrations have their own [support matrix](adapters/support-matrix.md).

[Installation details](INSTALL.md) · [First save and recovery](docs/first-use.md#english-checklist) · [中文](README.md)

## Install

You need **Python 3.10+ with venv / pip**, and a local terminal or assistant allowed to access your selected project. Run in your tools directory, using a new dedicated environment—not system Python. Stop at any failed step. Existing installations use the [upgrade procedure](INSTALL.md#upgrade-existing).

### macOS / Linux

Run after confirming that the [v0.2.0 Release](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.2.0) contains the matching wheel:

~~~sh
(
  set -eu
  if [ -e .recaloom-xs-0.2.0 ] || [ -L .recaloom-xs-0.2.0 ]; then
    echo "Environment exists; follow the upgrade guide." >&2
    exit 1
  fi
  python3 -m venv .recaloom-xs-0.2.0
  .recaloom-xs-0.2.0/bin/python -I -m pip install --no-index --no-deps "https://github.com/fugui6688661/glom-continuity/releases/download/v0.2.0/glom_continuity-0.2.0-py3-none-any.whl"
  .recaloom-xs-0.2.0/bin/python -I -B -m glom_continuity --version
  .recaloom-xs-0.2.0/bin/python -I -c "import sys; print(sys.executable)"
)
~~~

### Windows PowerShell

Confirm the matching wheel is attached to that Release before running. No activation script, administrator access or execution-policy change is needed:

~~~powershell
if (Test-Path -LiteralPath ".recaloom-xs-0.2.0") { throw "Environment exists; follow the upgrade guide." }
py -3 -m venv .recaloom-xs-0.2.0
if ($LASTEXITCODE -ne 0) { throw "Environment creation failed." }
& ".\.recaloom-xs-0.2.0\Scripts\python.exe" -I -m pip install --no-index --no-deps "https://github.com/fugui6688661/glom-continuity/releases/download/v0.2.0/glom_continuity-0.2.0-py3-none-any.whl"
if ($LASTEXITCODE -ne 0) { throw "Installation failed; preserve the environment for diagnosis." }
& ".\.recaloom-xs-0.2.0\Scripts\python.exe" -I -B -m glom_continuity --version
if ($LASTEXITCODE -ne 0) { throw "Version check failed." }
& ".\.recaloom-xs-0.2.0\Scripts\python.exe" -I -c "import sys; print(sys.executable)"
~~~

Expect `0.2.0`. Keep the **absolute Python path** printed last for the assistant prompt below. If the asset is not yet published or unavailable, do not substitute an old wheel. A fixed wheel supplied by the maintainer can use the [local installation and SHA-256 check](INSTALL.md#wheel-install).

Windows supports the basic installation/CLI route. Safe automatic project-rule writes, moves and exchanges are not provided there; managed Harness and full descendant-process cleanup are not Windows support promises. See [platform scope](adapters/support-matrix.md).

## Copy this to your assistant

The `v0.2.0` wheel **includes its matching Skill and guide**. You do not need to find another copy. Replace the two bracketed values with absolute paths and give this to an assistant with local file and command access:

~~~text
Project: [the absolute project path I provide; do not guess cwd or scan other projects]
Tool Python: [the absolute Python path printed by the installation commands]

Always invoke this Python with -I -B -m glom_continuity.
First run --project <that project> doctor and inspect version 0.2.0, runtime and storage.
Only when data.usage.state=available, read the bundled guide at data.usage.skill_path.
Then run read-only resume and report the saved goal, constraints, unknowns, next step,
project ID and revision. If storage or a checkpoint is absent, explain that.
Do not initialize, save, accept a handoff or overwrite project instructions in this request.
Do not switch runtimes or delete a database to work around an error.
~~~

This is a check-and-restore entry point. **Nothing saved yet?** Use the [first-use checklist](docs/first-use.md#english-checklist) to authorize one synthetic save, then open a new conversation and verify recovery without pasting the old requirements. Installing the tool neither makes every host load it automatically nor enables automatic saving.

## What you can do

- **Save / restore:** `checkpoint` records reviewed progress; `resume` restores it and checks references.
- **Project habits and workflows:** [Project memory](docs/project-memory.md) stores confirmed preferences and selects them by keywords. It does not import private chats or train a model.
- **Team handoff:** `handoff` / `accept` / `receipt` record a handoff; [return-work](docs/result-return.md) links actual artifacts. Both participants need authorized access to the same project. You relay instructions; this is not automatic cross-device sync or model scheduling.
- **Less repeated setup:** after the first checkpoint, review a `setup` binding card or [configure the selected host's project entry](INSTALL.md#project-entry). Preview integration into existing rules; never overwrite user content.

MCP, Harness and event saving are [optional integrations](INSTALL.md#optional-hosts), not installation prerequisites. The [support matrix](adapters/support-matrix.md) and [verification record](docs/verification.md) separate hosts, versions, systems and open checks. A bounded native-host pilot is not a universal capability.

## Data, cost and removal

The base CLI has no third-party runtime dependencies, model calls or project uploads, and needs no model account. Installation downloads use the network; optional MCP needs its SDK. Context read by a cloud assistant remains subject to that service's privacy and billing rules.

State lives in the project's `.continuity/state.sqlite3`; original files stay in place. Do not include secrets or unauthorized private material. Drafts, exports and binding cards can also be sensitive. Stop writers before backing up the entire `.continuity/` and referenced files together; do not cloud-sync a database with concurrent writers.

[Upgrade](INSTALL.md#upgrade-existing) while preserving the project and old runtime. For [removal](INSTALL.md#preserve-data-removal), verify entry deactivation before uninstalling the dedicated package; retain user rules and project memory. Never remove a whole `AGENTS.md`, rules directory or database.

## Older versions and evidence

The repository, package, commands and storage keep their `glom-continuity` compatibility names. Do not `init` an existing project again. Historical [Alpha.7](INSTALL.md#public-alpha7) retains its original assets and behavior, without XS bundled-guide or project-entry commands. Updated documentation does not upgrade an old installation.

Matching fingerprints do not establish content quality; recovery, acceptance and result registration do not replace work review. There is no general claim of external human first-use success, token savings or competitive superiority, nor a guarantee of encrypted storage, authenticated identity, remote HTTP access or all-platform automatic memory. [Security boundaries](SECURITY.md)

[Redacted trial feedback](https://github.com/fugui6688661/glom-continuity/issues/new?template=field_trial.yml) · [Reusable project workflows](docs/field-lessons.md#english-summary) · [Provenance](PROVENANCE.md) · [MIT License](LICENSE)
