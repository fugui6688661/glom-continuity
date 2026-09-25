# Native Harness controls — development candidate

This Alpha.7 wrapper is **not in Alpha.6**. It has been exercised through
the installed DeepSeek Harness 0.1.5-rc.1 command, settings and AgentLoop APIs.
Separate installed-command UI checks now cover project selection, visible
controls, normal process restart and detachment in a fresh managed home; see
[the validation record](../../docs/managed-host-validation.md). Ordinary-profile
installation, abrupt-crash guarantees and other runtime versions remain unverified.

## Packaged bundle preparation

The development wheel includes the Python recovery runtime and both Harness
entries. `glom-continuity-harness` provides `preflight`, `install`, and `status`.
Here, **install stages files only**: it does not start Harness, change a profile,
read a key, enable memory, or call a model. It is not the finished desktop installer.

Choose an existing initialized Continuity project and copy its project ID from
`/absolute/recaloom-venv/bin/glom-continuity --project /path/to/project status`. Choose an already installed,
trusted Harness SDK. This candidate only accepts 0.1.5-rc.1 and its checked peer
versions; it does not download another runtime or infer compatibility with a
newer release. Create a private parent directory (mode 0700) for the new bundle,
outside the project. Then run:

Use the absolute path of your development-wheel venv below; it need not be
activated or added to PATH. Replace `/absolute/recaloom-venv` with its actual
location. An Alpha.6 installation does not supply this new installer. For a
source ZIP, use `python3 -B /absolute/source/scripts/continuity.py` for project
status and `python3 -B /absolute/source/scripts/harness_install.py` for the
installer, followed by the same arguments. Use Python 3.10+; a ZIP extraction
does not install console commands.

```sh
/absolute/recaloom-venv/bin/glom-continuity-harness preflight \
  --directory /path/to/private-parent/harness-bundle \
  --project /path/to/project --project-id PROJECT_ID \
  --sdk-node-modules /path/to/trusted-sdk/node_modules
```

Replace `preflight` with `install` using the same arguments to stage a fresh
bundle. Run the same executable with `status --directory /path/to/private-parent/harness-bundle` to verify its
recorded file hashes, SDK binding and project identity. Paths containing spaces
must be quoted in a shell. This preparation command currently supports POSIX
filesystems only; Windows installation has not been validated.

Success reports `staged_not_activated`, with `host_state: not_inspected`. The
generated `overlay.json` describes two entries for a separately managed host.
Do not patch it into an everyday profile merely because staging passed. The
development [managed-host CLI](managed-host.md) adds explicit creation, foreground
launch, status, safe stop and detachment in a separate owned home. This is not an
ordinary-profile installer, a file-deleting uninstaller or a public release.
The SDK version checks and local hash manifest detect compatibility drift or
changed files; neither authenticates a publisher nor sandboxes trusted code.

Existing destinations are never overwritten. Interrupted staging leaves the
partial directory in place and cannot report ready without the final manifest.
Status does not repair modified files. No installer command deletes projects,
settings or chats. Removing the Python package does not remove a previously
staged bundle; do not remove any bundle while a host is using it.

## User-facing behavior

After a trusted installer binds one initialized Continuity project, the native
Harness command picker can discover `/recaloom`:

| Command | Effect |
| --- | --- |
| `/recaloom status` | Current binding, enabled/paused state and last recovery result. |
| `/recaloom resume` | Enable subsequent automatic reads for this exact project. |
| `/recaloom pause` | Immediately stop new recovery and persist the paused preference. |

Commands do not ask a model, save project memory, or replay a prompt. The first
mount is paused until a human enables it. A persisted activation is bound to the
canonical project root **and** project ID; changing either does not inherit it.
This is a single-project wrapper, not a multi-project authorization manager.

Pause stops future additions, not context already in a conversation. Disabling
the whole Loader row removes the command too; `/recaloom resume` cannot reload
an uninstalled plugin. Removing the wrapper leaves project records intact.

## Installation boundary

The native entry is `native-plugin.mjs`, next to `automatic-recovery.mjs`. It uses
the host's `@deepseek-ai/schemastery` and `@deepseek-ai/dsh-llm`; resolve these from
the audited Harness installation, not a second downloaded Cordis runtime.
The host must supply the `commands` and writable `settings` services.

Trusted composition config contains absolute `python`, `recovery`, and `project`
paths plus the real `projectId`. None of these can be set by retrieved notes or
slash-command arguments. Keep the wrapper and Python code outside an untrusted
project. Loader overlays execute trusted code and are **not** a sandbox.

