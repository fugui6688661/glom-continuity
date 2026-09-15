# Recaloom · 续珞

原名 glom-continuity。品牌已更新，仓库地址、安装包名、命令、MCP工具名和项目数据目录保持兼容；现有用户无需迁移或重新初始化项目。新名称不代表已发布正式版。

**换个助手，接着做。**

本地项目检查点与交接工具。记录目标、决定、限制和下一步；接手时，检查引用文件是否还是原来的版本。

“币种还没确认，原始记录不能删。”这些细节和下一步一起保存，供新会话读回。输入文件已经变化？先检查变化，再接受交接。

[English](README.en.md) · [MCP 接入](adapters/mcp.md) · [实测记录](docs/verification.md) · [安全与数据](SECURITY.md)

源码正在准备正式版（内部版本 `0.1.0.dev4`），尚未发布这一版本的下载包。下方下载链接仍是不可变的 Alpha.5，不含开发版记忆、`resume`、`doctor` 或 `return-work`；试用新功能需要对应候选包或源码，不会把旧下载包直接改名为正式版。

本轮新增[安装诊断与成果回存](docs/result-return.md)：查清当前调用的是哪份程序；接手方把产物保存到对应交接，原助手能读回文件、版本与变化情况。普通保存仍可用于单助手工作，不强制每个任务走交接。

开发版支持[单助手习惯与流程恢复](docs/project-memory.md)：不需要第二位助手，仍用同一套项目检查点保存。dev3 的只读 `resume` 可一次读取恢复状态、检查、上下文、选中记忆及待领取交接；流程按字面关键词选择，停用、过期或未确认条目不推荐。它不自动保存、领取交接、扫描聊天或增加权限，也不是语义记忆或永不遗漏的保证。

**0.1.0-alpha.5 · 开发者预览版，非稳定正式版。**本地 CLI、可选 MCP 和 Python 安装入口可供试验；已完成一次真实的 Codex → DeepSeek Harness → 新 Codex 合成项目恢复接力。它不等于所有助手都已兼容，也不证明比现有工具更省 token。

