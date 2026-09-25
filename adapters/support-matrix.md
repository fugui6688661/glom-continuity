# 接入与版本支持矩阵

## Alpha.7：Harness原生自动恢复

2026-09-25本机验证仅对应官方DSH **0.1.5-rc.1**、macOS、独立受管Web profile，不是下方Alpha.6发行包的能力。已验原生执行引擎的合成恢复合同、安装wheel的公开CLI、真实鉴权页面、目录选择、命令反馈、正常重开暂停和停用保留数据。[详细记录](../docs/managed-host-validation.md)保留中央工作区选择显示问题。

该启动器只支持POSIX，实际宿主运行与界面验证仅在macOS完成；没有验证Windows宿主。日常profile迁移、自动保存、真实模型效果及其他Agent生命周期适配尚未完成。不能用通用CLI/MCP可调用来替代这些宿主层验收。

Alpha.7 保留基础工具并新增 CLI-only `recover-storage`，共 13 个核心 CLI 命令；MCP 仍是默认 6 个只读工具、显式启用写操作后 12 个，不会自动取得修库权限。[本轮 CI](../docs/platform-validation.md)已跑过四环境和独立 macOS 宿主检查；不代表每个宿主的 GUI 或真实模型效果通过。

## Alpha.6 历史范围：工具能力与宿主实接分开

Alpha.6 提供 12 个 CLI 命令；本地 MCP 默认 6 个只读工具，启用写操作后共 12 个。安装见 [INSTALL](../INSTALL.md)，具体工具见 [MCP 接入](mcp.md)。没有远端 HTTP 服务、跨电脑实时同步或一键替所有宿主配置 MCP。

本版本的协议、发行包、安装和升级验证见[实测记录](../docs/verification.md)。这些测试不替代真实宿主运行。下面的成功跨厂商接力仍只属于 Alpha.5，不能扩展为 Alpha.6 新 Skill、DSH MCP 或其他宿主已通过。2026-09-15 的同模型试点仍未得出效果对照结论。

## 历史真实模型实测（2026-09-14，Alpha.5）

以下对应不可变 Alpha.5，不是 Alpha.6 的新模型实测。维护者已记录 macOS 上 Codex 0.154.0-alpha.6.2 → DSH 0.1.5-rc.1 → 新 Codex 的合成订单接力；经历过启动/传输失败后完成恢复，原失败保留。模型标记为 gpt-6-astra low 和 `deepseek-flash` low（提供方别名不证明隐藏的模型修订）。

本地命令接力与 MCP 是不同接入路线：上述结果不证明 DSH 的 MCP 配置或自动发现已通过；Codex 0.153.4 的只读 MCP 实测仍是另一项有日期的证据。其他宿主、其他版本、跨电脑同步均不能据此标成兼容。

