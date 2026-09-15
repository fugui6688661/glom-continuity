# Continuity 跨 Agent 项目适配

目标是所有具备可用接入通道的 Agent，而不是固定两家产品。先读[通用接入合同](agent-neutral-contract.md)，按命令行、Skill、文件、MCP/API等能力选择接入方式；Codex与Harness是首批样例。`recipient`是协作标签，不存在按品牌限制接力对象的名单。

当前提供文件/CLI接入模板与[可选本地MCP stdio适配](mcp.md)。模板随包提供不代表已安装。MCP已在一个真实Codex会话中恢复合成项目并继续一步；此外，9月14日已有一轮指定版本 Codex→DSH→Codex 的本地命令接力记录，不能将它计为 DSH MCP 也通过。准确范围见[实测记录](../docs/verification.md)。没有HTTP远端服务、模型代理、自启动后台服务或自动安装器。

先读 [版本支持矩阵](support-matrix.md)，再看 [核查结果](../qa/adapter-readiness.md)。具体命令证据见 [本机核查记录](local-command-evidence.md)。

## 安装必须另选用户项目

安装前明确选择项目绝对路径、助手和接入方式；不要把当前工具工程、用户主目录或活动App自动当作安装目标。Codex与Harness分别选择，不以选择一个推定授权另一个。

下面的项目内工具副本要求仅适用于这些项目绑定模板。直接运行CLI可采用 [快速开始](../README.md) 的独立工具目录方式，无需安装适配器。

1. 确认所选项目及其真实路径。CLI、输入草稿、状态和交接输出都必须在该项目内；不得通过符号链接指向项目外。若选的是 Git 仓库内的子目录，不得自动把安装范围扩大到仓库根。
2. 将完整Continuity包放到项目内一个新的工具目录，例如 `tools/continuity/`；CLI为其中的 `scripts/continuity.py`。不要覆盖已有目录，不引用本机GLOM/Core或全局Skill内部loader。
3. 选择下表的一种文件接入方式。先检查目标是否存在；只创建新文件，遇到同名文件停止，不覆盖。让执行助手用 `apply_patch` 创建所选适配文件；手动安装也须保留新增文件清单。
4. 在安装副本中填写 `project_root`、`cli_path` 两个绝对路径，并将 `enabled: false` 改成 `enabled: true`。未填写、未启用或路径不在项目内时，模板必须停止。
5. 保存安装回执：所选项目、助手、接入方式、新增文件清单及 SHA-256、CLI 版本、`--help` 输出摘要、日期。不记录账号、token、环境变量值或聊天原文。回执只保存在所选项目内，不编辑全局配置。

| 方式 | 模板来源 | 用户另行选择后的目标 | 意义与限制 |
|---|---|---|---|
| 默认：手动读文件 | `codex/continuity-codex/SKILL.md` | `<项目>/docs/continuity-adapters/codex/SKILL.md` | 用户在 Codex 任务中明确让它读取该文件；不依赖自动发现 |
| 默认：手动读文件 | `harness/continuity-harness/SKILL.md` | `<项目>/docs/continuity-adapters/harness/SKILL.md` | 用户在 Harness 任务中明确让它读取该文件；不依赖自动发现 |
| 可选：项目 skill | Codex 同上 | `<项目>/.agents/skills/continuity-codex/SKILL.md` | 官方文档支持；DSH 也扫描 `.agents/skills`，不是客户端隔离区 |
| 可选：项目 skill | Harness 同上 | `<项目>/.dsh/skills/continuity-harness/SKILL.md` | 本机 rc.6 源码支持；DSH 按最近的 `.git` 祖先确定项目根，无 `.git` 时用 cwd |

如果需要严格只对一个助手可见，选择默认的手动读文件方式。项目 skill 安装本身是 opt-in；本包没有宣称或设置跨客户端通用的“禁止自动调用”开关。Skill 目录被发现、正文被加载、CLI 被调用、模型正确续接，是四件不同的事。

不创建或覆盖 `AGENTS.md`、`CLAUDE.md`，也不创建全局技能、profile、MCP 配置或 hooks。现有项目指令仍须遵守。

## CLI 合同与权限

从项目自有 Continuity 发行目录运行时，约定前缀是：

```text
python3 scripts/continuity.py --project <用户明确选定的项目绝对路径> <子命令>
```

