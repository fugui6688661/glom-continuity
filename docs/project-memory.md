# 一个助手，也能接着做

本页适用于 alpha.6 预览版，安装以对应 Release 的具名附件及配套清单为准。它包含 dev4 已有的项目记忆与恢复能力；记忆始于 dev2，一调用恢复始于 dev3。这段版本说明不新增实测结论，历史结果见[验证记录](verification.md)。

你不一定需要第二个助手。这个功能把一个项目里已经确认的习惯、做法和进度保存下来，下次由有权限的助手读取。它不扩大模型上下文窗口，也不训练模型。

已有笔记库可以继续使用。Recaloom 另存可恢复的任务节点，核对登记文件的版本，并记录助手交接；它不扫描笔记库，也不自动与笔记软件同步。保存哪些习惯和流程由你决定，也不保证记全。

## 三类记录分开

- 习惯：例如解释用中文、报告先给结论。可设置始终适用，或只适用于某类任务。
- 流程：例如制作视频时，先确认素材用途，再检查画面、字幕和声音。按当前任务关键词取用。
- 项目进度：目标、限制、已定事项、待确认问题和下一步，仍保存在 checkpoint 中。

安装工具本身不会自动开启每个新聊天的记忆。助手需要能读取项目并调用 CLI/MCP；宿主是否自动加载 Skill 必须单独验证。只有当前助手被要求保存的内容才进入记录，不扫描历史聊天、公司资料或其他项目。

另有匹配的便携包/源码时，可在其工具目录运行 `python3 -B scripts/memory_demo.py --output ./memory-demo` 查看记忆保存/召回演示；不要假定 wheel 环境有这个脚本。输出目录必须尚不存在，父目录必须存在。打开生成的 `演示结果.md`；原始命令响应在 `events.json`。这是脚本回放，不证明所有恢复功能通过验收、模型效果或节省时间。

## 让助手第一次保存

按 [INSTALL](../INSTALL.md) 确认版本与帮助。把下面这段话连同项目绝对路径、匹配 [Skill](../skills/project-continuity/SKILL.md) 的实际绝对路径和完整可执行命令前缀交给有本地权限的助手。wheel 的 Skill 可在另一份匹配文档目录内，执行仍使用所选环境的程序。已有项目不要再次 init；陌生或损坏存储须先检查，不重建。

> 保存这个项目的进度，以及我明确确认的习惯和流程。猜测先列为 candidate，不导入其他项目或私人聊天；保存后告诉我记住了什么。

助手在选定项目内创建 `project-memory.json`（示例是虚构要求，不代表所有用户都应该采用）：

```json
{
  "format": "continuity-memory-v1",
  "items": [
    {
      "id": "explain-clearly",
      "kind": "preference",
      "title": "沟通习惯",
      "body": "用中文先讲结果，再讲未完成的部分。",
      "when": ["*"],
      "status": "active",
      "source": "用户在本项目明确确认的要求",
      "expires_at": null
    },
    {
      "id": "video-review",
      "kind": "workflow",
      "title": "视频交付检查",
      "body": "先确认素材使用范围；导出后检查画面与字幕并试听声音；未验证的部分单独说明。",
      "when": ["视频", "video"],
      "status": "active",
      "source": "用户确认的项目交付流程",
      "expires_at": null
    }
  ]
}
```

将它加入新 checkpoint 草稿的 `evidence`，保留其他目标、约束、未知项与引用：

```json
{"path": "project-memory.json", "role": "memory"}
```

然后通过原来的 `checkpoint --from-file … --expect-revision …` 保存并读回，不直接改数据库。只有 `memory` 角色会把正文带入恢复结果；普通 `input`/`artifact` 不会自动加载正文。

## 下次接着做

> 恢复这个项目，按“视频”找适用习惯和流程。先告诉我资料是否变化、接下来能做什么；以我这次的新要求为准。

先用 CLI `--help` 或 MCP 工具发现确认 `resume` 可用。CLI 命令接在 [INSTALL](../INSTALL.md) 选定的绝对命令前缀及 `--project <project>` 后：

```text
resume --query "视频" --max-chars 10000
```

MCP：确认发现 `continuity_resume` 后调用 `continuity_resume(query="视频", max_chars=20000)`，项目由服务绑定，不传项目参数。一次读回检查、已有上下文/选中记忆与 `pending_handoffs`；不初始化、不保存、不领取交接，也不增加权限。无需另一个助手或创建 handoff。

