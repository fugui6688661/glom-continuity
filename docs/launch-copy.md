# Public introduction draft / 公开介绍草稿

Not a publication record. Use only with the matching verified build and an actual download link. No downloads, endorsements, performance gains, or universal compatibility are implied.

## GitHub description

Local project checkpoints and reviewed handoffs for AI assistants. CLI + optional MCP.

## 中文介绍

换了一个助手，又要把项目从头讲一遍。

不是只缺一段聊天记录，而是漏了那些真正影响下一步的细节：为什么采用这个方案，哪份文件才是输入，哪些内容不能动，还有哪个问题没确认。

glom-continuity 把这些信息保存在你的项目里。新会话读回目标和下一步；接受交接前，重新检查引用文件。来源变了、修订落后了，先核对，再继续。

可以直接用本地命令，也可以接入支持本地 MCP 的助手。工具本身不调用模型、不上传项目，不要求你更换现有助手。连接云端助手时，收到的上下文仍受该服务的数据处理规则影响。

目前为早期候选版：已有本机协议测试，以及一个真实 Codex 新会话的恢复与文件产出实验。完整跨厂商接力和其他系统还在验证，不把支持标准接口说成所有产品都已兼容。

先用合成项目试一次：保存、恢复、看到变化被拒绝，再决定是否用于自己的工作。

## English introduction

A different assistant should not mean reconstructing the entire project brief.

The missing details are often small: why an approach was chosen, which file was the input, what must stay unchanged, and what still needs confirmation.

glom-continuity stores that working state in your project. A fresh session can recover the goal and next action. Before accepting a handoff, it checks the referenced files again. Changed inputs and stale revisions need review before work continues.

Use the portable CLI or connect a local MCP-capable assistant. The utility makes no model calls or uploads. A connected cloud assistant may still send recovered context to its provider.

This is an early candidate with local protocol tests and one live Codex recovery-and-output experiment. Full cross-vendor handoff and other operating systems are still being verified. Supporting an interface is not the same as testing every client.

Start with a synthetic project. Save it, recover it, and see what happens when its inputs change.

## Release notes draft: 0.1.0-alpha.5

- Added a local wheel, installed CLI/demo/MCP commands, and a first-use guide. Uninstallation leaves project records intact.
- Added independently authored recovery cases and a bounded private Windows/Linux/macOS CI matrix; exact per-version results and platform skips remain in the verification record.
- Fixed excessive-JSON-depth errors, legacy pipe encodings for Chinese text, and test-host bootstrap differences. Old failed runs are retained; a fix is not marked verified before its matching rerun.

Earlier alpha.2 work retained:

- Added an optional project-bound MCP stdio adapter using the official Python SDK. Read tools by default; project-state writes require an explicit startup option.
- Kept the portable CLI dependency-free and used the same state/validation contract for both interfaces.
- Fixed nonregular-draft blocking and launch-directory-dependent MCP draft selection, using independently reported regressions.
- Reworked the Chinese/English first-run guide, compatibility evidence and removal instructions.
- Preserved old archives; do not substitute this build's results for their contents.

See [verification](verification.md) for the tested environment, source hashes, earlier live-model scope and outstanding gates. The owner has approved the repository target `fugui6688661/glom-continuity` and the [MIT License](../LICENSE). The remaining release gates and an actual public download must be verified before this draft becomes a release announcement. Never turn outstanding items into checked boxes merely by publishing this text.
