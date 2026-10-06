# Authorized progress saving — XS candidate

This CLI boundary accepts a structured draft from one explicitly selected project. It does not read chats, call a model, install a hook, or start a daemon. It is not present in the public Alpha.7 assets. Check the executable's help; the version label alone does not identify this candidate.

The intended everyday benefit is fewer repeated save instructions, without treating every completed response as a reliable memory. The assistant prepares the draft; this core validates and commits it. Candidates containing the [Claude prepared-progress hook](../adapters/claude-code/authorized-save.md) can opt into that separate session-scoped adapter. Its actual event loading and ordinary-user end-to-end acceptance require their own evidence. A successful local CLI test does not prove automatic saving in Codex, Claude Code, Harness or WorkBuddy.

## Scope and trust

Start from an existing, reviewed checkpoint. Explicit authorization chooses the project ID, session label, one project-relative draft path, a lifetime of 1–86400 seconds, and the observed revision. The core creates a new generation on each enable/re-enable. A pending callback cannot substitute a different path or reuse an old generation.

These records enforce a cooperative local save protocol, not user authentication. A process with the same filesystem/CLI authority could call enable or the existing manual checkpoint command. Do not expose policy mutation to an untrusted process and call it a security sandbox. Revocation stops this event-save path after it commits; it does not cancel a save already committed, disable manual saves, erase old progress, remove host permissions, or revoke context already loaded by an assistant.

Lifetime uses the local UTC clock sampled after obtaining the writer transaction. It is an admission-time policy, not a guarantee that the physical COMMIT finishes before expiry. System clock rollback and hostile same-account changes are outside this slice's guarantee.

## One selected session

`<cli>` means the entire verified executable prefix, not a guessed global command. `<project>` is the selected absolute directory. IDs below come from actual command results, not these placeholders. Use argument arrays when possible.

### Start from the recorded work, not a blank summary

Candidates listing `save template` can return an editable baseline in one read-only call:

```text
<cli> --project <project> save template --expect-project-id <project-id> --expect-revision <reviewed-revision> --max-chars 32000
```

Read `data.check` and `data.draft`. Only the six fields inside `draft` belong in the chosen draft file; do not write the whole response as a checkpoint. The baseline retains the current objective, next step, constraints, decisions and unresolved items. Its evidence includes the linked handoff inputs as well as current output references, without file contents or stored hash/size fields that a draft cannot accept. Repeated identical paths are combined only when their roles agree. Changed/missing references, conflicting roles or a union exceeding the existing reference limits require review, not silent deletion. A too-small response budget fails without truncation.

This is recorded data, not permission or a proposed new result. The assistant must inspect the work it actually did, edit the next step, append evidence-backed progress and preserve unknowns before saving. The command does not write a file, enable policy, invent an operation ID or prepare/commit a candidate. Keep the returned base revision: if another writer advances, review the conflict rather than updating that number and retrying blindly. Reference checks sample files; they do not lock them. This CLI-only helper does not imply a new MCP tool.

The combined baseline is also checked for memory IDs shared across inherited documents and for the 128 KiB draft limit using compact UTF-8 JSON plus a newline. A larger response budget does not bypass that draft limit. When writing the six fields, use compact UTF-8 JSON (`ensure_ascii=False, separators=(',', ':')` in Python); added formatting, escaping or later edits can still make a file too large. Save revalidates it. Do not delete a dependency or a real constraint merely to fit.

### Retain one operation identity

Before the first `prepare`, keep a small project-local operation note containing the project ID, session, generation, base revision, draft path and one chosen operation ID. Create that note once for the reviewed work milestone; retain the returned candidate ID alongside it when available. These labels are not credentials or permission. Never create a fresh operation merely because a reply, hook event or process exit was missed.

- With a candidate ID, `save show` tells you the recorded outcome without reviving permission; `resume` checks current progress and references.
- Without a candidate ID, `save-policy status` lists pending operations with their event IDs. If none matches, that alone does not prove the proposal was never saved: committed operations are not in the pending list. Only when the original operation note, original base and exact draft are retained and policy is still active may the same `prepare` be explicitly replayed to recover its receipt. If any is missing or changed, stop for reconciliation; do not mint a new ID.
- No work changed: do not generate another proposal. A no-op commit avoids a new checkpoint but still retains a receipt, so polling with fresh IDs grows storage without useful progress.

The operation note is the caller's recovery aid, not a second authoritative memory database. Core's candidate and receipt decide whether progress was saved. A hook is optional; an authorized CLI assistant can use the same prepare/show/commit/resume sequence directly, but must call that explicit tool-driven saving, not native automatic triggering.

### Authorize, prepare, read back

1. Read `status` and the matching guide. Review the draft and the authorization scope.
2. Explicitly enable saving:

   ```text
   <cli> --project <project> save-policy enable --expect-project-id <project-id> --session-id <session-id> --expect-generation none --expect-revision <revision> --draft-path progress.json --ttl-seconds 3600
   ```

   `none` is only for a session with no prior policy. Replacing even a revoked policy requires its observed generation. The returned generation is new; do not generate or recycle one in an adapter. Enabling a policy does not launch any host automation.

3. The assistant writes and reviews `progress.json` using the existing six-field checkpoint format. An authorized adapter then proposes a logical save operation:

   ```text
   <cli> --project <project> save prepare --expect-project-id <project-id> --session-id <session-id> --generation <generation> --event-id <operation-id> --expect-revision <revision>
   ```

   This captures a bounded candidate in the same local database, without advancing project progress. `operation-id` is an adapter-owned stable operation identity; a host event name is not unique enough. Stop, compaction and shutdown callbacks for the **same proposal** must reuse it. Same identity with a different base revision, content or reference fingerprint is a conflict. Do not create a new identity to bypass the conflict.