恢复状态 `not_initialized` / `no_checkpoint` 表示还没有可恢复记录，只有另获授权的首次保存流程才创建节点；`needs_review` 先复核变化；`no_references` 仅作无文件验证的规划；`restored` 是恢复记录，不是任务完成。待领取交接不是领取回执；确需接手时另按 Skill 的 handoff 流程处理。错误或损坏的已有存储仍报错，不当作新项目。

`max_chars` 默认 6000，覆盖完整响应；MCP 包括工具包装及文本/结构化表示。上面的预算只是示例，不是最低要求。不足返回 `BUDGET_TOO_SMALL`，不截断，也不能自行丢掉约束。

旧版迁移：未提供 `resume` 的包仍先 `status`，未初始化/无节点时按获准首次保存或仅报告分流，有节点才 `check` → `context`。MCP 同样先 `continuity_status`、有节点再 `continuity_check` / `continuity_context`。仅当版本/帮助确认支持记忆查询时给 `context` 传 `query`；alpha.5 不支持记忆或查询，不能把 `memory` 偷换成普通输入。它仍兼容原有记录，但不会自动获得新功能。

有 memory 登记时，`data.memory.selected` 是选中的完整条目，`data.memory.omitted` 列出未选条目的 ID 和原因，`data.text` 也包含同样信息。有 checkpoint 的 `resume` 沿用 context 的同级字段 `data.text`、`data.memory`（存在时）及 `data.check`，另加 `data.recovery_state`、`data.name` 和 `data.pending_handoffs`，不会多嵌套一层 context。空状态没有 `data.memory` 键；未登记 memory 的旧 context 也不附加空的 `memory` 字段。

## 修正、停用和过期

- 临时猜测使用 `candidate`，不进入推荐正文；得到当前用户明确确认后才保存为 `active`。`source` 是作者记录的依据，不是系统认证。
- 用户说某个做法不要了，把原条目设为 `retired`，保存新 checkpoint。停用不等于从历史和备份中安全擦除。
- 临时规则可以填写带时区的 ISO 时间，例如 `2026-09-30T18:00:00+08:00`；到期按本机时钟停止推荐。
- 修改记忆文件但尚未重新保存时，引用校验会提醒变化并暂不加载记忆正文。重新审核后保存新修订，再恢复使用；旧 handoff 不再适用于新修订。
- 同一个 ID 不能同时出现在多个登记的记忆文档中。不靠“后面的覆盖前面的”消除冲突。不同 ID 之间的语义矛盾仍需要助手或用户判断，工具不声称自动理解。
- checkpoint 记录引用哈希，不备份文件正文。需要保留历史习惯原文时，使用有版本的文件名并保留旧文件；review export 也不包含这些正文。

## 边界与格式

每个 checkpoint 最多登记 4 份 memory 文档；每份最多 128 KiB、32 条记录。条目字段与示例必须一致。ID 为小写英文字母/数字及 `._-`，最长80；title160、body4000、source512字符。`when` 为1–16个非空关键词，每个最多80字符；只有通用 preference 可用单独的 `["*"]`，workflow 必须明确关键词。状态仅 active/candidate/retired；kind仅 preference/workflow；expires_at为带时区时间或null。

检索是忽略大小写的字面关键词包含匹配，不是语义搜索。没带 query 时仅选择通用习惯；所有没选中的条目会给原因。重要项目限制始终放在 checkpoint 的 constraints，不能仅靠关键词触发。任何登记引用变动都先复核。检查和召回不创建权限、不自动执行流程、不保证语义正确。

文字必须是有效 Unicode 标量；JSON 中转义的孤立代理项会在保存前被拒绝，并指出字段，不覆盖原 checkpoint。普通中文和有效补充平面字符可正常使用。

内容会进入调用助手的上下文，可能由该宿主发送给云模型。只登记已经允许用于该项目的非敏感材料；不记录密钥、密码、原始私聊。内置敏感格式筛查并不完整，不能作为唯一防泄漏措施。

现阶段没有自动扫描聊天、跨项目个人画像、嵌入模型、后台常驻、自发训练或效果百分比保证。减少重讲、遗漏和返工的效果，需要用真实新会话按同样任务对照验证，不能用这份文档或单元测试代替。
