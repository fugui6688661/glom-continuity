# 安装与第一次使用 / Installation and first use

需要 Python 3.10+。这是 CLI 与可选 MCP 连接器，不是聊天 App；工具、演示与工作资料分开存放。
Requires Python 3.10+. This is a CLI with optional MCP, not a chat app. Keep the tool, demos and working data separate.

## 先选版本 / Choose the delivery

- **公开 Alpha.5 / Released preview:** 从[发布页 / release page](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.5)下载命名附件 `glom-continuity-0.1.0-alpha.5.zip` 或对应 wheel，不是自动生成的 Source code。无新记忆或 `resume`，不是稳定版。 Use the named ZIP or matching wheel, not the automatic Source code archive. No development memory or resume; not stable.
- **已提供 dev3 候选/源码 / Provided dev3 candidate or source:** `0.1.0.dev3` 尚未公开发布；使用维护者已提供的工具目录或候选 wheel，核对 `--version` 与帮助。此处没有 dev3 公共下载链接；未拿到时不能用 Alpha.5 代替记忆教程。 Use the already-provided directory or wheel and check version/help. There is no public dev3 download here; Alpha.5 cannot substitute for the memory walkthrough.

目前没有 PyPI/应用商店版本，不从同名陌生软件安装。 No PyPI/app-store release is offered; avoid unrelated namesakes.

公开下载的 `SHA256SUMS` 与 ZIP/wheel 放同一目录：Mac/Linux 用 `shasum -a 256 -c SHA256SUMS`（全部校验需两个文件）；Windows 用 `Get-FileHash 文件名 -Algorithm SHA256` 逐项比较。候选只对照其配套清单，不套用 Alpha.5 哈希。
For public assets, verify the accompanying SHA256SUMS with those commands; download both assets to check every entry. A provided candidate needs its own manifest. Hashes check integrity, not a publisher signature.

## 便携包或源码 / Portable package or source

进入已解压包或已提供源码的 README 所在目录；不安装依赖、不调用模型。 From that tool directory, no dependencies or model calls are needed:

```sh
python3 -B scripts/continuity.py --version
python3 -B scripts/smoke_demo.py --output ./my-first-demo
```

Windows 将 `python3` 换成 `py -3`。输出目录必须不存在。打开 `my-first-demo/演示结果.md` 查看协议回放；**不是两个模型，也不是新增 resume 的验收**。
On Windows substitute `py -3`. Use a new output directory; nothing is overwritten. Read the generated report for synthetic protocol behavior, not a live-model trial or resume acceptance result.

## 安装成命令 / Install a local wheel

以下是 Alpha.5 wheel 示例；dev3 仅在收到候选 wheel 后，把文件名替换为实际收到的文件。只有源码则走上面的便携路径。基础安装不联网、不调用模型；新建独立环境，不覆盖已有环境。
These examples use the Alpha.5 wheel. For dev3, substitute the exact provided candidate wheel filename; source-only users take the portable route. Base installation is offline and makes no model calls. Use a new environment, not an existing one.

Mac / Linux：

```sh
python3 -m venv .continuity-tools
.continuity-tools/bin/python -m pip install --no-index --no-deps ./glom_continuity-0.1.0a5-py3-none-any.whl
.continuity-tools/bin/glom-continuity --version
.continuity-tools/bin/glom-continuity-demo --output ./installed-demo
```

Windows PowerShell:

```powershell
py -3 -m venv .continuity-tools
.\.continuity-tools\Scripts\python.exe -m pip install --no-index --no-deps .\glom_continuity-0.1.0a5-py3-none-any.whl
.\.continuity-tools\Scripts\glom-continuity.exe --version
.\.continuity-tools\Scripts\glom-continuity-demo.exe --output .\installed-demo
```

无需管理员权限、全局 PATH 或 PowerShell 策略修改。平台/历史结果见[验证记录 / verification](docs/verification.md)，本文不新增通过记录。
No admin access, global PATH or PowerShell-policy changes are needed. The dated verification record, not these commands, defines tested coverage.

## 给助手正确的命令位置 / Bind the assistant to the right command

把[通用 Skill / generic Skill](skills/project-continuity/SKILL.md)、明确选择的项目绝对路径与下面一种**绝对命令前缀**交给有本地权限的助手：
Give an authorized assistant the Skill, the selected project's absolute path and one absolute command prefix:

- 便携/源码 / Portable/source: `python3 -B /absolute/tool/scripts/continuity.py`（Windows: `py -3 -B ...`）。
- Wheel: `/absolute/tool-env/bin/glom-continuity`，或 `/absolute/tool-env/bin/python -B -m glom_continuity`。Windows 用环境内 `Scripts/glom-continuity.exe` 或 `Scripts/python.exe -B -m glom_continuity` 的绝对路径 / use absolute environment paths.

