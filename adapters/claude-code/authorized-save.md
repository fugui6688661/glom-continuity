# Claude Code prepared-progress hook — XS candidate

This adapter submits an already-prepared project checkpoint when Claude finishes a response or starts compaction. It does not infer progress from chat text. It is not in the public Alpha.7 release. Check the candidate's verification record for the exact host, platform and observed events; a test feeding JSON directly is not evidence that Claude loaded a hook.

## What a user gets

After one explicit session authorization, the assistant can prepare progress at meaningful work boundaries. The hook commits that prepared snapshot without another save instruction. The next session uses the existing `resume` command. The assistant still has to form an accurate six-field draft and call `save prepare`; this is not automatic transcript summarization, autonomous preference discovery or a guarantee that every task is remembered.

The current entry is session-scoped and opt-in, not a global plugin installer. Installation convenience and native model-quality acceptance remain separate. Existing Codex, Harness and WorkBuddy routes are unaffected.

## Bind once per authorized session

Read [the core save contract](../../docs/authorized-save.md) first. Use the verified installed CLI, its matching guide, the selected project ID and one reviewed initial checkpoint. Create a UUID for a new Claude session, explicitly authorize the selected draft path using `save-policy enable`, and retain the returned generation. A saved generation is not permission to silently re-enable it after exit.

`<hook>` means the verified wheel environment's `glom-continuity-claude-save`, or `python -I -B /absolute/package/scripts/claude_save_hook.py` from the matching portable package. `<core-sha>` is the reviewed core digest from that package's `doctor`, not an arbitrary hash copied from another release.

```text
<hook> --project <absolute-project> --expect-project-id <project-id> --session-id <session-uuid> --generation <generation> --program-sha256 <core-sha> --print-settings
```

This only prints a JSON settings preview on macOS/Linux. Windows command serialization is not supplied; it fails explicitly instead of guessing shell quoting. Inspect and save the preview to a chosen session-only settings file, keeping its local paths private. Pass that file to the explicitly selected Claude invocation with `--settings <file> --session-id <session-uuid>`. Do not overwrite existing user/project settings or change their permissions to force it to run. Host exclusions and managed settings may disable hooks. Verify loading in that actual host; this command is not proof of it.

Within the authorized project/session, the assistant writes and reviews its six-field draft and calls `save prepare` with a **stable logical operation ID** and observed base revision. Keep that ID across a lost acknowledgment. The resulting core candidate is the immutable save unit. Only prepare when the draft is ready to commit; the hook is allowed to submit it at the next matching event, regardless of which prompt originally led to the event. Host event names, prompt IDs and delivery times are not operation identities.

## Event behavior

| Event | Effect |
| --- | --- |
| Stop / PreCompact | Check project, session, core digest and current generation. No pending proposal is a silent no-op; exactly one pending proposal in this generation is committed through the existing core. Multiple pending proposals return `HOOK_AMBIGUOUS_PENDING`; inspect/discard explicitly, never pick the newest by guess. |
| SessionEnd | Request generation-bound revocation only. It does **not** flush an unprepared or pending draft at exit. Old-session cleanup cannot revoke a replacement generation. |

Queue selection is an observation, not a lock on future proposals. The core rechecks the chosen candidate, policy and revision in its write transaction. Concurrent deliveries of that candidate reuse its receipt; a later new proposal must use a reviewed current revision. A late same-generation callback may submit an already-authorized prepared snapshot; it does not prove which response or task completed.

Only the JSON fields `session_id`, `cwd` and `hook_event_name` are used for routing. All fields count toward the 256 KiB input cap. Duplicate keys, malformed input, wrong scope and unsupported events fail without a core write. `transcript_path`, response text and tool output are never read as files or converted into memory. Input fields and local session labels are not authenticated identities; an equally privileged local process remains outside this cooperative boundary.

The adapter never enables policy, prepares a new candidate, invents an operation ID, accepts a handoff, runs a model, or reports semantic task completion. It emits a short status after a save. Host/event output handling determines whether that status or an error is displayed; do not promise a visible receipt for every event, particularly compaction and exit. Inspect the candidate with `save show`, policy with `save-policy status`, and current progress with `resume` when the outcome is unclear. A core reference/revision/policy failure returns a non-blocking hook error (exit 1), never exit 2 that asks Claude to keep responding. No automatic retry or policy recreation is performed.

## Pause, failures and uninstall

- Pause saving with core `save-policy revoke` for the exact project/session/generation. Removing a recovery instruction file is not revocation. Disabling hooks likewise does not revoke an already-enabled policy; revoke first, inspect, then remove the selected session configuration. The database and user's rules remain untouched.
- Stop/PreCompact owned CLI calls share an 8-second budget. SessionEnd gives its revocation child 0.7 seconds because the host has a short shutdown deadline. Those are adapter bounds, not latency promises. Core contention can fail sooner. A timeout is **outcome unknown**, not proof that a transaction rolled back: inspect policy and candidate receipt before retrying.
- SessionEnd delivery is not guaranteed on crash, force quit or host timeout. If it is absent, automatic revocation is unverified and the explicit policy lasts until its configured expiry/revocation. Do not advertise immediate revocation on every exit. Never relax a failed permission check to hide this gap.
- The hook never saves content just because a response ended. No prepared candidate means no newly saved work. A pending candidate after shutdown remains inspectable/discardable; preserve it instead of claiming success or redoing the business action.
- An old callback after reauthorization fails its generation check. Changed evidence remains changed; user reconciliation is required. The hook does not replace old runtime or global rules during an upgrade.

Official event and settings semantics: [Claude Code hook reference](https://code.claude.com/docs/en/hooks). Rolling documentation is not a substitute for a fixed-candidate, fixed-host run. Real host delivery with a local scripted model protocol only tests delivery and persistence; it does not prove autonomous draft quality or support for other hosts.
