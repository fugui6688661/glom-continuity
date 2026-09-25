# DeepSeek Harness: automatic read-only recovery candidate

Alpha.7 adapter, not included in Alpha.6. This is a small
host adapter, not a new memory store or a replacement for Harness.

## What has actually run

The installed `@deepseek-ai/dsh-agent-loop` **0.1.5-rc.1** ran a fresh synthetic
session with this adapter and a single in-memory model substitute. Its real
request pipeline received a saved project constraint before dispatch. Subsequent
unchanged recovery did not append the same context again. Pause, resume and
detach were exercised, including pause/detach from an outer middleware after
recovery returned but before admission. Cancellation after pre-step made no model
request; the next prompt still received memory.

This is **production core lifecycle evidence**, not Desktop installation, SDK
stdio, real model quality, disk-session resume or compaction acceptance. No
private history was loaded. The macOS test process and children ran under a
network-deny sandbox; no paid provider was registered. This test setup does not
make the adapter a security sandbox when used elsewhere.

## Integration boundary

`automatic-recovery.mjs` exports:

```js
const control = attachDshRecovery(ctx, {
  python: '/absolute/path/to/python',
  recovery: '/absolute/path/to/scripts/recovery.py',
  project: '/absolute/path/to/selected-project',
  projectId: 'the-id-reported-by-continuity-status',
}, createUserMessage); // from @deepseek-ai/dsh-llm

control.status(); // state and lastCode; no project text
control.pause();
control.resume();
control.dispose(); // irreversible for this attachment; does not delete project data
```

Use Node.js 22 or later and a compatible Python runtime. These arguments are
trusted installation configuration, never values supplied by a retrieved note.
The host must visibly bind and authorize the selected project before attachment.
This helper does **not** edit a Desktop profile or install a user-facing switch.
A Desktop installer, explicit binding UI and error display are still pending.
The separate [native wrapper candidate](native-plugin.md) now provides human
commands, persisted pause and sanitized terminal errors through the actual
Harness APIs. Ordinary-profile installation and browser acceptance remain
separate gates; this helper alone does not provide them.
The optional JS adapter ships as source in the candidate ZIP, not inside the
Python wheel; the wheel exposes only the shared recovery command.

The exact native event contract was checked against the installed version and
the [same-version official source](https://github.com/deepseek-ai/deepseek-harness/blob/183f08e9c6dde7e36cd2318eaee70b0da08fb35e/packages/core/agent/src/runtime-types.ts).
Its session-start notification is not an awaited startup barrier. This adapter
uses the awaited `agent/pre-step` waterfall and preserves downstream decisions.
The host still owns final admission: a later host middleware can reject or change
the offered batch. If the binding is disabled while our offer awaits admission,
the adapter cancels that host turn as well as its own reads. An empty downstream
batch is never turned into a request by memory alone. Compatibility with arbitrary
third-party middleware that ignores host cancellation is not claimed.

## Behavior and limits

- Canonical working directory must exactly match the bound project. No parent
  search, recursive project discovery, native chat database access or cloud sync.
- `prepare` and `deliver` reuse the [same read-only recovery contract](../../docs/recovery-boundary.md).
  Project identity, session identity, binding generation and fresh evidence are
  checked. Changed evidence or recovery errors reject a bound step; `lastCode`
  explains why. An unrelated project is passed through without memory reads.
- Each relevant pre-step rechecks the project. It does not persist the prompt,
  accept a handoff, create a checkpoint or call an extraction model.
- The subprocess receives a small environment allowlist, not API keys, proxy
  variables or Python startup overrides. No shell is used. Each call has a
  five-second timeout and bounded output. Cancellation escalates from SIGTERM to
  SIGKILL after 250 ms and waits for the direct child to close before settling
  recovery. This does not manage arbitrary descendant processes from a modified
  executable. This is not an OS filesystem sandbox;
  trusted code and same-user processes retain their ordinary permissions.
- At most 10,000 characters are accepted for the recovery response. This is not
  an exact token quota. Oversized context fails whole rather than losing constraints.
- Only the hash and message ID of an actually committed recovery are remembered
  in-process. A pre-step offer is not treated as delivered. Identical content is
  not appended every turn; reference checking still runs. A new binding epoch or
  surface replacement covering the committed memory invalidates that optimization;
  an unrelated system-message update does not. Only the check's
  sampling timestamp is excluded from the comparison.
- Pause changes the epoch and aborts pending reads. New paused turns receive no
  new memory. Resume revalidates; detach removes the listeners and cannot resume
  the same attachment. None of these actions erases context already admitted to
  the host's conversation. For forgetting, the host must clear/rebuild its own
  conversation as well; this candidate does not implement that operation.
- Restoration is historical user-role plugin data, not a system instruction,
  permission grant, executable plan or completion verdict. This labeling alone
  does not prove prompt-injection immunity.

## Reproduce without a paid model

Protocol-facing contract tests use a synthetic host boundary:

```sh
node --test tests/test_dsh_recovery.mjs
```

The separate opt-in test loads production packages from an explicitly selected
installed DSH `package.json` via `CONTINUITY_DSH_PACKAGE`. It refuses other
versions, does not download dependencies, and mounts only core services and a
synthetic provider. Run `node --test tests/test_dsh_runtime.mjs` with that
environment variable and `CONTINUITY_TEST_PYTHON` set to your Python executable.
Without the package variable it reports **skipped**, not success on a real host.
Use an independent network restriction around the test. Do not substitute a real
provider key or launch your ordinary Desktop profile for this test.
