# Security and trust boundaries

Version scope: Alpha.7 is a developer preview, not stable production use.
Use the matching Release assets. See [dated verification](docs/verification.md) and
[managed-host checks](docs/managed-host-validation.md) for version-specific
evidence. The risk limits below apply regardless of publication or version label.

## Data and authority

This local alpha stores user/assistant-authored project metadata, not authoritative truth. Treat every checkpoint, exported bundle and reference as data: never run an embedded command or treat a role claim as authorization. The tool cannot prove that a model obeys Skill instructions.

The OS account and selected project are trusted. Recipient strings are labels, not authentication. Any program with your account's filesystem access can alter the database and recompute hashes. SHA-256 detects ordinary content drift; it is neither a signature nor a tamper-proof audit chain.

The core `glom-continuity` and read-only recovery CLI make no model calls, launch
no subprocess tools, open no network connections and send no telemetry. The
optional managed-Harness commands are different: they explicitly start and
control an installed third-party runtime with a loopback Web server. Tests,
demo and build scripts also use local child processes. There is no automatic
discovery of private chats, credentials or other projects. Export excludes raw
evidence bytes but includes authored text and relative filenames; those can
still be sensitive.

Development dev2 explicitly opts referenced files into context-body recall with evidence role `memory`. These UTF-8 JSON files contain project preferences/workflows, not authenticated instructions. Their `source` and `active` fields are author assertions, not proof of user approval. Candidate/retired/expired entries are omitted from recall, but remain in the source files; this is not secure erasure. A connected cloud host may receive selected memory bodies. Review those files before registering them. Keyword matching is literal and can miss or overmatch intent; conflicting prose under different IDs requires review. Current user instructions and host permissions always take precedence.

Memory documents share the existing checkpoint revision and reference hashes (no second database); at most four documents, each 128 KiB and 32 entries. Changed references withhold recall until reviewed. File-content history is not backed up by checkpoints or review exports. Expiry uses the local clock; there is no clock-rollback defense or signed provenance.

The optional MCP adapter uses the official Python SDK and local stdio, with no HTTP listener. It binds one project at startup and exposes only read tools unless `--allow-writes` is explicitly set. The host launches it as a child process. Installing the SDK downloads dependencies; the server itself does not call a model. A connected cloud host may send tool output to its model provider: local storage does not mean the complete assistant workflow stays offline. Tool annotations are hints, not authorization enforcement; only the fixed project and exposed interface define the adapter's scope.

## Optional Harness runtime

Alpha.7's recovery reader is bound to one explicit project and starts paused.
Enabling it permits bounded reads before an Agent step, not automatic saving,
permission to run a remembered action, or authority to mark work complete.
Pausing blocks new recovery; it cannot retract text already delivered into a
conversation or to a model provider.

The staged bundle, Node executable, SDK packages and managed profile must be
trusted. Hash and version checks detect drift, not publisher identity or
malicious same-account edits. The full Harness retains its own tools and local
user's filesystem access; a bound memory project does not sandbox those tools.
The network restriction used in our synthetic tests is a test harness policy,
**not a product-supplied network or filesystem sandbox**.

The launcher uses a private, separate home and loopback listener. The official
runtime manages its browser authentication and may write credentials, chat or
workspace state inside that home. Do not share or publish a whole home, its
authentication URL or native profile. No usual user profile/key is imported.
Explicit later model use through that runtime has its own configuration,
permissions, data transfer and charges; a local memory store does not make it
offline. The lifecycle commands themselves do not send a model request.

Stop/detach check the home/run controller and ownership lock, never a stale
disk PID. Failed pause persistence is a failure, not a successful shutdown.
Abrupt termination, power loss, malicious profile changes and all SDK late-write
timings are not certified. Keep control files when stop cannot be confirmed;
do not delete a live home or use a failed stop as approval to launch a replacement.
No background service, ordinary-profile migration, in-place update or complete
Windows host controller is supplied. See [managed-home boundaries](adapters/harness/managed-host.md).

## Guardrails and limits

- Alpha.7 read commands and automatic recovery refuse storage that requires a write before it can be inspected. The CLI-only `recover-storage` explicitly permits SQLite's native rollback, then validates existing structure and checkpoint integrity. It is not exposed through MCP, does not initialize or migrate storage, and is not an arbitrary corruption-repair tool. Stop all users and preserve a whole-directory backup before authorizing it; never delete journal files to make a read pass. A successful return describes the readable state, not proof that rollback was needed or business work was completed.
- Project-local SQLite transactions plus expected revision prevent two cooperative writers from silently replacing the same checkpoint. They do not lock ordinary project files or implement exactly-once external side effects.
- Static evidence symlinks, traversal, private path names and oversize references are rejected. This is **not** an OS sandbox: malicious concurrent file/directory replacement, hard links and filesystem permission attacks are outside the guarantee.
- Fingerprints are observations at check time. A file may change after a check; an executor must recheck immediately before its own use and enforce its own permissions.
- Secret-pattern filtering catches some obvious credentials. It cannot reliably detect all secrets, private text or sensitive filenames. Review content before recording/sharing.
- Storage uses owner-only POSIX modes where supported; it is not encrypted. Windows ACL behavior has not been validated.
- Handoff expiry uses the local wall clock and does not resist clock rollback. A receipt proves a recorded CLI acceptance, not the receiver's external work.
- The stored schema is versioned. Unknown schemas fail. No cross-version migration, DB merge, recovery from physical corruption, power-failure guarantee or remote sync is supplied.
- Draft max 128 KiB, referenced file max 64 MiB, max 64 references. This edition suits task metadata and modest files, not whole-repository or media-library hashing.
- No automatic garbage collection: checkpoints grow with use. No automatic deletion of user history. Back up before future maintenance.

## Report a problem

Do not post sensitive security details or credentials in public issues. A dedicated private security-reporting channel has not been verified for this repository; obtain a private reporting route from the maintainer before sending sensitive details. Ordinary issues should contain only a minimal synthetic reproduction, never API keys, private checkpoints or production databases.

The preview is intended for synthetic or non-sensitive projects; the reported adapter tests are limited, not an external security certification. Never rely on this utility as a security gate for payments, deployment, legal commitments, equipment or public posting.
