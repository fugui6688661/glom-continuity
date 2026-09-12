# 两助手接入就绪核查

日期：2026-09-12。结论：**适配材料已制作，尚未安装到用户项目，未证明模型实接。**

## 已实核

- Codex 内置 CLI：`0.153.4`；桌面包 `26.903.71938 / 8576`。版本、顶层帮助及 `exec --help` 在禁止写盘/联网的沙箱内退出 `0`。
- DSH 内置 CLI：`0.1.0-rc.6`；桌面壳 `0.2.6`。通过明确的内置 Node 和 `lib/bin.js` 跑顶层版本/帮助，退出 `0`。
- 本机 DSH skill provider 静态源码支持 `.dsh/skills` 和 `.agents/skills`，Codex 官方文档支持后者；发现目录不等于两个模型已经使用模板。
- 已提供两份默认禁用、需填写用户项目和项目自有 CLI 的模板，安装/撤回说明和版本支持矩阵。不创建客户端配置，不覆盖 `AGENTS.md`、`CLAUDE.md`，不读写原生会话 DB。

## 阻塞与分工

| 项目 | 状态/下一步 |
|---|---|
| 文件模板/材料 | 已同步九命令及缺证分支，静态复核见下；不是安装证据 |
| 用户项目安装 | 必须另选项目和助手；本轮没有选择或初始化业务项目 |
| Continuity 命令合同 | 已按主线程确认的九命令及全部参数更新，九条子命令 `--help` 均退出 0；JSON 错误路径另列，不改核心代码 |
| CLI 业务验收 | 由主线程独立做干净项目协议回放，含 receipt 只读、export 不覆盖和 no_references 规划路径；本成员终端仅只读，不代报回放结果 |
| Codex / Harness 模型实接 | 未运行模型会话，未检查认证或付费额度；需要另行允许对应会话及潜在费用 |
| 双模型接力 | 无真实两端读取/调用/续接证据，不可宣称成功 |

官方当前发布说明与本机版本不同：rc.8 是历史预发布，发布列表顶部已是 `dsh-v0.1.5-rc.2`；本机仍只核实到内置 rc.6，没有升级或据此推定兼容。

## 文件与证据

- [安装与撤回](../adapters/README.md)
- [准确版本与支持边界](../adapters/support-matrix.md)
- [Codex 模板](../adapters/codex/continuity-codex/SKILL.md)
- [Harness 模板](../adapters/harness/continuity-harness/SKILL.md)
- [具体命令、退出码与原始错误摘要](../adapters/local-command-evidence.md)

## 最终回读

- `init/status/check/checkpoint/context/handoff/accept/receipt/export --help` 九项均退出 `0`，参数与主线程通知一致。早期五/七命令快照保留为历史记录，不再当作当前接口。
- 两模板明确：`context --max-chars N` 预算包含整个 stdout（JSON 与换行），正文取 `data.text`；`recipient` 只是协作标签；`accept` 不带 revision 参数；草稿恰好六字段；哈希通过不等于完成；没有 Agent/模型启动或自动消息发送。
- 新增 `receipt --id UUID` 只读核回执；必须核对 `state: accepted` 与 accepted_at，不能仅凭查询成功说已接受。新增独立 `export --output simple.json` 只新建 review 元数据、不覆盖，绝不是 `handoff --output`，也不是跨项目导入/权限授予。
- `check.data` 与 `context.data.check` 的 `no_references` 分支均允许用户已授权的纯规划继续，但须明确“无文件证据”，不称 verified/产物通过；`needs_review`/issues 则停止依赖该状态的任务继续。只读回执和获准 review 导出不因缺证被一律阻塞。
- **仍有一个本机接口反例**：未初始化目录执行 `status`，退出 `2`，返回 `{"code":"NOT_INITIALIZED","error":"Initialize this project first","ok":false}`，缺少合同要求的 `data`。主线程需修复并回归；本成员不改 CLI，也不把用户确认的合同当成该错误路径已通过。
- skill-creator 的 Python 校验器缺 PyYAML，未通过、未安装依赖；改用系统 Ruby 的 YAML/JSON/路径解析做只读校验，退出 `0`。这只验证材料结构，不证明客户端加载或模型行为。

## 写入边界

本成员仅用 `apply_patch` 写 `adapters/` 内材料和本文件；未修改 CLI、内部 loader、Core 或活动 App。其他成员正在并行写核心实现，项目整体新增文件不能归因于本成员，也不能用整体目录状态冒充独占修改审计。

## 追加修复结果：九命令、可移植展示与失败 envelope

2026-09-12 追加；上文历史核查原样保留。最新接口与阻塞以本节和命令证据第 8–9 节为准。

- 当前是九命令，不停留在七命令：`init/status/check/checkpoint/context/handoff/accept/receipt/export`；九条 `--help` 均退出 `0`。两模板默认禁用，仍需用户另选项目，只指向该项目自有 CLI 与状态。
- receipt 只读核回执，查询成功不等于已接受；export 独立新建 review 文件、不覆盖，不是 `handoff --output`。`no_references` 允许明确缺证的纯规划继续，不能称产物通过；context 内的 check 使用同一规则。
- **上文 NOT_INITIALIZED 缺 data 的实测反例已修复**：同一沙箱中再跑未初始化目录的 `status`，退出 `2`，原文为 `{"code":"NOT_INITIALIZED","data":null,"error":"Initialize this project first","ok":false}`。这只覆盖该错误路径；全失败 envelope/干净项目协议回放由主线程独立验证，不预填其成绩。
- 已按 skill-creator 保持指引型模板，并用系统 Ruby 只读复核 YAML、禁用绑定、九命令、精确 draft JSON 和六份 Markdown 的本地链接/围栏，退出 `0`；不把静态通过当作客户端实接。
- `adapters/local-command-evidence.md` 的个人绝对路径改为 `<HOME>` / `<TOOL_ROOT>`，明确声明原始本地核查已执行、此为脱敏展示；历史输出语义保留。适配材料中不放个人路径或全局状态引用作为安装依赖。
- 边界未变：本成员没有初始化/安装业务项目、没有执行 receipt/export 成功流程或写操作、没有模型调用；主线程的 CLI 回放不是 DSH 模型实接证明。