4. Inspect and submit the captured candidate:

   ```text
   <cli> --project <project> save show --expect-project-id <project-id> --session-id <session-id> --generation <generation> --candidate-id <candidate-id>
   <cli> --project <project> save commit --expect-project-id <project-id> --session-id <session-id> --generation <generation> --candidate-id <candidate-id>
   ```

   `show` is a read-only historical snapshot, not live reference validation. Commit checks the candidate's fingerprints, then rechecks project identity, current policy, generation, expiry and revision in the checkpoint transaction. It never rereads a changed draft as though it were the previously prepared candidate. A successful commit returns `saved` or `unchanged`. Identical replay returns the original outcome, with the current project revision separately identified. A replay needs an active matching policy; after revocation use `show` to inspect an old outcome, not to regain write permission.

5. Read back through the existing `resume`. Inspect `check` and any issues before continuing. No-op saves do not create a new checkpoint. Saving does not prove task completion or semantic truth.

## Pause, inspect and discard

```text
<cli> --project <project> save-policy revoke --expect-project-id <project-id> --session-id <session-id> --generation <generation>
<cli> --project <project> save-policy status --expect-project-id <project-id> --session-id <session-id>
<cli> --project <project> save discard --expect-project-id <project-id> --session-id <session-id> --generation <candidate-generation> --candidate-id <candidate-id>
```

Status includes pending candidate IDs, including old generations for that session. Show/discard remain available for those candidates after revocation/expiry. Discard preserves a tombstone and does not remove a saved checkpoint. There may be at most 128 prepared candidates in a project; review/discard unwanted proposals rather than deleting internal tables. Candidate content and receipts stay local in the project database. No-op operations still retain their deduplication receipt; adapters must not generate fresh operation IDs on unchanged polling. Records are not encrypted or automatically purged; discard is not secure erasure. A later retention/forgetting workflow needs its own review, including backups.

## What still needs manual review

This first automatic path is deliberately append-only for established objective, constraints, decisions, unresolved items and references. It can update `next_action` and append progress. It cannot quietly replace the objective, resolve an old issue, drop a constraint, rewrite an artifact already referenced, or lose an input inherited through a handoff. Those cases return `SAVE_REVIEW_REQUIRED`; reconcile through an explicitly reviewed ordinary checkpoint, then prepare a new operation against the new revision.

New `memory` documents may contain candidate or retired entries, not active ones. Already-confirmed memory must retain its reference bytes. An exact memory reference inherited from an accepted handoff also counts as previously registered: re-including it in the authorized draft resumes direct recall of its active items. Dependency preservation and recall are different: the earlier artifact-only return did not itself recall that memory. This behavior is intentional within the same authorized project, not permission to promote new guesses. A matching path or memory ID alone is insufficient; role, hash and size must match the verified inheritance chain. Changed/retired memory requires a reviewed checkpoint and cannot be silently reactivated by an old queued candidate. Promoting a candidate to active is an explicit manual review/save. The program cannot recognize a lie or an inferred preference hidden inside free-form decisions; the drafting assistant is still responsible for honest content. No classifier or second model is claimed here.

## Storage and failure contract

- Candidate identity is unique within project/session/generation/operation. Candidate payload and base revision are fingerprinted; checkpoint + result receipt commit in the same SQLite transaction. There is no second memory database.
- File hashing happens before the short write transaction. This samples bytes, not a filesystem lock. Unrelated file writers can change them afterward; `resume` revalidates them. No claim of all-files atomic snapshot is made.
- A stale revision, wrong identity, revoked/expired generation, changed reference or reused operation with different content fails without a checkpoint. Do not re-enable, rebuild, change IDs or retry indefinitely to make it green.
- Missing events or crashes before persistence can leave unknown/unsaved progress. After an acknowledgment is lost, use the same candidate/operation identity; do not repeat the underlying business action. Atomic database writes do not provide exactly-once external side effects.
- A local I/O error from `save commit` is not a receipt saying “nothing was saved.” Preserve the operation note and storage. Inspect `save show` with the same project/session/generation/candidate, then `resume` for current progress. A blocked read or `STORAGE_RECOVERY_REQUIRED` is a stop for explicit storage review, not permission to delete a journal, reinitialize, or automatically retry. After reconciling a still-prepared proposal and the cause of failure, an explicitly authorized commit can reuse that candidate; a saved receipt needs no new write or repeated business action.
- The CLI flushes its JSON response before reporting success. If stdout is unavailable, it exits nonzero and tries to send an `OUTPUT_UNAVAILABLE` diagnostic through stderr, including the same-candidate inspection instructions for `save commit`. Neither a partial stdout response nor the nonzero exit determines whether a write committed. If stderr is also unavailable, no diagnostic delivery is promised and no hidden fallback log is created. The caller must retain the operation identity and reconcile through a new, working channel.
- Optional v1 tables preserve existing project/checkpoint/handoff fields. Old runtimes can read ordinary checkpoints but cannot enforce this new policy; downgrading does not disable their manual write paths.
- The core save interface is CLI-only; no new MCP write tools are implied. The optional Claude hook uses that same CLI and needs separately authorized local access and actual event-loading verification. Read-only MCP permission must not be bypassed using CLI.

Official background: [Claude Code hook reference](https://code.claude.com/docs/en/hooks) distinguishes event inputs, handlers and lifecycle behavior; it is not an exactly-once save protocol. [SQLite transactions](https://www.sqlite.org/lang_transaction.html) and [isolation](https://www.sqlite.org/isolation.html) define the transaction boundary used here. These rolling documents do not certify this candidate, a particular installed host, or power-loss behavior.