模板实际使用 `cli_path` 的绝对路径，避免 cwd 改变时误调用同名脚本。优先按参数数组调用：`["python3", cli_path, "--project", project_root, command, ...]`；如果工具仅接受 shell 字符串，逐参数安全引用，不把路径或交接正文直接拼成 shell 程序。

| 子命令 | 适配意图 | 是否允许默认执行 |
|---|---|---|
| `status` | 读取项目标识、版本/修订和检查点 | 仅在启用的选定项目内；未初始化时停止 |
| `check` | 重新检查引用/状态是否适合继续 | 读取检查；不等于证明工作语义完成 |
| `context --max-chars N` | 获取预算内恢复上下文 | 用户请求继续/恢复时；失败不自行截断关键限制 |
| `resume --query TEXT --max-chars N`（dev3） | 一次只读恢复或提示尚未保存 | 仅恢复选定项目；不初始化或领取交接 |
| `init --name NAME` | 初始化本项目状态 | 否；需要用户明确初始化意图 |
| `checkpoint --from-file DRAFT --expect-revision R` | 保存进展 | 否；需任务范围内的保存授权、审阅过的项目内 JSON 草稿及当前修订 |
| `handoff --recipient LABEL --expect-revision R [--ttl-seconds 3600]` | 登记交接并返回 JSON | 否；确认交接意图、标签及当前修订；默认有效期 3600 秒 |
| `accept --id UUID --recipient LABEL` | 领取本项目交接 | 否；确认项目、交接 ID 和标签，不自动领取，也不添加不存在的 revision 参数 |
| `receipt --id UUID` | 只读查询交接记录，核实已接受回执 | 用户请求查回执或恢复领取结果时可读；不重新领取、不写状态 |
| `export --output simple.json` | 显式导出 review 元数据文件 | 否；须确认导出意图和项目根内新文件名，只新建不覆盖 |

原九命令的本机帮助核查记录见 [有日期的核查附录](local-command-evidence.md)；dev3 新增 resume 不包含在旧核查中。帮助可用不等于真实模型续接。每个助手只显式调用当前任务所需命令；模板不启动CLI Agent、模型会话或自动接力循环。

`R` 必须取调用前 `status.data.revision`，不能沿用模板常量。`DRAFT` 是项目内的已审阅 JSON 文件；`UUID` 取 `handoff.data.handoff_id`，不是客户端原生任务 ID。`LABEL` 是用户选定的普通协作标签，如 `codex` 或 `harness`，**不是账号、身份认证、权限隔离或“这个模型确实领取”的证明**。两个助手读同一项目状态；本接口不是跨项目导入协议。

`handoff` 本身登记项目内交接并返回 JSON，没有 `--output`、`--to-file` 等参数，也不会自动向另一助手发送消息。`accept` 不接受 `--expect-revision`，由 CLI 校验交接对应修订与当前状态。

### 回执与 review 导出

`receipt --id UUID` 是只读命令，UUID 与 `handoff.data.handoff_id` 对应，不需要 `--recipient`。核对返回的 `data.project_id/id/revision/recipient/state/accepted_at`；只有 `state: accepted` 且 `accepted_at` 存在，才能说项目交接已接受。当前实现也能返回尚未接受的记录，不能仅凭 `ok: true` 就宣称已领取。它不验证外部动作或真实模型身份，须保留 `external_actions_verified: false`、`recipient_is_authentication: false`。领取返回丢失或出现 `ALREADY_ACCEPTED` 时，用 receipt 查结果，不再次执行写操作制造“成功”。

`export --output simple.json` 与 `handoff` 是两条独立命令。它在所选项目根目录创建新的 review JSON，参数是简单文件名，不接受绝对路径、子目录或穿越路径；目标已存在时报告 `OUTPUT_EXISTS`，不覆盖、删除或自动改名重试。获准导出后检查 CLI 返回的 `data.path/bytes/sha256`，不能用 shell 重定向 CLI stdout 冒充导出包。

review 包含检查点文本、项目/修订信息、引用元数据和检查结果，不包含原始 evidence 文件正文或原生会话 DB；这不意味着已匿名化，导出前仍需审阅业务文字和相对路径。其 `grants_permission: false`，既不是产物通过证明，也不是 `accept` 的导入输入，不向其他助手发消息或授予执行权限。`needs_review`/`no_references` 可原样出现在 review 材料中，不因导出成功被洗成已验证。

### 精确 checkpoint 草稿