Only `{enabled, binding}` is stored in the dedicated `recaloom-recovery` settings
namespace. No model key, checkpoint body or conversation history is copied there.
The binding hash is an identity fence, not a secret or a cryptographic permission.
The native settings page does not automatically render arbitrary namespaces;
this wrapper supplies commands, **not** a custom toggle card.

The currently inspected local launcher uses official `dsh web` in a standalone
browser window. That is distinct from both community and official Electron
clients. An installer for one must not silently modify another's profile.
Do not use the ordinary profile as a keyless test fixture.

## Failure and concurrency

An own recovery failure becomes a short native terminal error, with a stable
code and a reminder to check `/recaloom status`. It does not fabricate an
assistant reply or include raw stderr, memory text, or an exception cause.
An upstream/downstream rejection is not mislabeled as a Recaloom failure.
Cancellation keeps its normal cancellation semantics.

Control writes carry the public settings revision read when the human command
was accepted. Stale queued activation cannot overwrite newer settings. A
separate intent generation prevents an older resume from clearing a newer
pause. The namespace owner remains alive while pending commands drain, allowing
a cancelled activation to persist its compensating pause before plugin teardown.

A failed settings write keeps this attachment paused and reports failure; it
does not claim the preference reached disk. Abrupt process termination or a disk
failure between commits is not a distributed transaction, and no blanket
crash-atomic authorization claim is made. Inspect settings after such a failure.
The local settings provider and installed code are trusted host components.

## Trusted removal barrier

An in-process supervisor may call `ctx.recaloomLifecycle.prepareRemoval()` before
stopping a managed host. It fences new activation, drains accepted control
writes and recovery subprocesses, then persists `enabled: false`. Settings
validation also rejects new activation through other public Settings clients.
Only a resolved receipt plus current `status().readyForRemoval` establishes a
quiesced attachment; the receipt alone is not permanent authorization.

Persistence failure rejects the prepare call and leaves the live reader paused.
An explicit retry can save the pause. Teardown still unregisters the namespace
if a concurrent save fails; it does not turn that failure into successful safe
removal. A restart after failed persistence may still observe the previously
saved activation. Stop and inspect that condition before removing any files.

This service is not an HTTP endpoint, model tool, file deletion operation or
finished uninstall command. The supervisor must still verify the host exited
and preserve user projects, chats and unrelated profile configuration. External
same-user file edits, process crashes and modified trusted SDK code are outside
this in-process barrier's guarantee.

## Reproduce the native seams

Use the same explicit installed `CONTINUITY_DSH_PACKAGE` and
`CONTINUITY_TEST_PYTHON` as the [core adapter tests](automatic-recovery.md).
Run `node --test tests/test_dsh_desktop_plugin.mjs` with network disabled around
the test process. It registers only a synthetic provider and uses temporary
project/settings files. Tests that require DSH skip when its explicit package
anchor is absent; a skip is not host compatibility evidence.

Persistent pause has been tested across plugin unload/remount and separate
official Web processes. Public managed CLI lifecycle tests are separate from
browser rendering and ordinary Desktop installation. Automatic saving remains
a different, unfinished capability.

## Web command feedback companion

Harness 0.1.5-rc.1 does not activate its chat view for command-only sessions.
The command may be recorded while the welcome page still looks unchanged.
Do not work around this by sending a fabricated prompt or calling a model.

The optional `client-notice/index.mjs` Loader entry has a separate browser half,
discovered through its own `package.json` (`dsh.client`, `exports["./client"]`).
Mount it alongside the native wrapper in a reviewed Web composition that already
contains the official command UI, session controller and conversation UI. This
is not an npm install instruction, an ordinary-profile installer, or a claim of
compatibility with every Harness release. The tiny dependency-free `client.js`
is source in the public module-registration format; no bundler step is required.

The companion subscribes to the browser's public `command/executed` event and
sends the returned text to the originating session's input notice. Successful
status is inline; a command error uses the host's error notice. No prompt,
assistant message, model call, memory write or additional Host command is made.
Other commands are ignored. A missing/closed originating session is ignored,
never redirected to a different current session. The listener follows Cordis
plugin disposal. Host command records remain the durable source of the result.

These notices are local submission acknowledgments, not cross-client broadcasts.
They do not make a command-only session appear in the persistent chat sidebar.
Removing this companion alone leaves the native command/recovery wrapper loaded;
remove both Loader entries to uninstall both halves. Neither deletes memory.

Run `node --test tests/test_dsh_client_notice.mjs` for packaging and lifecycle
contracts. The routing tests use fake public service ports and real Cordis, not
real browser rendering; production Web discovery/rendering needs separate QA.
