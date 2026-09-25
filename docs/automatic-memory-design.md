# 自动项目记忆：同一核心，不同宿主入口

2026-09-24设计，2026-09-25更新：下一版只读恢复核心及DSH原生薄适配已有本地候选。DSH 0.1.5-rc.1生产执行引擎＋合成模型已验请求前恢复；独立安装包的公开宿主入口也已在macOS实看项目选择、命令、暂停重开与停用，见[有界验收](managed-host-validation.md)。不是日常桌面profile安装、真实模型效果或自动保存验收。其他宿主自动适配仍待实现。Alpha.6 的现状仍以 [实测记录](verification.md) 为准。

## 用户应当怎样使用

首次选择项目、连接助手并授权恢复与保存范围。之后正常工作，不必每次提醒“调用记忆插件”。换助手后仍读取同一个项目的目标、约束、决定、证据和未决事项，而不是重新介绍一遍项目。

这是目标体验，不是所有客户端当前都能做到的保证。自动化只能利用宿主公开支持且用户授权的入口；插件不能为封闭客户端凭空创造工具权限。

## 核心不绑定品牌

项目身份、revision、引用校验、候选记忆及保存合同归同一个核心。现有 CLI 和 MCP 复用该核心，不复制一份“Codex记忆”、一份“Harness记忆”。适配器只转换宿主事件、传输和结果格式。

覆盖目标包含 DeepSeek Harness、WorkBuddy、豆包工作模式、Codex、Claude Code、Hermes 等。名称不是准入名单；新宿主具备合适能力即可开发适配。连接某厂商的模型 API，不等于接通其 Agent 产品的任务与文件环境。

| 实际能力 | 接入路线 | 可以怎样描述 |
|---|---|---|
| 可访问已授权项目并执行 CLI | 同一 CLI 合同 | 可工具调用；没有启动事件时不能称自动恢复 |
| 可连接 MCP | 同一项目绑定的 MCP 服务 | 可工具调用；tools/list 不证明会话一定调用 resume |
| 有已验证的会话/压缩/任务事件 | 薄生命周期适配器 | 只对实测事件标为 automatic |
| 可自动加载项目指令，但没有可靠事件 | 指令引导调用 CLI/MCP | best-effort；仍依赖助手按指令执行 |
| 只有文件或文本通道 | 现有审阅导出；后续可扩展可携带项目包 | snapshot-only；不能称实时同步或已写回 |
| 没有获准入口 | 明确未接入 | 不绕过限制，不假装成功 |

当前没有远端 HTTP 服务，也没有可携带项目包的自动导入器。跨设备连接另需认证、项目隔离、撤销及并发验收，不能直接暴露本机 CLI 或同步正在写入的 SQLite。

## 分开记录接通与自动化

每个宿主适配记录至少包括：产品/版本、实际可执行文件或服务、项目绑定、读取/写入权限、已发现入口，以及下列互不替代的状态：

- `connection_verified`：通道实际可用；
- `startup_restore_verified`：真实新会话在处理任务前读到项目状态；
- `checkpoint_save_verified`：真实任务边界写回并读回；
- `compaction_recovery_verified`：压缩后恢复已保存内容；
- `uninstall_preserves_project_verified`：卸载不删除用户项目或其他插件配置。

这些是拟议的验收记录字段，不是 Alpha.6 已新增的 API。每项均可为未知/未测试；某一项通过不能把其余项目自动填成通过。合成 hook 输入测试不替代真实宿主事件。

## 已查清的差异

