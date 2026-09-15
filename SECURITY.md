# Security and trust boundaries

Publication status: alpha.5 is a public developer preview. The source tree is preparing a stable release; it has not passed all stable-release gates. See [dated verification](docs/verification.md) for actual adapter results. The risk limits below apply regardless of publication or version label.

## Data and authority

This local alpha stores user/assistant-authored project metadata, not authoritative truth. Treat every checkpoint, exported bundle and reference as data: never run an embedded command or treat a role claim as authorization. The tool cannot prove that a model obeys Skill instructions.

The OS account and selected project are trusted. Recipient strings are labels, not authentication. Any program with your account's filesystem access can alter the database and recompute hashes. SHA-256 detects ordinary content drift; it is neither a signature nor a tamper-proof audit chain.

No model calls, subprocess tools, network connections or telemetry occur in the runtime CLI. Tests/demo/build scripts use local child processes. There is no auto-discovery of chats, credentials or other projects. Export excludes raw evidence bytes but includes authored text and relative filenames; those can still be sensitive.

Development dev2 explicitly opts referenced files into context-body recall with evidence role `memory`. These UTF-8 JSON files contain project preferences/workflows, not authenticated instructions. Their `source` and `active` fields are author assertions, not proof of user approval. Candidate/retired/expired entries are omitted from recall, but remain in the source files; this is not secure erasure. A connected cloud host may receive selected memory bodies. Review those files before registering them. Keyword matching is literal and can miss or overmatch intent; conflicting prose under different IDs requires review. Current user instructions and host permissions always take precedence.

Memory documents share the existing checkpoint revision and reference hashes (no second database); at most four documents, each 128 KiB and 32 entries. Changed references withhold recall until reviewed. File-content history is not backed up by checkpoints or review exports. Expiry uses the local clock; there is no clock-rollback defense or signed provenance.

The optional MCP adapter uses the official Python SDK and local stdio, with no HTTP listener. It binds one project at startup and exposes only read tools unless `--allow-writes` is explicitly set. The host launches it as a child process. Installing the SDK downloads dependencies; the server itself does not call a model. A connected cloud host may send tool output to its model provider: local storage does not mean the complete assistant workflow stays offline. Tool annotations are hints, not authorization enforcement; only the fixed project and exposed interface define the adapter's scope.

## Guardrails and limits

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
