# glom-continuity

**换个助手，接着做。**

本地项目检查点与交接工具。记录目标、决定、限制和下一步；接手时，检查引用文件是否还是原来的版本。

“币种还没确认，原始记录不能删。”这些细节和下一步一起保存，供新会话读回。输入文件已经变化？先检查变化，再接受交接。

[English](README.en.md) · [MCP 接入](adapters/mcp.md) · [实测记录](docs/verification.md) · [安全与数据](SECURITY.md)

**当前为 0.1.0-alpha.5 本地候选，尚未公开发布。**CLI、可选 MCP 与标准Python安装入口已实现；早期版本有一个真实 Codex 会话通过 MCP 恢复合成项目并产出文件。这不是当前新版双模型接力通过，也不是“所有 Agent 已验证”。

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

Windows 命令可用 `py -3` 替代 `python3`；目前尚无 Windows 实机通过记录。不提供尚未上架的 `pip install glom-continuity` 命令。

## 怎么接入你的助手

| 你的助手具备什么 | 接入方式 | 已核验到哪一步 |
|---|---|---|
| 本地命令执行与项目访问 | 便携 CLI；可配通用 Skill | 本机公开接口测试通过 |
| 本地 MCP stdio | [可选适配器](adapters/mcp.md)，默认只读 | 协议用例与一个 Codex 0.153.4 真实会话；其他宿主待验 |
| 只能读文件或聊天 | 提供经过审阅的 JSON 快照 | 人工交接，不做实时校验或自动回写 |
| 远端 HTTP / 其他设备 | 后续认证与同步适配 | 尚未实现，不能将本机服务直接暴露出去 |

不限定厂商。Codex、Harness 只是适配样例；客户端能发现工具、真正调用工具、按要求继续任务，分别验证。[通用合同](adapters/agent-neutral-contract.md) · [版本矩阵](adapters/support-matrix.md)

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

真实跨厂商接力、跨系统实机、公平效果对照和外部试用仍须完成。未测量 token 节省或返工减少，不宣称优于竞品。许可及公开发行条件见[来源与许可](PROVENANCE.md)；开发顺序见[实施表](IMPLEMENTATION.md)。

## 许可

[MIT License](LICENSE)。适用于本工具；第三方依赖保留各自许可。