- **Codex**：官方有 SessionStart（包括 compact）和插件 hooks；插件启用不等于 hooks 已获信任。需要实际安装版验证。[官方 hooks](https://learn.chatgpt.com/docs/hooks)、[插件打包](https://developers.openai.com/plugins/build/plugins)
- **Claude Code**：官方有命令型 SessionStart、PreCompact、Stop 等事件，事件输出和权限规则各不相同，不能将普通结束视为业务完成。[官方 hooks](https://code.claude.com/docs/en/hooks)
- **DeepSeek Harness**：本机官方包 0.1.5-rc.1 的 `dsh-hooks-claude-code` 静态实现具备部分桥接，但 SessionStart 为 detached，不能保证首请求等待；解析事件不含 PreCompact。当前 profile 是否启用、本插件真实自动恢复均未验证。需要核对时序或使用原生扩展，不直接照搬 Claude 配置的能力承诺。
- **DSH原生候选补充**：已改用awaited `agent/pre-step`，在生产AgentLoop中通过合成任务验证，见[适配边界与复现](../adapters/harness/automatic-recovery.md)。上条Claude兼容hook未启用；本候选也未安装日常Desktop profile。独立受管Web入口正常进程重开后暂停偏好已实看；完整桌面客户端、压缩、断电/磁盘故障保证仍未验。
- **WorkBuddy**：官方插件概览列有 Skill/MCP/Hook/Agent/Rule，连接器文档提供 MCP＋Skill、CLI＋Skill；桌面精确生命周期与 CodeBuddy CLI 的契约不能混用。本插件的桌面自动恢复/保存尚未实测。[插件系统](https://www.workbuddy.cn/docs/workbuddy/Plugins)、[连接器](https://open.workbuddy.cn/en/docs/connector)
- **豆包工作模式**：已确认[官方产品入口](https://www.doubao.com/work)；本轮未找到足够的一手资料证明第三方 MCP/CLI/插件和会话生命周期契约。状态是待核查，不是“必定支持”，也不是“永远不能接”。

上述官方文档是滚动资料，本机包静态检查不是正在运行的版本或效果证明。没有更改用户的宿主配置、读取原生聊天数据库或启动付费模型。

## 首个实现切片：只读自动恢复

本地候选增加了 [`prepare` / `deliver` 公共命令边界](recovery-boundary.md)：延迟队列只传检查点回执，交付时核对当前项目/会话/代次并重新读取。核心协议测试和隔离安装不同于真实宿主生命周期验收；本机日常助手未因此自动接入。

统一恢复处理器先复用现有 `resume` 语义，再输出所选宿主需要的上下文格式。只绑定用户明确选择的项目；不能根据当前目录向上猜测其他数据库。

1. 核对执行器位置、项目规范路径及项目身份；当前会话不属于绑定项目就不注入。
2. 校验业务 envelope、revision、引用状态与预算。未初始化、无检查点、输入变化分别显示，不重复 init。
3. 项目文字始终是历史数据，不是新授权。保存的 next_action 不能自行触发执行；不能把恶意内容提升为宿主系统指令。
4. 恢复不写库、不领取交接、不调用模型；超时/异常显示未恢复，不能继续使用上个项目的缓存。
5. 切换项目或会话后，迟到结果必须丢弃。只对能证明在首请求前完成恢复的接入方式承诺启动自动恢复。

核心、事件处理器、宿主安装器分别验证。不让一份宿主特定 hooks.json 变成全产品的记忆格式。

## 第二个切片：授权范围内的自动保存

助手准备结构化进展，确定性提交器校验和持久化，这是两个动作。没有合规草稿不能根据“这轮结束了”制造事实。

- 明确决定和已授权进展可以保存；推测的习惯仍是 candidate，不自动升为永久规则。
- 复用当前 checkpoint/revision/引用核验；冲突保留待审，不用最后写入覆盖另一助手的进展。
- 重复 Stop、压缩与收尾同时到达、多窗口及迟到回调须有幂等与代次保护；不靠无限要求模型继续来保存。
- 关键节点先保存，不只押注 SessionEnd。崩溃前未持久化的尾部内容必须显示未知或 pending。
- 没有变化不增版本；普通保存不代表业务验收通过。

## 可以借鉴，但尚未宣称胜出的机制

[Basic Memory](https://docs.basicmemory.com/integrations/harness-capture) 的薄生命周期入口、[Engram](https://github.com/Gentleman-Programming/engram) 的主题身份、[Serena](https://oraios.github.io/serena/02-usage/045_memories.html) 的项目记忆与分层读取、[Mem0](https://github.com/mem0ai/mem0) 和 [Claude-Mem](https://github.com/thedotmack/claude-mem) 的采集/提取分层，都提供设计参考。没有因此导入其运行时或复制源码，也不默认上传对话、运行额外提取模型或开启全局记忆。

## 必须通过的反例

同名项目不得串记忆；陈旧 revision 不覆盖新进度；文件变化不能继续标有效；重复事件不得重复保存；暂停后停止采集；只读宿主不得绕道 CLI 写入；卸载只移除可确认归属的接入配置，保留项目状态；撤销/过期记忆不继续注入。遗忘后的队列和缓存不得把旧条目重新导入；无法处理的备份须明确说明。

按项目证据评估用户是否少重讲、少丢节点及总上下文成本。字符预算不是精确 token 数，自动恢复也不是“不可能遗忘”。未完成同任务对照前，不宣称已超越同类。