后接 `--project <项目绝对路径>` 与命令；README 的脚本前缀可替换成选定前缀。wheel 不要求旁边存在 `scripts/continuity.py`，也不猜全局安装。路径含空格时分别安全引用。
Append `--project <absolute-project>` and the command. Replace README script prefixes with this binding; a wheel route does not require a sibling source tree. Quote paths safely; do not guess a global installation.

首次可说：“保存这个项目的目标、限制、待确认问题和下一步。”下次说：“恢复这个项目，告诉我资料是否变化和下一步。”
Try: “Save this project's goal, constraints, unresolved questions and next step.” Later: “Recover this project; tell me what changed and what comes next.”

帮助确认有 `resume` 后，恢复用 `resume --query "video" --max-chars 10000`；MCP 发现对应工具后用 `continuity_resume(query="video", max_chars=20000)`。它只读，不自动 init/save/accept；无记录时报告，保存需另有授权。默认完整响应预算 6000，MCP 包装计入预算；不足报错，不截断。详见 [恢复分流 / recovery states](skills/project-continuity/SKILL.md)。
Use resume only after help/tool discovery confirms it. Recovery is read-only, grants no new authority, and does not initialize, save or accept. It reports missing records; saving requires authorization. The default full-response budget is 6000, including MCP wrapping; insufficient budgets fail without truncation.

旧包仍先 status；有节点才 check → context。Alpha.5 不支持记忆/query；`init` 只建存储，`NO_CHECKPOINT` 是未保存，不是网络故障；坏库不能当新项目。无需全局钩子、整机权限或聊天导入，也不保证新会话自动加载。
Older packages use status, then check → context only with a checkpoint. Alpha.5 has no memory/query. Initialization alone saves no memory; NO_CHECKPOINT is not a network failure. Corrupt storage remains an error. No global hook, whole-computer access or chat import is needed; automatic new-session loading is not guaranteed.

## 可选 MCP / Optional MCP

按[MCP 接入 / MCP setup](adapters/mcp.md)配置。在独立环境安装可选依赖 / install the optional dependency in the separate environment:

```sh
.continuity-tools/bin/python -m pip install 'mcp==2.2.0'
```

这一步联网下载第三方依赖；Windows 换成 `.\.continuity-tools\Scripts\python.exe`。启动命令指向环境内 `glom-continuity-mcp` 的绝对路径（Windows 为 `.exe`），启动参数是 `--project` 与项目绝对路径，单次 MCP 调用不传项目。
This downloads third-party dependencies. Use the environment's absolute MCP executable with `--project` at startup; individual calls take no project argument. On Windows use the environment Python/executable paths above.

默认只读；授权保存/领取时才显式配置 `--allow-writes`，不绕过只读限制，也不授予邮件、付款或发布权限。云端助手仍按自己的计费/隐私规则处理收到的上下文。
Read-only is the default. Enable `--allow-writes` explicitly for authorized writes/acceptance; do not bypass it. This grants no email, payment or publication authority. Cloud assistants retain their own pricing/privacy rules for received context.

## 自己验收 / Check your first use

用非敏感小项目保存后，在新对话恢复，检查限制和未知项是否保留；只有口头“记住了”不算通过。若测试接力：A 保存并交接 → 新 B 检查/领取/工作/保存并交回 → 新 A 读回结果。需要共享同一份本地项目，不提供跨电脑同步；只读快照不等于实时校验/回写。
Save a non-sensitive project, then recover in a fresh session and inspect constraints and unknowns. A verbal “remembered” is insufficient. For a relay, A saves/hands off; fresh B checks, accepts, works, saves and returns it; fresh A reads the result. Both need the same local project. Snapshots are not live checking/writes; no cross-device sync is supplied.

## 停用与反馈 / Removal and feedback

只移除自己添加的 Skill/客户端配置，关闭 MCP 子进程，在新会话确认不再加载；wheel 可卸载 / remove only added Skill/client entries, close the MCP child process and verify it no longer loads in a new session. Uninstall the wheel with:

```sh
.continuity-tools/bin/python -m pip uninstall glom-continuity
```

Windows 同样换用环境内 Python；便携版只移走工具文件。保留项目 `.continuity`，不删库排错。备份先停全部写入，再复制完整 `.continuity` 和引用文件，保留相对路径。
Use the environment Python on Windows; portable users can move the tool files. Keep project data. For backups, stop all writers and copy the whole `.continuity` plus referenced files, preserving relative paths; never delete the database to disguise a failure.

反馈只附版本、失败步骤、错误码与虚构复现，不发送密钥、公司资料或原始聊天。
Report OS/Python/assistant versions, failed steps, error codes and a synthetic reproduction—not secrets, company data or raw chats.
