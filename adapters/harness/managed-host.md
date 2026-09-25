# A separate Harness home for Recaloom

Alpha.7 feature, **not included in Alpha.6**. These commands
start the installed official Harness Web runtime in an independently owned home.
They do not modify the Harness window or profile you already use.

## Start with an existing project

First stage a bundle with the [native installer](native-plugin.md). It requires
an initialized Continuity project and a trusted local Harness 0.1.5-rc.1 SDK.
The examples below use placeholders: replace the paths, project ID and Node
executable. Quote paths with spaces. Do not paste a model key into these commands.

The examples use the absolute path of the dedicated venv in which you installed
this development wheel. Replace `/absolute/recaloom-venv` with that location;
activation or a global PATH change is not required. The published Alpha.6 venv
does not contain these new commands. With a source ZIP instead, replace the
installer command with `python3 -B /absolute/source/scripts/harness_install.py`
and the host command with `python3 -B /absolute/source/scripts/harness_host.py`.
Use Python 3.10+; extracting a ZIP does not create console commands.

```sh
/absolute/recaloom-venv/bin/glom-continuity-harness install \
  --directory /path/to/private-parent/bundle \
  --project /path/to/project --project-id PROJECT_ID \
  --sdk-node-modules /path/to/trusted-sdk/node_modules

/absolute/recaloom-venv/bin/glom-continuity-host create \
  --home /path/to/private-parent/host \
  --bundle /path/to/private-parent/bundle \
  --node /path/to/node

/absolute/recaloom-venv/bin/glom-continuity-host run --home /path/to/private-parent/host --open
```

The parent directory must belong to you and be private (0700). Bundle and host
must be fresh, distinct locations outside the project. Keep the host path short:
the local control socket path must fit within 100 bytes. Node 24 or newer is
required. This launcher is POSIX-only; its real runtime checks were on macOS,
not Windows. The rest of the Continuity CLI has a separate support matrix.

`create` prepares the managed home without starting a server. `run` is a
foreground command: it stays in that terminal until the host exits. It is not a
login service or a background daemon. Without `--open`, it does not open a browser.
With `--open`, the official host handles its authenticated browser entry. Do not
substitute a bare localhost address: it may lack the required local authentication.
The installed command's authenticated opening and native controls were visually
checked on macOS with Harness 0.1.5-rc.1 on 2026-09-25. That bounded check does
not certify ordinary-profile installation or every host interaction; see the
[validation record](../../docs/managed-host-validation.md).

The managed Web profile uses the official in-page folder picker rather than
a separate OS dialog. `status.workspace_picker` reports its runtime capability
(`browse`), not proof that a person selected a workspace. Like the official
picker, it can browse the host filesystem as the signed-in local user; it is
not a filesystem sandbox. Recovery remains bound to the staged project only.
This composition applies to newly created homes; existing homes are not edited.

Known UI issue: after restarting the host, an existing project can remain in the
sidebar while the central selector still says “选择工作区” (Select workspace).
Do not infer the current workspace from that label. The native command reports
the exact staged project binding. If the active conversation's workspace does
not match it, recovery must not be treated as available for that conversation.

The host listens on a random loopback port. The launcher suppresses SDK output
so an authentication URL is not copied into logs. On startup failure it currently
returns a bounded error rather than a detailed SDK log; diagnostics are limited.
It passes an allowlisted environment and refuses a top-level host `.env` or
DSH-home `.env`. It does not copy your usual profile, keys, chats or subscriptions.
No model request is made by these lifecycle commands. Future model use through
the opened host requires its own configuration and may incur provider charges.

## Check, stop, or detach

Use another terminal, pointing at the **same exact home**:

```sh
/absolute/recaloom-venv/bin/glom-continuity-host status --home /path/to/private-parent/host
/absolute/recaloom-venv/bin/glom-continuity-host stop --home /path/to/private-parent/host
/absolute/recaloom-venv/bin/glom-continuity-host detach --home /path/to/private-parent/host
```

| Command/result | Meaning |
| --- | --- |
| `status: stopped` | The ownership lock is free. No current managed run owns it. |
| `status: running` | The private control channel confirmed this home and run identity. |
| `starting_or_unresponsive` | An owner still holds the lock; a replacement must not start. |
| `stop: stopped` without a receipt | The home was already stopped; no new pause persistence is claimed. |
| `stop: stopped` with `persisted_pause: true` | The pause barrier succeeded and all lock holders exited. |
| `stop: stopped` with `persisted_pause: false` | The detached host exited; there was no reader to pause. |
| `detach: detached` | The host stopped; future starts omit the native reader and UI notice. |

The first attachment starts paused. In the Harness command picker use
`/recaloom status`, `/recaloom resume` or `/recaloom pause`. Resume permits
bounded automatic recovery reads for the one bound project; it does **not**
automatically save each conversation, authorize external actions or certify a
task complete. Merely starting a server does not prove a model answered or used
the recovered information correctly.

Ctrl-C in the foreground terminal asks the launcher to use the same pause
barrier. The SDK child has its own session so it does not receive that terminal
signal directly. An early interrupt is queued until the controller becomes ready;
a timeout reports `STOP_PENDING`, never a forced-success stop. This is not a
guarantee for power loss, SIGKILL, closing every terminal or killing the SDK
process directly. If only the launcher crashes, the child retains its ownership
lock and remains reachable through `status` and `stop`.

Detachment is **not deletion**. It preserves project records, host settings and
chats, and keeps the small lifecycle controller available. There is no reattach
or in-place upgrade command yet. Do not manually remove a live bundle or edit
its composition to work around a refusal. Review an explicit migration before
using an existing managed home with another candidate version.

## Failure and trust boundaries

- A second run fails with `HOST_BUSY`; stale PID files are never used to kill a
  process. The actual private socket response and inherited file lock are used.
- A wrong home/run identity is refused. Only an owned, connection-refused stale
  socket is removed while its lock is held. Unrecognized objects are left alone.
- Failed or invalidated pause receipts do not authorize exit. A later explicit
  stop request can retry persistence. Check status before removing anything.
- Stopped-after-detach does not claim that a missing attachment saved a pause.
- Private paths and hashes detect accidental changes, not malicious code running
  as your own user. The Node executable, installed SDK and host profile are trusted.
  Version metadata is not publisher authentication; this is not a code sandbox.
- This candidate has no ordinary-profile migration, automatic saving, Windows
  process-control adapter, telemetry collection or new public release.

## Reproduce the lifecycle checks

Set `CONTINUITY_DSH_PACKAGE` to the trusted installed SDK's `dsh/package.json`
and run `python -m unittest discover -s tests -p test_managed_host.py -v`.
Restrict that process and its children to loopback and Unix sockets at the OS
level; the test creates a fresh synthetic project and does not configure a model.
The test covers creation, readiness, duplicate-run refusal, wrong-identity
refusal, normal stop, terminal-group Ctrl-C, detached restart and launcher death.

`node --test tests/test_managed_control.mjs` checks stale removal-receipt retry
over a real Unix socket with fake public host services. It is not an additional
full SDK test. Neither suite is a visual browser test or semantic model benchmark.