准确用例、源版本和限制以[2026-09-14 实测摘要](../docs/verification.md#current-alpha5-evidence--2026-09-14)为准。下方 9月12日的“尚无新增/未验收”只描述当时快照，不是当前的总判断。

## 2026-09-12 后续实测增量

Codex CLI **0.153.4**：在 macOS 26.4.1 arm64、Python 3.12.14、MCP SDK 2.2.0 上，一个真实新会话调用 `continuity_status/check/context`，恢复合成项目并写出订单说明。只读MCP入口已实际使用；不是完整跨厂商交接。具体源码指纹、产物与限制见[实测记录](../docs/verification.md)。未修改全局配置，没有据此标记桌面自动加载、其他客户端或其他系统通过。

## 首轮入口核查快照（保留原核查时点）

以下表格及PATH描述是当天更早的只读探测，不表示后续实测仍未发生。Codex新增行为证据以上节为准；DSH尚无新增实接通过结果。

核查日期：2026-09-12。证据分级：`VERIFIED LOCAL` 本机命令/安装文件；`DOCUMENTED` 已打开的官方文档；`PREVIEW` 官方预发布；`UNVERIFIED` 未实测或范围外。版本仅对所列二进制/包有效，不声称最低兼容版本或任意后续版本均支持。

| 对象/版本 | 实际入口与证据 | 项目文件适配 | Continuity CLI / 模型实接 |
|---|---|---|---|
| Codex CLI **0.153.4** | `VERIFIED LOCAL`：`/Applications/ChatGPT.app/Contents/Resources/codex --version`；`--help`、`exec --help` 退出 0；均在禁止写盘/联网的外层沙箱中执行 | `DOCUMENTED`：可从项目 `.agents/skills` 发现 skill；本轮只提供未安装模板 | CLI 二进制帮助可调用；未在 Codex 模型任务中调用 Continuity；模型实接 `UNVERIFIED` |
| 本机桌面包 **26.903.71938 / build 8576** | `VERIFIED LOCAL`：`ChatGPT.app/Contents/Info.plist` 的两个版本字段；它包含上行 Codex 二进制 | 桌面包版本不等于 CLI 版本，也不单独证明模板加载 | 不打开、重启或修改活动 App；其 Continuity 实接 `UNVERIFIED` |
| `@deepseek-ai/dsh` **0.1.0-rc.6** | `VERIFIED LOCAL`：DSH Desktop 内置 Node 执行内置 `lib/bin.js --version/--help`，退出 0；包名、版本、bin 和官方 repository 字段一致 | `VERIFIED LOCAL`（静态源码）：项目 `.dsh/skills` 与 `.agents/skills`；`DOCUMENTED`：官方 master 文档同样说明这两个入口 | 仅启动器帮助可调用；未 boot profile、未跑模型；模板运行 `UNVERIFIED` |
| DSH Desktop **0.2.6** | `VERIFIED LOCAL`：桌面壳 plist 版本；打包 manifest 依赖 rc.6 | 壳版本不能当作 Harness 版本 | 没有接入此 App；不推定任何活动 profile 正在使用哪个 runtime |
| 官方历史 **dsh-v0.1.0-rc.8 / 141eb6f** | `PREVIEW`：2026-08-19 发布页；提到可选 Codex/Claude Code 子代理 Bundle | 不据此把本机 rc.6 升格为 rc.8 | 未安装该版本；Bundle 能力不等于 Continuity 两模型接力 |
| 官方列表顶部 **dsh-v0.1.5-rc.2 / fb2c4b9** | `PREVIEW`：本次官方发布页显示 2026-09-10、预发布 | master 文档是滚动文档，不与本机 rc.6 或此 tag 自动等同 | 未升级、未运行、未做兼容回归 |
| 其他 Codex/DSH 版本及本机自定义 Harness 壳 | `UNVERIFIED` | 需逐版本/入口复核；无隐式兼容承诺 | 不研究或运行自定义第三方仓库，不接触 Core |

本次 PATH 中 `command -v codex`、`command -v dsh`、`command -v harness` 未命中。不能写成“机器未安装”；已找到的内置入口不需要添加到 PATH，也没有修改 PATH/全局配置。

## 已核对的命令差异

- Codex 本机帮助支持 `-C/--cd`，`exec --json` 是**模型事件 JSONL**；它不等于 Continuity 的单次 `ok/code/data` 业务响应。`exec --ephemeral` 的帮助称不保存会话文件，但不等于不使用账号、不计费或整个客户端没有其他副作用，故没有运行会话。命令类别与 [官方 CLI 参考](https://learn.chatgpt.com/docs/developer-commands?surface=cli) 对照。
- DSH 的 `web` 是 profile 入口；`--profile headless "job"` 会运行一个新持久化会话，不是离线诊断。顶层 `--help` 与 `--profile web --help` 不同，后者会进入 profile 路径。本轮只运行顶层版本/帮助，没运行配置 dump 或 plugin 管理。[官方启动器文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/cli/README.md)
- Codex 官方 skill 根规则是从 cwd 向仓库根扫描 `.agents/skills`；没有文档依据把 `AGENTS.md` 当可随意覆盖的配置容器。[官方 skill 文档](https://learn.chatgpt.com/docs/build-skills)
- DSH 本机 rc.6 的 `dsh-skill-filesystem/lib/index.js` 行 150–165、799–805 证明两个项目目录及最近 `.git` 祖先规则；并非所有嵌套子目录都被独立视为项目根。官方滚动文档另见 [skills 子系统](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md)。这也是默认提供手动文件接入、不默默扩大到仓库根的原因。

## 官方版本来源与局限

- [rc.8 发布页](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.1.0-rc.8)：只证明预发布说明，非本机安装或执行证据。
- [rc.2 发布页](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.1.5-rc.2) 与 [发布列表](https://github.com/deepseek-ai/deepseek-harness/releases)：只记录本次看到的顶部版本，不推断 npm 分发标签。
- rc.6 的 `dsh-v0.1.0-rc.6` tag 文档/发布页本次抓取返回 404；没有把失败解释为版本不存在。rc.6 的准确包版本及发现规则以本地随包 manifest、README、源码和帮助为证，不以 master 文档伪装该 tag 的冻结文档。

命令输出和路径详见 [本机核查记录](local-command-evidence.md)。所有已实核项都止于本机入口、静态文件与 CLI 只读探测；两个模型续接能力仍没有验收证据。

## 历史：2026-09-12 项目协议同步

本轮仅更新自有协议材料，以上客户端版本/官方来源保留首轮 2026-09-12 的核查时点，未重新启动客户端或模型。当前模板覆盖九命令：`init/status/check/checkpoint/context/handoff/accept/receipt/export`，本轮九条 `--help` 均退出 0。`receipt --id UUID` 只读查询；`export --output simple.json` 显式新建 review 文件、不覆盖；二者不是客户端原生会话命令。`no_references` 允许明确缺证的纯规划继续，不是 verified。详见 [接入说明](README.md)。主线程将独立做干净项目协议回放，不能用该回放替代 DSH 模型实接证据。