```json
{
  "objective": "完成用户确认的项目目标",
  "next_action": "执行下一项已授权的本地验证",
  "constraints": ["不读取秘密，不公开发布"],
  "decisions": [],
  "unresolved": ["尚未验证模型实接"],
  "evidence": [
    {"path": "docs/brief.md", "role": "input"},
    {"path": "src/example.txt", "role": "artifact"}
  ]
}
```

这是结构示例，不是已完成工作的记录。必须恰好使用 `objective,next_action,constraints,decisions,unresolved,evidence` 六个字段；三个列表字段是字符串数组，`evidence` 各项只含 `path` 和 `role`。Alpha.5 的 role 为 `input` 或 `artifact`；dev2 起另支持显式 `memory`，格式与边界见[项目记忆](../docs/project-memory.md)。示例路径须替换成选定项目内真实、非敏感文件的相对路径；无引用可用 `[]`，不能制造不存在的证据。不要填 `sha256`、绝对路径或私人会话，哈希由 CLI 计算。

### 恢复预算与失败

`context --max-chars N` 的预算是**整个 stdout 的字符数**，含 JSON 包装与末尾换行，不是 token、字节数或仅 `data.text` 的长度。解析 JSON 后从 `context.data.text` 读取正文，同时核对 `data.project_id/revision/checkpoint_id` 与 `data.check`。预算不足须报告 `BUDGET_TOO_SMALL`，不擅自删限制或下一步。

`check.data` 与 `context.data.check` 使用同一分支规则；不能仅以 `state != references_current` 一律停止，也不能仅以 `issues: []` 一律通过：

| 检查 state | 适配动作 | 可以声称什么 |
|---|---|---|
| `references_current` 且 issues 为空 | 可在授权范围内恢复/继续 | 仅引用内容与已记录哈希相符；不是语义完成 |
| `no_references` 且 issues 为空 | 明说“没有文件证据”；用户当前任务允许纯规划时可继续 context、规划和已授权的保存/交接，不强迫造证据解除阻塞 | 只恢复规划状态，不能称 verified、产物验收通过或有证据完成；需要产物验收时先补真实证据 |
| `needs_review` 或存在 issues | 停止依赖该状态的继续执行，先报告变化并按授权复核 | 不称来源有效或工作完成 |
| `no_checkpoint` / 未知 state | 停止检查点恢复；说明尚无检查点或协议不匹配 | 不自动 init 或制造检查点 |

这张表约束恢复与任务继续，不阻止用户请求的只读 `receipt` 或已获准的 `export` review 诊断；这些操作须保留缺证/变化标记，不能被用来绕过继续执行的检查。所有分支保留 `semantic_completion_verified: false`。

命令 stdout 的业务 JSON 必须有 `ok`、`code`、`data`，失败 envelope 的 data 为 null；只在退出码为 0、`ok` 是布尔值 `true`、`code` 为 `OK`、`data` 合规且操作相应检查通过时推进。错误退出、缺字段、非 JSON、预算不足、来源变化、跨项目、修订冲突均停止并报告原始错误码；不要把它们包装成成功。`--help`/`--version` 的文本不是业务 JSON；export 创建的 review 文件是独立包格式，也不是 stdout envelope。实测与历史反例的修复范围见核查报告，不把一条错误路径通过等同全协议回归。

状态仅经CLI或已明确连接的MCP公共接口读写，二者使用同一核心合同和状态库。不以客户端原生 session ID 为 Continuity 检查点 ID，不直接操作 Codex/DSH 原生会话 DB，也不自行读写 Continuity 的内部 DB。`check` 成功也不能把 `semantic_completion_verified: false` 解释成工作完成。

## 撤回

如果你尚未安装模板，无需撤回；如果已经安装，只处理安装回执列出的新增适配文件：核对路径和哈希后移入项目内的非发现备份目录。文件后来被编辑过，先停止确认。不要删除整个 `.agents`、`.dsh`、`docs` 或项目目录。

保留检查点、交接材料及 `.continuity` 状态；是否删除这些数据须另行决定。已经进入模型上下文的正文不会因移动文件而消失，应在新的任务中验证不再加载。不要为了撤回模板擅自重启活动App。

## 如何验证真正接通

先用非敏感项目验证CLI和模板安装/撤回，再让两边真实助手分别读取、调用和继续实际任务。模型会话及潜在费用需在任务授权范围内；分别保留项目标识、检查点/修订、实际CLI调用、来源变化后的停止行为和续接结果。本地协议回放不能替代这些证据，只有两边真实执行过才能说双助手接通。