[下载预览版](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.5) · [安装说明](INSTALL.md) · [提交问题](https://github.com/fugui6688661/glom-continuity/issues)

首次使用请下载该 release 的 ZIP 附件，而不是 GitHub 自动生成的 Source code。附件保持已验收候选的原字节；其中的发布状态文字是打包时快照，后续验证与限制以[发布说明](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.5)和[实测记录](docs/verification.md)为准。

第一次使用请看[安装与试用](INSTALL.md)：从虚构案例开始，再接入自己的助手。基础工具不需要模型API；使用云端助手时仍遵循该助手的计费与隐私规则。

## 先试一次，不用账号

需要 Python 3.10+。解压便携包，在工具目录运行；CLI 不需要安装依赖，也不调用模型。以下演示只用脚本生成的合成数据。

```sh
python3 -B scripts/continuity.py --version
python3 -B scripts/smoke_demo.py --output ./continuity-demo
python3 -B scripts/continuity.py --project ./continuity-demo context --max-chars 6000
```

`continuity-demo` 必须是尚不存在的新目录；已存在时换一个名字，不会替你覆盖。

打开生成的 `continuity-demo/演示结果.md`：可以看到恢复的项目、文件改变时被拒绝的交接，以及重复领取的拒绝结果。`events.json` 保留本次事件，`handoff-review.json` 是审阅快照。**这是 CLI 协议回放，不是两个模型在工作。**真实 Codex 的单独试验见[实测记录](docs/verification.md)。

Windows 命令可用 `py -3` 替代 `python3`；已在 GitHub Windows runner 跑过协议和安装检查，不代表所有 Windows 实机验证。不提供尚未上架的 `pip install glom-continuity` 命令。

## 怎么接入你的助手

| 你的助手具备什么 | 接入方式 | 已核验到哪一步 |
|---|---|---|
| 本地命令执行与项目访问 | 便携 CLI；可配通用 Skill | 协议检查；维护者记录了一轮指定版本 Codex→DSH→Codex 接力，见实测记录 |
| 本地 MCP stdio | [可选适配器](adapters/mcp.md)，默认只读 | 协议用例与一个 Codex 0.153.4 真实会话；其他宿主待验 |
| 只能读文件或聊天 | 提供经过审阅的 JSON 快照 | 人工交接，不做实时校验或自动回写 |
| 远端 HTTP / 其他设备 | 后续认证与同步适配 | 尚未实现，不能将本机服务直接暴露出去 |

不限定厂商。Codex、Harness 只是适配样例；客户端能发现工具、真正调用工具、按要求继续任务，分别验证。[通用合同](adapters/agent-neutral-contract.md) · [版本矩阵](adapters/support-matrix.md)

## 直接告诉助手要保存或恢复什么

把项目位置、工具位置和[通用 Skill](skills/project-continuity/SKILL.md)交给有权限的助手。例如：“保存这个项目的目标、限制、待确认问题和下一步。”下次说：“恢复这个项目，按‘视频’找适用流程，先告诉我资料是否变化、接下来能做什么。”安装本身不会给新聊天自动加载记忆；不需要全局钩子或导入聊天。

已提供的 dev3 候选/源码，经 `--help` 确认存在 `resume` 后，在工具目录可运行：

```sh
python3 -B scripts/continuity.py --project /absolute/path/to/project resume --query "视频" --max-chars 10000
```

MCP 须先发现 `continuity_resume`，再调用 `continuity_resume(query="视频", max_chars=20000)`，不传项目参数。没有该命令/工具的旧包仍按 `status` 分流：有节点才 `check` → `context`；Alpha.5 不支持记忆或 `query`。便携包与 wheel 的绝对命令路径见[安装说明](INSTALL.md)。

恢复返回 `not_initialized`、`no_checkpoint`、`needs_review`、`no_references` 或 `restored`：分别表示尚未初始化、尚未保存、需审阅变化、仅可恢复无引用的规划、已恢复记录；不是完成认证。它不执行 `init`/保存/`accept`，待领取交接也不会自动领取；损坏的已有存储仍报错。预算默认 6000 字符，覆盖完整响应，MCP 还计入工具包装；示例预算不是最低值，不足时报错而非截断。开发功能说明不代表新增测试已通过。

## 在自己的项目保存节点

明确选择一个已有项目目录。工具本身可以放在项目外。

```sh
python3 -B scripts/continuity.py --project /absolute/path/to/project init --name "我的项目"
```

在该项目内创建 `checkpoint.json`，再运行保存命令：

```json
{
  "objective": "整理报告，保留原始统计口径",
  "next_action": "确认缺失记录的处理方法",
  "constraints": ["未经确认，不删除原始记录"],
  "decisions": ["按月份汇总"],
  "unresolved": ["币种待确认"],
  "evidence": []
}
```

```sh
python3 -B scripts/continuity.py --project /absolute/path/to/project checkpoint --from-file /absolute/path/to/project/checkpoint.json --expect-revision 0
python3 -B scripts/continuity.py --project /absolute/path/to/project context --max-chars 6000
```

这是无文件引用的规划例子，状态为 `no_references`，不代表验过成品。已有输入用 `[{"path":"input.csv","role":"input"}]`，输出用 `artifact`；文件必须真实存在，路径相对项目，指纹由工具计算。后续保存先读 `status.data.revision`，不能一直填 0。冲突时合并进展，不盲目重试。

可以让助手读取[通用 Skill](skills/project-continuity/SKILL.md)。文件说明不会凭空赋予命令执行或文件权限。包内 Codex 插件元数据和项目模板也不代表已经安装；不自动覆盖全局配置或现有项目指令。

## 交接给另一个助手

第一个助手保存后，显式创建交接。`reviewer` 是你选的标签，不是认证身份：

```sh
python3 -B scripts/continuity.py --project /absolute/path/to/project handoff --recipient reviewer --expect-revision 1
```

接收方获准访问同一个项目后，用返回的 ID 领取并恢复：

```sh
python3 -B scripts/continuity.py --project /absolute/path/to/project accept --id HANDOFF_ID --recipient reviewer
python3 -B scripts/continuity.py --project /absolute/path/to/project context --max-chars 6000
python3 -B scripts/continuity.py --project /absolute/path/to/project receipt --id HANDOFF_ID
```

它不会自动发消息或启动助手。回执只记录领取，不证明模型身份或任务完成。来源变化、交接过期、修订陈旧、重复领取均会拒绝；通过后仍须按当前权限核查并执行下一步。

## 数据留在哪里，怎么停用

- 状态在所选项目 `.continuity/state.sqlite3`；原始材料留在原处。**手写草稿、数据库和导出包不要直接提交到公开仓库。**
- 工具本身不调用模型、不上传内容。但你连接的云端助手可能把收到的上下文发给其模型服务；“本地存储”不等于整条链路不出机。
- `export --output review.json` 在项目根新建审阅包，不覆盖。它包含文字和相对文件名，仍可能敏感；不是原始文件备份或数据库导入。
- 备份先停止所有写入者，再复制整个 `.continuity/` 和被引用文件，保留相对路径。恢复到新位置后运行 `status`、`check`。不要并发同步正在写入的 SQLite。
- 停用时移除自己添加的 Skill/客户端配置，关闭对应 MCP 子进程，在新会话确认不再加载；按安装记录移走工具文件即可。**不需要删除项目记忆。**本工具不安装自启动守护进程。

## 失败时怎么办

| 提示 | 下一步 |
|---|---|
| `BUDGET_TOO_SMALL` | 增加字符预算，不裁掉关键限制；字符不是 token |
| `REVISION_CONFLICT` / `STALE_HANDOFF` | 读最新节点、合并进展，再交接 |
| `needs_review` / `EVIDENCE_CHANGED` | 核对文件变化，审阅后保存新节点 |
| `ALREADY_ACCEPTED` | 查询 `receipt`，不要重复外部动作 |
| `NOT_INITIALIZED` / `NO_CHECKPOINT` | 获准后初始化 / 保存首个节点 |
| `UNSAFE_PATH` / `SENSITIVE_CONTENT` | 修正引用或清除敏感内容，不绕过检查 |
| `IO_ERROR` | 保留数据、检查磁盘状态，不删库伪装恢复 |

完整错误、预算、到期与接口规则见[接入说明](adapters/README.md)。CLI 预算统计成功 stdout；MCP 统计完整工具结果，两者不能当作相同的 token 预算。

## 验证与当前限制

```sh
python3 -B -m unittest discover -s tests -v
```

未安装可选 MCP SDK 时，MCP 测试会明确跳过；不能把该次运行说成 MCP 通过。[MCP 安装及测试](adapters/mcp.md) · [完整证据与未验项](docs/verification.md)

文件指纹一致不等于内容正确。这里没有自动调度、语义记忆推理、身份认证、加密存储、远端同步或外部动作“只执行一次”的保证。相同系统用户有磁盘访问权；这是协作工具，不是抵抗恶意同机程序的沙箱。

已完成的真实接力和跨系统 CI 范围见[实测记录](docs/verification.md)。外部真人试用、完整公平效果对照和普通跨系统实机体验仍待验证。未测量 token 节省或返工减少，不宣称优于竞品。许可与预览版发行边界见[来源与许可](PROVENANCE.md)；开发顺序见[实施表](IMPLEMENTATION.md)。

## 许可

[MIT License](LICENSE)。适用于本工具；第三方依赖保留各自许可。
