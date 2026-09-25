# Recaloom · 续珞

`0.1.0-alpha.7` 开发者预览。新增 DeepSeek Harness 的可选自动恢复：明确绑定并启用后，在开始工作前读回项目进度。首次接入默认暂停；普通对话不会自动保存。[实测范围](docs/managed-host-validation.md)。

给用 AI 助手持续做项目的人。把目标、限制、已定事项和下一步留在项目里，换会话后读回；引用文件变了，就先审阅变化。一个助手也能用。

本页对应 v0.1.0-alpha.7，不是稳定版。请使用对应 Release 的具名附件及校验清单；旧版附件不会被替换，更新网页也不会升级你已安装的程序。

[安装与首次使用](INSTALL.md) · [English](README.en.md)

Mac / Linux，先在工具存放目录运行；`.recaloom-alpha7` 必须是新目录，不覆盖已有环境，也不安装到系统 Python：

```sh
python3 -m venv .recaloom-alpha7
.recaloom-alpha7/bin/python -m pip install --no-index --no-deps "https://github.com/fugui6688661/glom-continuity/releases/download/v0.1.0-alpha.7/glom_continuity-0.1.0a7-py3-none-any.whl"
.recaloom-alpha7/bin/glom-continuity --version
```

需要 Python 3.10+，版本应显示 `0.1.0-alpha.7`。固定附件不可用时先核对对应 Release，不换成旧包完成新版教程。Windows 路径替换、本地 wheel 和卸载见 INSTALL。

先跑一次合成演示，输出目录必须尚不存在：

```sh
.recaloom-alpha7/bin/glom-continuity-demo --output ./recaloom-demo
```

打开 `recaloom-demo/演示结果.md`。这是无模型调用的 CLI 协议回放，不是真实模型接力。

## 先用一个助手

安装后，把项目绝对路径、匹配版本的 Skill 绝对路径和工具的可执行命令前缀交给有本地权限的助手：

> 保存这个项目的目标、限制、待确认问题和下一步。下次新会话先只读恢复，告诉我资料是否变化。

安装不会让所有新聊天自动加载项目。wheel 用户需要另外取得匹配的 Skill，不能假定环境里有 `skills/` 或 `scripts/`。照[首次使用卡](docs/first-use.md)保存一个虚构小项目，再开新会话读回来。

保留既有的项目记忆与交接功能：

- `resume`：一次读回项目状态、引用检查、选中的习惯或流程，以及待领取交接。它只读，不自动初始化、保存或领取。
- [项目记忆](docs/project-memory.md)：保存经你确认的习惯和流程，按字面关键词选择；不扫描聊天、不训练模型，也不保证记全。
- `doctor`：查看实际调用的版本、程序位置和项目存储状态。诊断成功不等于数据兼容或发布者身份得到认证。
- [成果回存](docs/result-return.md)：用 `return-work` 将接手产物关联到已领取交接；普通单助手保存不需要交接。

## 让 Harness 自动读回进度

已有 Continuity 项目和受支持的 Harness SDK 时，按[原生适配安装](adapters/harness/native-plugin.md)接入一个独立的[本机 Web 入口](adapters/harness/managed-host.md)，不会改动你原来的 Harness 配置。

用 `/recaloom resume` 启用，`/recaloom pause` 暂停，`/recaloom status` 查看绑定。它只恢复所选项目；切换会话、暂停或引用变化时，不应把旧结果注入新任务。此宿主路径已在 macOS 验证，不代表所有 Agent 都自动接好了。

异常退出后若需要修库，只读恢复会明确拒绝；[单独的恢复流程](INSTALL.md#storage-recovery-after-a-crash)要求先备份，再明确授权，不靠静默重建项目。

## 需要第二个助手时

A 保存并创建交接，B 获准访问同一份本地项目后检查、领取并工作。适合单阶段回存的任务，B 可以用 `return-work` 登记真实产物；A 再读回执和文件。输入或基础版本已变化时要先解决冲突，不能强行关联旧交接。

由你把指令交给另一位助手，工具不会发消息或启动模型。领取回执不证明任务完成、模型身份或外部动作“只执行一次”。不能访问同一项目时，可人工传递经审阅的快照，但没有实时校验或自动回写。

有本地命令权限可用 CLI；支持本地 stdio 的宿主可选 [MCP](adapters/mcp.md)，默认只读。Skill 和插件元数据本身不会授予权限，也不表示客户端已完成安装。[接入合同](adapters/agent-neutral-contract.md)与[版本矩阵](adapters/support-matrix.md)说明各自边界。

## 隐私、费用和停用

基础 CLI 无运行时第三方依赖，不调用模型、不上传项目内容，也不需要模型账号。安装时下载 wheel 会联网；MCP 的 SDK 是另装的可选依赖。连接云端助手后，助手可能把读到的上下文发送给其模型服务，并按自身规则计费。

状态在所选项目的 `.continuity/state.sqlite3`，原文件留在原处。草稿、数据库和导出包可能含私人内容，不要直接公开。备份须先停写，再一起保留 `.continuity/` 和引用文件；不要并发同步正在写入的 SQLite。

停用时移除自己添加的 Skill／客户端连接，关闭对应 MCP 子进程；wheel 可从专用虚拟环境卸载，便携工具可移走。项目记忆可以保留。本工具不安装自启动守护进程。[安装说明](INSTALL.md)有卸载、备份与故障处理步骤；[安全说明](SECURITY.md)列出信任边界。

## 旧用户与实测限制

Recaloom 原名 glom-continuity。仓库、包名、命令、MCP 工具名和项目目录保持兼容；已有项目不要再次 `init`。旧 alpha.5 仍可按原有功能使用，但不会因文档更新而获得项目记忆、`resume`、`doctor` 或 `return-work`。升级步骤见 INSTALL。

[实测记录](docs/verification.md)保留指定版本的 Codex → DeepSeek Harness → 新 Codex 合成接力、协议测试和跨系统 CI，也保留失败与未验项。这些记录不自动成为 alpha.7 包的验收结果。历史接力中曾保留过时的 `next_action` 文字；恢复记录后仍要核对当前任务和回执。

外部真人首次使用、完整公平效果对照、普通 Windows／Linux 实机体验和其他 MCP 宿主仍有未验项。没有 token 节省、返工减少或优于竞品的测量结论。脚本演示是协议回放，不是两个模型在工作；未装可选 SDK 时跳过 MCP 测试，也不算 MCP 通过。

文件指纹一致不等于内容正确。工具没有语义搜索、自动调度、身份认证、加密存储、远端 HTTP 接入或跨设备自动同步，也不是抵抗同一系统用户下恶意程序的沙箱。恢复和产物登记都不能代替业务验收。

[可复用项目方法](docs/field-lessons.md) · [脱敏试用反馈](https://github.com/fugui6688661/glom-continuity/issues/new?template=field_trial.yml) · [来源与预览范围](PROVENANCE.md) · [实施记录](IMPLEMENTATION.md)

## 许可

[MIT License](LICENSE)。第三方依赖保留各自许可。
