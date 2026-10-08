# Recaloom XS v0.2.0 安装指南 / Installation guide

**本页对应 XS v0.2.0。** 本文面向普通用户和工程团队的项目级 CLI 安装、保存与接续。下载以该具名 Release 附件为准；若无附件，不要用旧包冒充。团队固定包须由维护者明确提供并核对摘要。

**This page covers XS v0.2.0.** These instructions target the project-level CLI. Download assets from the named Release; if they are absent, do not substitute an older package. Team trials may use an explicitly supplied, verified fixed package from the maintainer.

需要 Python 3.10+，含 venv / pip。CLI 无第三方运行时依赖，不需要模型账号，也不调用模型。工具环境、测试项目和正式工作资料应分开存放；不需要管理员权限、全局 PATH 修改或 Harness。

[安装 wheel](#wheel-install) · [首次保存](docs/first-use.md#first-save) · [项目入口](#project-entry) · [升级](#upgrade-existing) · [停用/卸载](#preserve-data-removal) · [历史 Alpha.7](#public-alpha7)

## 选择一条路线 / Choose one route

- **新用户**：按下面安装 wheel；或者已按 [README](README.md)/[English README](README.en.md) 的发布直链安装，直接去首次保存，不重复建环境。
- **已有项目/旧安装**：先看[升级](#upgrade-existing)，保留旧工具和原项目，不重新 init。
- **收到完整固定源码/便携包及 wheel**：可以选择[带摘要的一步环境安装器](#xs-candidate)，不是普通 wheel 安装后的追加步骤。
- **历史 Alpha.7 用户**：原件与能力保持原样，见[历史兼容](#public-alpha7)。

安装包的兼容名称仍是 `glom-continuity`。本指南不提供 PyPI、Homebrew 或应用商店入口，不从同名陌生软件安装。网页更新不会升级本机程序。

Use either the wheel instructions below, the README's direct Release URL, or the optional verified-package installer—not all three. Existing projects retain their storage and use the upgrade path. There is no automatic updater or PyPI/Homebrew/app-store installation route in this guide.

<a id="wheel-install"></a>

## 1. 安装 wheel / Install the wheel

### 先取得并核对文件 / Get and verify the file

具名 Release 与附件（先确认存在）：

- [v0.2.0 Release](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.2.0)
- [glom_continuity-0.2.0-py3-none-any.whl](https://github.com/fugui6688661/glom-continuity/releases/download/v0.2.0/glom_continuity-0.2.0-py3-none-any.whl)
- [SHA256SUMS](https://github.com/fugui6688661/glom-continuity/releases/download/v0.2.0/SHA256SUMS)

**链接仅在对应附件已上传时有效。** 未提供附件时停止，不用 Alpha.7 的文件或摘要顶替。若使用团队固定包，核对维护者明确给出的文件来源及该 wheel 自己的 SHA-256。wheel、源码归档和安装后程序是不同对象，摘要不能互相比相等。

下载到工具存放目录后，用下列命令显示 wheel 摘要，与对应清单的该文件条目逐字比较：

~~~sh
shasum -a 256 glom_continuity-0.2.0-py3-none-any.whl
~~~

Linux 没有 `shasum` 时可用 `sha256sum glom_continuity-0.2.0-py3-none-any.whl`。Windows PowerShell：

~~~powershell
Get-FileHash -LiteralPath ".\glom_continuity-0.2.0-py3-none-any.whl" -Algorithm SHA256
~~~

校验不一致就保留文件并停止。若使用 `shasum -a 256 -c SHA256SUMS`，须备齐清单列出的文件；只下载 wheel 时比较它自己的条目即可。哈希核对是完整性检查，不是发布者签名认证。

Check that the named Release assets exist. Compare the wheel's own SHA-256 with the matching Release checklist or the maintainer's explicit fixed-package record. Do not substitute an old asset, compare digests of different objects, or treat a checksum as publisher authentication.

### macOS / Linux

确认 wheel 摘要后，在它所在的工具目录执行。环境名必须尚不存在；失败保留现场，不覆盖旧环境：

~~~sh
(
  set -eu
  if [ -e .recaloom-xs-0.2.0 ] || [ -L .recaloom-xs-0.2.0 ]; then
    echo "Environment exists; follow the upgrade guide." >&2
    exit 1
  fi
  python3 -m venv .recaloom-xs-0.2.0
  .recaloom-xs-0.2.0/bin/python -I -m pip install --no-index --no-deps ./glom_continuity-0.2.0-py3-none-any.whl
  .recaloom-xs-0.2.0/bin/python -I -B -m glom_continuity --version
  .recaloom-xs-0.2.0/bin/python -I -c "import sys; print(sys.executable)"
)
~~~

### Windows PowerShell

同样在已核对 wheel 的目录运行：

~~~powershell
if (Test-Path -LiteralPath ".recaloom-xs-0.2.0") { throw "Environment exists; follow the upgrade guide." }
py -3 -m venv .recaloom-xs-0.2.0
if ($LASTEXITCODE -ne 0) { throw "Environment creation failed." }
& ".\.recaloom-xs-0.2.0\Scripts\python.exe" -I -m pip install --no-index --no-deps ".\glom_continuity-0.2.0-py3-none-any.whl"
if ($LASTEXITCODE -ne 0) { throw "Installation failed; preserve the environment for diagnosis." }
& ".\.recaloom-xs-0.2.0\Scripts\python.exe" -I -B -m glom_continuity --version
if ($LASTEXITCODE -ne 0) { throw "Version check failed." }
& ".\.recaloom-xs-0.2.0\Scripts\python.exe" -I -c "import sys; print(sys.executable)"
~~~

版本应为 `0.2.0`。保留最后输出的 **Python 绝对路径**；无需激活环境或修改 PowerShell 执行策略。若没有 `py`，需先准备可信的 Python 3.10+ 安装并使用它的完整路径，不猜另一个全局 Python。

本地 wheel 安装不查包索引、不下载依赖、不调用模型。README 的直链方式会联网下载具名 wheel。缺少 venv / pip 时，先按所用 Python 发行版的方式补齐，不改成系统级 pip 安装或使用管理员权限绕过。

Expect `0.2.0` and keep the final absolute Python path. Local-wheel installation is offline; the README URL route downloads the named asset. No activation or administrator access is required. Missing venv/pip is a Python-installation issue, not permission to overwrite system Python.

### 安装后：直接首次保存 / Next: first save

v0.2.0 wheel **已带匹配 Skill 和指南**，无需另找文档。将工具 Python 和**由你提供的项目绝对路径**交给助手，使用[首次使用卡](docs/first-use.md#first-save)；英文提示词见 [English checklist](docs/first-use.md#english-checklist)。

完整调用前缀为：

~~~text
<工具Python绝对路径> -I -B -m glom_continuity
~~~

后接 `--project <项目绝对路径> doctor`。查看：

- `data.version`、`runtime.program_path/program_sha256`：实际调用的是哪份程序。
- `data.usage.state=available`：用其绝对 `skill_path` 读取匹配指南。`unavailable` 先看 issues；不借用别处同名 Skill。`source_unsealed` 仅表示源码布局，不是已校验 wheel。
- `storage`：已有存储须兼容；`not_initialized` 只允许在明确首次保存授权下初始化。诊断 `ok:true` 不等于项目已经可恢复。

指南检查是本地清单一致性，不是宿主加载或发布者认证。安装本身不初始化项目、保存进度或配置助手。

Use the same interpreter with `-I -B -m glom_continuity` throughout. Doctor locates the bundled guide: use `data.usage.skill_path` when `state=available`, inspect storage separately, and stop on a mismatch. Installation does not create project memory, integrate a host or enable automatic saving.

### 可选无模型演示 / Optional offline demo

不需要演示也能直接使用。想先观察协议，可在新输出目录运行：

~~~sh
.recaloom-xs-0.2.0/bin/glom-continuity-demo --output ./recaloom-demo
~~~

Windows：

~~~powershell
& ".\.recaloom-xs-0.2.0\Scripts\glom-continuity-demo.exe" --output ".\recaloom-demo"
~~~

输出目录必须不存在。打开其中的 `演示结果.md`；这是合成 CLI 协议回放，不是实际模型/真人接续的验收。

<a id="xs-candidate"></a>

## 可选：固定完整包的一步安装器 / Verified-package installer

此锚点保留旧 XS 候选文档链接。v0.2.0 固定源码/便携包提供 `scripts/runtime_env.py`；只拿 wheel 的普通用户用上面的路线，不必另下源码。

在核对完整包来源/摘要并解压后，进入其根目录，替换下面三个值：新环境绝对路径、可信本地 wheel 绝对路径、**该 wheel 的 64 位 SHA-256**。环境父目录须已存在，环境本身不能存在：

~~~sh
python3 -I -B scripts/runtime_env.py create --directory "/absolute/tools/recaloom-xs-0.2.0" --wheel "/absolute/downloads/glom_continuity-0.2.0-py3-none-any.whl" --sha256 "<wheel的64位SHA-256>"
~~~

Windows PowerShell 对应完整写法：

~~~powershell
py -3 -I -B scripts/runtime_env.py create --directory "C:\Tools\recaloom-xs-0.2.0" --wheel "C:\Downloads\glom_continuity-0.2.0-py3-none-any.whl" --sha256 "<wheel的64位SHA-256>"
~~~

成功 `TOOL_READY` 后直接用返回的 `data.cli_argv` 参数数组进行首次保存，不再运行 venv/pip。逐项保留解释器和参数，不把整串当作一个可执行文件名。`host_integrated=false`：仍未接入任何宿主或启用自动保存。

带 `--wheel/--sha256` 时先校验，再创建环境、离线安装、检查已安装程序和指南。二者必须成对提供；同时省略仅准备环境，返回 `RUNTIME_READY`，不表示工具已安装。已有目标（包括空目录、文件、链接）拒绝，失败保留已创建的部分环境，不自动重试。

需要诊断环境时，用可信基 Python 运行：

~~~sh
python3 -I -B scripts/runtime_env.py check --directory "/absolute/tools/recaloom-xs-0.2.0"
~~~

Windows 换用 `py -3` 和相应绝对路径。`check` 不安装或修复。保留基 Python，不把 venv 当可移动包；POSIX 默认符号链接、Windows 默认副本。失败检查 `phase/exit_code/next_step/child_cleanup`，不要设 DYLD 变量掩盖错误。POSIX 清理只涵盖仍持有身份的进程组；脱离组的后代、已回收组首和 Windows 整棵进程树不声明清理已确认。

This optional installer requires the matching full package, trusted local wheel and its own digest. Keep all elements of `data.cli_argv` after `TOOL_READY`; do not reinstall. Bare environment creation returns only `RUNTIME_READY`. Existing destinations are refused and partial failures retained. Runtime diagnosis is not a sandbox for an untrusted interpreter or wheel.

## 2. 保存与恢复 / Save and recover

[首次使用卡](docs/first-use.md)提供可直接交给助手的首次保存与新会话提示词，包含六字段草稿、项目 ID/修订校验和读回检查。下文 `<cli>` 是上面完整解释器前缀，`<project>` 是用户给定的已有项目绝对路径；代码中这些占位符必须替换。支持参数数组时逐项调用，shell 中分别引用，PowerShell 用 `&` 调用首项。

`resume` 只读：不初始化、不保存、不自动接受交接。状态区分：

| 状态 / State | 处理 / Action |
| --- | --- |
| `not_initialized` | 只有获准首次保存才 init / Initialize only for an authorized first save |
| `no_checkpoint` | 存储已有但无保存，不重复 init / Save when authorized; do not reinitialize |
| `needs_review` | 先审阅引用变化 / Review references before continuing |
| `no_references` | 仅规划恢复，无文件验收 / Planning only, no verified artifact |
| `restored` | 读回目标/限制/下一步；仍按当前授权行动 / Recovered context is not new authority |

预算覆盖完整响应字符数，不是 token；`BUDGET_TOO_SMALL` 时增加 `--max-chars`，不删约束凑预算。未知状态、坏库、项目或修订冲突都要先报告，不能删库/重建/换绑定绕过。

<a id="project-entry"></a>

## 3. 可选项目入口：保留用户规则 / Optional project entry

先完成一个检查点，再决定是否接入一个所选宿主。**CLI 可独立使用；自动加载和保存不是安装结果。**

### 手动绑定卡：各平台的基础入口 / Manual binding

~~~text
<cli> --project <project> setup
~~~

这是只读预览。`ready_for_manual_binding` 返回程序、指南、项目身份与 `doctor_argv/resume_argv`。给获准访问该项目的助手，先对照 doctor 检查摘要/项目 ID/指南，再执行恢复参数数组。`requires_initialization` 不是自动初始化授权。卡片含本机路径，不公开。

### 新建或合并规则 / Create or integrate a rule

选择一个 `--host`，不是一次授权全部宿主：

| host | 固定项目入口 |
| --- | --- |
| `codex` | `AGENTS.md` |
| `claude-code` | `.claude/rules/recaloom.md` |
| `workbuddy` | `.codebuddy/CODEBUDDY.md` |

没有入口时，先预览，获准后才写入：

~~~text
<cli> --project <project> setup --host codex
<cli> --project <project> setup --host codex --write-instructions
~~~

已有个人规则时，**不覆盖、不删除、不拿空文件替换**，改用合并预览：

~~~text
<cli> --project <project> entry integrate --host codex
<cli> --project <project> entry integrate --host codex --apply --expect-state active --expect-sha256 <审阅的原件摘要> --expect-new-sha256 <审阅的新摘要>
~~~

只在用户授权、完整预览和摘要都已审阅时应用。规范 managed block 加入后，原用户文字、换行、BOM 和已闭合 frontmatter 保留；旧整份文件另留存。保留字节不是解决规则间语义冲突。已有 Recaloom 块用 status/upgrade，不重复 integrate；块内修改、未知规则、链接、优先 override 或摘要变化都停止。

`written_unverified` 只代表文件写入，`active` 只代表入口状态。用 `doctor --host codex` 检查所有 issues，再在同项目新会话验证实际恢复。写入后 `cleanup_state=incomplete` 要看临时路径，不重复安装。`host_loading_verified=false` 不能改称“已自动加载”。

**Windows** 可预览和手动绑定，安全自动写入、移动和交换后端未提供；不支持时拒绝，不降级为覆盖或删规则。macOS/Linux 也受文件系统原生接口限制；限定 CI 不认证任意机器/共享盘。见[支持矩阵](adapters/support-matrix.md)。

An entry is optional. Preview before any write. Existing user rules require reviewed integration, never replacement; unknown or edited blocks require review. Inspect operation outcomes and verify a fresh host session. Windows uses manual binding: safe automated rule mutations are not provided.

### 入口写好了但助手没读？ / Entry exists but is not loaded?

检查 doctor 的 `storage/usage/host_entry` 与所有问题，不能只看 `ok:true`：

- Codex 的优先 override、完整规则链和指令预算可能影响加载。
- Claude 的 frontmatter 可能限定作用范围；提示只识别存在，不替你解析语义或扩大范围。
- WorkBuddy 5.6.2 的已检查桌面读取器优先根 `CODEBUDDY.md`，其次 `.codebuddy/CODEBUDDY.md`，再其次 `AGENTS.md`，首个可读文件生效。模式、会话和长度限制仍需分别核对，不外推其他版本或 CodeBuddy CLI。

来源、版本和更详细限制见[支持矩阵](adapters/support-matrix.md)。保留全部用户规则，不通过删优先文件、缩短用户内容或扩大条件范围来凑接入成功；手动位置路线始终与宿主自动加载分开。

<a id="pause-and-enable"></a>

### 暂停与启用 / Pause and enable

使用已选 host，先审阅当前 status 和整份文件摘要：

~~~text
<cli> --project <project> entry status --host codex
<cli> --project <project> entry pause --host codex --expect-sha256 <审阅的当前data.sha256>
<cli> --project <project> entry status --host codex
<cli> --project <project> doctor --host codex
~~~

只有明确要求暂停、状态 active 且摘要已核对才执行 pause；已 paused 只核验。独立模板移动到暂停位置，嵌入块只改变插件块，用户正文留在原路径。核对独立模板的 `data.operation.outcome` 或嵌入块的 `data.upgrade.outcome`，再确认 paused；外层 `ok:true` 不够。

以后启用是另一项授权。重新审阅 paused 状态、运行时绑定和**新**摘要，再执行：

~~~text
<cli> --project <project> entry enable --host codex --expect-sha256 <刚审阅的暂停态摘要>
<cli> --project <project> entry status --host codex
~~~

摘要/项目/程序不符先停止，不刷新参数盲重试。暂停不停止任务、不撤销权限，也不会让旧会话忘掉已读内容；需要新会话确认实际行为。

Pause preserves user rules and memory; enable needs a newly reviewed paused-state digest and matching runtime. Neither action revokes loaded context, stops a host or grants permissions.

<a id="upgrade-existing"></a>

## 4. 升级，不重建项目 / Upgrade without resetting the project

1. 停止该项目所有写入者、自动保存和 MCP 写连接；将完整 `.continuity/`（含存在的 journal/WAL/SHM）及引用文件备份到新位置。
2. 在**新的工具环境**安装已核对的 v0.2.0 wheel，保留旧环境。不覆盖旧程序、不把旧数据库备份盖到新进度上。
3. 用新程序对**同一个项目绝对路径**运行 doctor、读取匹配指南并 resume；核对项目 ID、修订和限制。已有项目不再次 init，不自动迁移/修复不兼容存储。
4. 手动/MCP 路线只调整所选连接的可执行路径，保留项目路径与权限模式；由用户控制重新连接。已装项目入口则先审阅下方绑定升级。
5. 验证新会话确实使用新程序后，再决定是否移除旧工具。失败保留原件与错误，回退先核对兼容性，不丢弃新版已保存的进展。

既有 Recaloom 入口使用**新版本**的完整前缀：

~~~text
<新cli> --project <project> entry upgrade --host codex
<新cli> --project <project> entry upgrade --host codex --apply --expect-state <预览的active或paused> --expect-sha256 <审阅的旧摘要> --expect-new-sha256 <审阅的新摘要>
~~~

第一条只预览；第二条才按授权应用。保留当前用户正文和暂停状态，不自动启用。规范完整模板或规范嵌入块才能升级，未知内容不覆盖。运行时摘要变化不是重新生成入口绕过绑定检查的理由。

**原生文件操作结果必须核验：**

| outcome | 意义与动作 |
| --- | --- |
| `move_observed` / `exchange_observed` | 当次观察符合预期；读回实际文件和保留件 |
| `already_in_state` / `already_current` | 已在目标状态，本次无需替换 |
| `moved_needs_review` / `staged_needs_review` / `exchanged_needs_review` / `outcome_unknown` | 保留全部对象，核对实际位置，不重试、删除或自动交换回去 |

交换只在支持的 macOS/Linux 文件系统进行，会先探测交换语义，不可靠则拒绝。检查 `native_result/native_errno`、`retained_role`、`observed_*`、`requested_paths_current`；请求路径不是永久位置保证，残留也不一定是完整旧备份。`probe_state=cleanup_failed` 单独报告探针清理失败。没有覆盖式回退或自动回滚，不承诺摘要检查与交换是 CAS、任意并发安全或断电持久性。共享目录须另核访问策略，0600 不等于完整 ACL 隐私验证。

Stop writers and back up storage plus references; install separately and inspect the same project. Upgrade only the reviewed entry binding, preserving user text and paused state. Check native outcomes and retained-file roles. Uncertain results require review, not another exchange or an old backup copied over new work. Windows mutation restrictions still apply.

<a id="storage-recovery-after-a-crash"></a>

### 异常退出后的存储恢复 / Recovery after a crash

`STORAGE_RECOVERY_REQUIRED` 不是空项目：不要 init、删 journal/WAL 或使用旧缓存冒充恢复。先停止全部读写，完整备份 `.continuity/` 和引用文件，再明确授权：

~~~text
<cli> --project <project> recover-storage
<cli> --project <project> resume --max-chars 10000
~~~

这是 CLI-only 写操作，允许 SQLite 原生恢复并核对现有状态；不初始化、迁移、添加检查点或修复任意损坏。失败保留数据，不循环修复。MCP 只读恢复和自动接续都不会代为执行。

Crash recovery is a separate authorized write after a complete stopped-storage backup. It is not reinitialization, schema migration or arbitrary corruption repair; never delete journals as a workaround.

<a id="optional-hosts"></a>

## 5. 可选 MCP、宿主与团队交接 / Optional integrations

基础 CLI 足够完成首次保存和接续。下面都不是必装项：

- **MCP**：按[本地 stdio 接入](adapters/mcp.md)，在专用环境另装 `mcp==2.2.0`；会联网下载 SDK。服务启动时绑定一个项目，默认只读；仅在所选连接明确获准时启用 `--allow-writes`。工具可见不等于允许付款/发布。
- **Harness**：按[独立受管入口](adapters/harness/managed-host.md)配置；`/recaloom resume`、`pause`、`status` 控制绑定恢复。不是普通 CLI 的前提，也不迁移日常 profile。已验版本和 POSIX/macOS、Windows 未支持边界见矩阵。
- **事件保存**：[授权保存合同](docs/authorized-save.md)与[Claude 事件适配](adapters/claude-code/authorized-save.md)需独立的项目/会话/草稿授权。`prepare` 候选不是已提交检查点；有限宿主试点不等于稳定的所有平台自动保存。
- **第二位助手**：双方获准访问同一项目，A 保存并 handoff，B 检查/accept 后工作；[return-work](docs/result-return.md)登记产物，A 查 receipt 和文件。由你传递指令，工具不唤醒模型。标签不是认证身份，领取不是完成，不保证外部动作恰好一次。
- **导出**：`export --output review.json` 只新建审阅快照，不覆盖。不是数据库导入、原文件备份、跨设备实时同步或权限凭证。

The CLI works alone. Optional MCP, host recovery, event saving and handoffs each require explicit setup and scope. Experimental host behavior is not a universal stable feature. Consult the dated [support matrix](adapters/support-matrix.md) and [verification record](docs/verification.md), not a host name or a successful install.

<a id="preserve-data-removal"></a>

## 6. 安全停用与卸载 / Preserve-data removal

**先处理入口，后卸载工具。** 没接入过规则则只处理自己添加的连接；无需制造一个入口来卸载。保留用户规则、项目 `.continuity/`、草稿与原材料，不删整个 `AGENTS.md`、`CLAUDE.md`、`.claude/`、`.codebuddy/` 或其他规则目录。

### 保留暂停入口，或解除接入 / Pause or detach

要以后继续用，按[暂停流程](#pause-and-enable)在工具仍可用时审阅、pause、status、doctor；不为了卸载而 enable。

要解除项目入口，先查看已安装程序的 `entry --help`，确认有 `detach`，再预览：

~~~text
<cli> --project <project> entry detach --host codex
<cli> --project <project> entry detach --host codex --apply --expect-state <预览的active或paused> --expect-sha256 <审阅的data.sha256>
~~~

只有明确授权、状态/摘要已核对且预览无问题才应用：

- 独立规范模板移到报告中的非发现备份名；`removal.content=null` 不是删除项目。
- 嵌入入口仅移除自己的规范块，**当前用户正文**、BOM、换行及 frontmatter 留在原位；旧完整入口另存保留件，不用安装时备份覆盖后来的用户修改。
- 核对 `data.state=detached`、`data.removal.outcome=move_observed` 或 `exchange_observed`，再读回文件；只看 `ok:true` 不够。
- 未知/修改过的块、摘要或路径变化、平台不支持、needs_review/未知结果均停止并保留全部对象。不手工剪块、删规则或盲重试。
- 解除后的普通规则可能被旧 entry status 报 `ENTRY_UNRECOGNIZED`，不是再次覆盖它的理由。重新接入须重新审阅 setup/integrate，不能直接搬回旧保留件绕过绑定。

Windows 不提供原生安全修改后端，不能通过普通 rename、覆盖或删除来模拟。pause/detach 不删除项目记忆、不卸载包、不关宿主，也不撤回旧会话内容；在新的项目会话确认不再加载 Recaloom，原规则仍有效。

### 最后卸载专用环境里的包 / Uninstall last

核验入口停用后，仅移除你在所选客户端添加的 Recaloom Skill/连接项，保留同文件里的其他配置，关闭对应 MCP 子进程。使用安装时的**准确环境路径**：

~~~sh
.recaloom-xs-0.2.0/bin/python -I -m pip uninstall glom-continuity
~~~

Windows：

~~~powershell
& ".\.recaloom-xs-0.2.0\Scripts\python.exe" -I -m pip uninstall glom-continuity
~~~

若工具目录不同，换成记录的环境 Python 绝对路径。便携版只移走已确认的工具文件，不搬项目或用户规则目录。包卸载不清除记忆/规则；本工具没有安装自启动守护进程。

Before uninstalling, either review and pause a recognized entry or preview and explicitly detach it. Preserve current user rules, memory and retained files; require the reported state and native operation outcome, not merely `ok:true`. Unsupported platforms and uncertain results stop for review—never hand-edit a managed block to force removal. Then remove only your Recaloom connection items and uninstall from the exact dedicated environment. Old conversations retain already-loaded context.

## 隐私、费用与故障 / Privacy, cost and troubleshooting

状态在 `<project>/.continuity/state.sqlite3`；原文件留在原处，数据库不是原材料备份。CLI 不上传项目、不扫描私人聊天、不调用模型；安装下载和可选依赖会联网。云端助手可能把恢复内容发给其模型服务，并按其隐私/收费规则处理。

草稿、规则预览、导出、数据库和恢复内容均可能含私人信息。不要放入密钥、未经允许的公司资料或原始聊天；不要并发同步正在写入的 SQLite。无加密存储、身份认证或抗同系统用户恶意程序的沙箱保证，见 [SECURITY](SECURITY.md)。

| 提示 / Error | 处理 / Action |
| --- | --- |
| `BUDGET_TOO_SMALL` | 增加字符预算，保留限制 / Increase budget without dropping constraints |
| `REVISION_CONFLICT` / `PROJECT_MISMATCH` / `STALE_HANDOFF` | 核对当前项目与进度，不盲重试 / Reconcile identity and revision |
| `needs_review` / `EVIDENCE_CHANGED` | 先复核引用 / Review changed inputs |
| `ALREADY_ACCEPTED` | 查 receipt，不重复外部动作 / Read the receipt |
| `UNSAFE_PATH` / `SENSITIVE_CONTENT` | 修正输入，不绕过 / Correct the input |
| `IO_ERROR` / `UNRECOGNIZED_STORAGE` / `UNSUPPORTED_SCHEMA` / `UNSAFE_STORAGE` | 保留数据并停止写入 / Preserve storage and investigate |
| `STORAGE_RECOVERY_REQUIRED` | 停写备份后单独授权恢复 / Back up before explicit recovery |

Local storage does not mean a connected cloud assistant keeps context on-device. Share only redacted version/system/host, failed step and error code in [trial feedback](https://github.com/fugui6688661/glom-continuity/issues/new?template=field_trial.yml). Do not post raw diagnostics with private paths or contents.

<a id="public-alpha7"></a>

## 历史 Alpha.7 及兼容 / Historical Alpha.7 compatibility

[历史 v0.1.0-alpha.7](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.7) 不是 v0.2.0 的替代安装包。其具名 wheel 为 `glom_continuity-0.1.0a7-py3-none-any.whl`，CLI 显示 `0.1.0-alpha.7`；原附件保持原样，不会因网页更新获得新能力。

Alpha.7 保留项目记忆、resume、doctor、return-work 和显式 recover-storage；公开旧 wheel 没有 XS 的 `usage` 随包指南发现、setup/entry 等新增入口。需从**同一 Release 的匹配具名便携包/固定源码**取得旧 Skill，仍使用原来的可执行程序；不要把现在的 main 文档或另一个包的指南当作旧包匹配说明。

更早 Alpha.5 按原有 status → check/context 路线使用，没有记忆/query、resume、doctor、return-work。已有项目不重复 init；显示名称变为 Recaloom XS 不需要另建数据库。旧同名软件的数据也不能当成本工具项目。

较早本地 XS 候选可能仍显示 Alpha.7 版本名，却包含部分新命令；仅按其准确文件、摘要、帮助和匹配指南识别，不用版本文字推定能力。升级至 v0.2.0 走本页独立环境流程。

Historical assets and behavior remain version-bound. Alpha.7 lacks XS guide discovery and project-entry commands; obtain its matching guide separately and do not guess new options. Alpha.5 uses its legacy workflow. Preserve existing projects and install a new runtime separately.

## 验证范围 / Evidence scope

[支持矩阵](adapters/support-matrix.md)和[验证记录](docs/verification.md)按日期、源码/包摘要、宿主与系统区分证据。稳定 CLI 范围不把受限的原生宿主试点升级成所有平台自动记忆。Windows 限定基础 CI 不等于其所有文件操作和宿主能力通过，Linux CI 也不替代各宿主实机。

本指南不声称外部真人首用已通过、节省多少 token、优于竞品或零错误。文件哈希相符、恢复与交接登记不代表语义正确或业务完成。普通用户无需构建/测试源码；维护者需要复验时应使用对应固定包和分车道测试计划，不把跳过项当作通过。

Installation, protocol checks, host loading and actual task quality are separate observations. No universal human-onboarding, competitive-superiority or error-free claim is made.
