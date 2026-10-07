# 安装与第一次使用 / Installation and first use

需要 Python 3.10+。Recaloom 是本地 CLI 与可选 MCP 连接器；把工具、演示和工作资料分开存放。基础 CLI 没有第三方运行时依赖，不调用模型，也不需要模型账号。

Requires Python 3.10+. Keep the tool, demos and working data separate. The base CLI has no third-party runtime dependencies and makes no model calls.

## 版本与发布状态 / Version and release status

先选一条路线，不要串着执行：

- 从 GitHub 下载公开包：用[公开 Alpha.7 安装](#public-alpha7)。它是开发者预览，不含本页标为 XS 的新命令。
- 已收到维护者明确提供的 XS 候选 zip、wheel 和各自 SHA-256：用[XS 候选安装](#xs-candidate)。这是本地候选，不是已发布的正式 XS。
- 已有项目或安装：先看[升级](#upgrade-existing)，不要重新建库或覆盖环境。

公开 [v0.1.0-alpha.7 Release](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.7)保留项目记忆、`resume`、`doctor`、`return-work`，增加可选的 Harness 只读恢复与显式存储恢复。网页更新不代表该 Release 附件或本机程序已更新。

Choose one route: the [public Alpha.7 preview](#public-alpha7), an explicitly supplied [local XS candidate](#xs-candidate), or an [existing-project upgrade](#upgrade-existing). Do not concatenate these routes. XS commands documented here are not additions to published Alpha.7 assets; neither route is a stable XS release.

**版本文字不能认包。** XS 候选目前也可能显示 `0.1.0-alpha.7`，wheel 名称也可能相同。安装前核对维护者提供的准确文件及整包 SHA-256；安装后用同一环境的 `doctor` 核对程序路径/摘要、`usage` 和帮助中的命令。程序摘要不是 wheel 摘要，两者不能互相比相等。`usage: available` 只证明配套说明通过本地一致性检查，不认证发布者，也不证明宿主接通。

The version string or wheel filename alone cannot identify XS. Verify each supplied asset's own SHA-256, then inspect the installed runtime and bundled guide with that environment's doctor. Wheel and program digests refer to different objects; a local manifest check is not publisher authentication or host acceptance.

已有项目不要重新 `init`；先看本页升级步骤。没有自动更新器，文档更新不会升级已安装程序。本页不提供 PyPI、Homebrew 或应用商店安装入口，不从同名陌生软件安装。

Do not reinitialize existing projects. Documentation changes do not upgrade an installed copy; no automatic updater or PyPI/Homebrew/app-store entry is offered here.

<a id="xs-candidate"></a>

## XS 候选：一个环境走到首次接续 / XS candidate: one runtime throughout

以下是 XS 本地候选的安装接口，未随公开 Alpha.7 发行；各平台验收范围以具名候选记录为准。
仅在取得明确包含成对 `--wheel` / `--sha256` 参数的完整候选后使用，不从旧包猜命令，不需要 Harness。

先核对维护者提供的候选 zip 及其 SHA-256，再进入解压目录。macOS/Linux 可用
`shasum -a 256 文件路径`，Windows 用 `Get-FileHash 文件路径 -Algorithm SHA256`。
下面替换环境路径、可信本地 wheel 的绝对路径和**该 wheel 自己的 64 位十六进制 SHA-256**，
不要填 zip 或程序摘要。环境目标必须尚不存在，父目录须已存在；没有可信文件/摘要就停止。

```sh
python3 -I -B scripts/runtime_env.py create --directory "/absolute/tools/recaloom-xs" --wheel "/absolute/downloads/glom_continuity-0.1.0a7-py3-none-any.whl" --sha256 "<维护者提供的wheel的64位SHA-256>"
```

`--wheel` 与 `--sha256` 可一起省略，但不能只给一个。带二者时，先校验包，hash 不符在建环境前拒绝；
再预检新环境的 Python、SQLite 和 pip，随后离线按精确 hash 安装指定 wheel，不查包索引、不下载依赖，
最后核验**已安装的** `glom_continuity` 的 `doctor` 与 `usage`。只有整条成功才返回 `TOOL_READY`。
它仍为 `host_integrated=false`：不初始化任何项目、不修改任何 host，也不恢复或保存记忆。
哈希一致不认证发布者；本命令不是运行陌生 wheel/Python 的安全沙箱。

成功后保留返回的 **`data.cli_argv` 参数数组**，它是后续 `<cli>` 的完整环境前缀；逐项保留解释器和参数，
再追加具体命令。不要把整串当一个可执行文件名；用 shell 时逐项引用，PowerShell 用 `&` 调用首项。
**直接进入[第一次保存与接续](docs/first-use.md#first-save)**：把 create 结果和选定项目的绝对路径交给有权限的助手，
由它定位配套 Skill、检查项目，经授权才初始化缺失存储、保存六字段草稿并读回。保存后再单独审阅宿主入口。
不要再执行下方公开版的 `venv .recaloom-alpha7`、重复 pip 安装或复制旧适配模板；Harness/MCP 均非必需。

Windows 的命令写法是将 `python3` 换成可用的 `py -3`，并换成本机绝对路径；这不是 Windows 实机验收声明。
POSIX 默认符号链接、Windows 默认副本，无须激活或管理员权限。保留基 Python，不把虚拟环境当可搬运包；
已完成的 Windows/Linux 限定 CI 与尚未提供的宿主能力分列在[支持矩阵](adapters/support-matrix.md)；
命令写法、CI 通过和用户实机全部可用不是同一件事。

This is a local XS candidate interface, not a published update. Platform acceptance requires the named candidate's results.
After verifying the supplied archive, one `create` accepts a trusted absolute local wheel path and its own 64-hex SHA-256
as a pair. It rejects a hash mismatch before creating the environment, preflights the runtime, installs that exact wheel
offline with hash enforcement, and validates the installed module's doctor/usage before returning `TOOL_READY`.
Keep the returned `data.cli_argv` array as the complete prefix for [first save](docs/first-use.md#first-save).
`host_integrated=false`: no project initialization, host changes, recovery or automatic saving occurs. No platform acceptance is implied.

### 诊断／兼容：旧分步 create 与 check / Diagnostic or compatibility route

只准备环境或使用没有成对参数的旧候选时，仍可采用原来的分步入口；它不是上述成功后的追加步骤：

```sh
python3 -I -B scripts/runtime_env.py create --directory "/absolute/tools/recaloom-xs"
python3 -I -B scripts/runtime_env.py check --directory "/absolute/tools/recaloom-xs"
```

不带 wheel 的 `create` 成功仍为 `RUNTIME_READY`，不表示 Recaloom 已安装；`check` 只诊断，不安装或修复。
旧候选的手动 wheel 安装继续按其配套说明，使用返回的 `python_executable`，再核对已装工具的 doctor/usage；
不能对刚创建的路径再运行带 wheel 的 `create`。新旧路线都拒绝一切已有环境目标（包括空目录、文件或链接）。

失败或超时不重试；如本次已建环境则保留，包括部分安装。检查 `phase`、`exit_code`、`next_step`，
不要删除项目、覆盖环境或设置 DYLD 环境变量掩盖错误。部分托管 macOS Python 的副本无法找到 libpython，
`--copies` 会明确报告启动失败，不静默切换模式。可用仍工作的可信基 Python 运行 `check` 诊断旧环境；
检查不是陌生可执行文件的安全沙箱，详细原始子进程输出不回显。

在 POSIX 上，探针/ensurepip 的超时清理只针对本次仍持有身份的进程组，不按进程名或磁盘里的 PID 清理。
请查看失败结果的 `child_cleanup`：直接进程退出不等于所有后代结束。主动脱离该组的程序、Windows 整棵
进程树及主进程已被回收的情况，均不声明清理已确认。原目录保留，不自动修复或再次安装。
安装后的同一入口是 `glom-continuity-env`（Windows 为 `.exe`）；环境不能启动时，用基 Python 与候选脚本诊断。

Without the pair, successful `create` remains `RUNTIME_READY`, not tool readiness. Retain the old `create`/`check` route
for diagnostics or compatibility, not as extra onboarding steps. `check` runs the selected trusted interpreter without
repairing it. Every existing destination is refused; never rerun wheel-enabled `create` into an environment just created.
Failures retain any newly created environment and partial installation, without retry or silent fallback.
POSIX cleanup covers only the owned process group while its leader remains unreaped; inspect `child_cleanup`.
Detached descendants, Windows process trees and an already-reaped leader are not certified as cleaned up.

<a id="public-alpha7"></a>

## 公开 Alpha.7：专用环境中的 wheel / Public Alpha.7 wheel

**仅供选择公开 Alpha.7 的用户。已按上节装好 XS 就跳过本节。**

先在工具存放位置新建专用虚拟环境。`.recaloom-alpha7` 必须尚不存在；已有此目录时先检查它，不覆盖、不删除。不要在系统 Python 中安装，不需要管理员权限或修改全局 PATH。

Create a new dedicated environment in your tools directory. If that path already exists, inspect it instead of replacing it. Do not install into system Python; no administrator access or global PATH changes are needed.

Mac / Linux：

```sh
python3 -m venv .recaloom-alpha7
```

确认对应 Release 已提供下列具名 wheel 后，使用这一条安装命令。附件不可用时先核对发布页和版本，不换成旧包来完成新版教程。已下载同一公开文件的用户可用下一节本地安装；拿到 XS 候选的用户返回上方 XS 路线。

Use this command after confirming the matching named wheel is available on its Release page. If it is unavailable, check that page and version instead of substituting an older package. A downloaded copy of that public asset can use the local route below; XS candidates use the separate route above.

```sh
.recaloom-alpha7/bin/python -m pip install --no-index --no-deps "https://github.com/fugui6688661/glom-continuity/releases/download/v0.1.0-alpha.7/glom_continuity-0.1.0a7-py3-none-any.whl"
```

此命令会联网下载指定 wheel，不查包索引、不安装其他依赖、不调用模型。

This downloads the specified wheel over the network, without an index lookup, other dependencies or model calls.

Windows PowerShell 先建环境：

```powershell
py -3 -m venv .recaloom-alpha7
```

然后将上方 pip 命令开头的 `.recaloom-alpha7/bin/python` 换成 `.\.recaloom-alpha7\Scripts\python.exe`，保留同一 URL 和参数。无需激活脚本或修改 PowerShell 执行策略。

Then use the same pip command with `.\.recaloom-alpha7\Scripts\python.exe` as its executable. No activation script or PowerShell-policy change is required.

### 已下载的 Alpha.7 文件 / Downloaded Alpha.7 files

本地方式和上方直链方式二选一。此处是公开 Alpha.7，不是 XS；XS 使用上方已选环境的流程。先核对 Alpha.7 文件和配套 SHA-256 清单，不套用其他版本的哈希。在已新建的专用环境安装：

For public Alpha.7, choose either this downloaded-file route or its Release URL. XS users keep their already-selected runtime above. Verify the matching checksums:

```sh
.recaloom-alpha7/bin/python -m pip install --no-index --no-deps ./glom_continuity-0.1.0a7-py3-none-any.whl
```

本地 wheel 安装不联网。Windows 同样替换为环境内 Python，并使用收到的文件路径。公开附件的 `SHA256SUMS` 可用 `shasum -a 256 -c SHA256SUMS` 校验，需备齐清单中所列文件；Windows 用 `Get-FileHash 文件名 -Algorithm SHA256` 逐项比较。哈希校验不是发布者签名认证。

A local wheel install is offline. On Windows use the environment Python and the supplied file path. Verify all listed assets with SHA256SUMS, or compare individual Get-FileHash results. Integrity hashes do not authenticate the publisher.

### 检查安装并跑合成演示 / Check the installation and demo

Mac / Linux：

```sh
.recaloom-alpha7/bin/glom-continuity --version
.recaloom-alpha7/bin/glom-continuity --help
.recaloom-alpha7/bin/glom-continuity-demo --output ./installed-demo
```

Windows：

```powershell
.\.recaloom-alpha7\Scripts\glom-continuity.exe --version
.\.recaloom-alpha7\Scripts\glom-continuity.exe --help
.\.recaloom-alpha7\Scripts\glom-continuity-demo.exe --output .\installed-demo
```

alpha.7 的 CLI 版本应为 `0.1.0-alpha.7`，wheel 文件名使用 Python 版本形式 `0.1.0a7`。帮助应列有 `resume`、`doctor`、`return-work`；不符时先查调用路径，不在旧包上猜命令。

Expect CLI version `0.1.0-alpha.7`; the wheel uses Python's `0.1.0a7` spelling. Confirm resume, doctor, return-work and recover-storage in help. A mismatch needs a path/version check, not guessed commands. Recovery is an explicit write operation, not a routine installation step.

`installed-demo` 必须是新目录。打开其中的 `演示结果.md`，核对恢复、文件变化拒绝和重复领取拒绝；`events.json` 保留响应，`handoff-review.json` 是审阅快照。这是合成 CLI 协议回放，不是两个模型在工作，也不单独证明所有恢复或记忆功能通过验收。

Use a new demo directory; existing data is not overwritten. The generated report, events and review snapshot show synthetic protocol behavior, not a live-model trial or complete feature acceptance.

## 给助手正确的位置 / Bind the assistant

**XS 本地候选的简化入口**（公开 Alpha.7 尚无此命令）：

```text
<cli> --project <项目绝对路径> setup
```

它把当前程序、配套 Skill、项目 ID 和恢复命令整理成一张 JSON 接手卡。已有项目返回 `ready_for_manual_binding` 时，可以把整张卡交给有本地文件／命令权限的助手；助手先核对 `doctor_argv` 返回的程序哈希、项目 ID 与说明状态，再运行 `resume_argv`。命令是参数数组，不要直接拼成 shell 字符串。卡片包含本机路径，别贴到公开反馈中。

空目录返回 `requires_initialization`，不会悄悄建库；坏库或缺失／错配说明会拒绝生成可用卡。更换了项目后，旧卡的恢复命令会因项目 ID 不符而拒绝。该入口不安装或配置任何 Agent、不上传资料、不开自动保存，也不赋予助手权限；第一次保存仍按下文明确执行。它只是把原先需人工整理的三个位置和项目身份合成一个入口。

XS candidates offer read-only `setup` to prepare a JSON binding card from the actual executable, matching guide and selected project identity. Pass the card only to an authorized local-command assistant; verify its doctor result before executing the returned argument array. Missing storage requires explicit first-save initialization, while incompatible storage or guides refuse binding. This does not install a host integration, grant permissions or enable automatic memory. Public Alpha.7 assets do not contain this command.

### 先看哪里没接上 / Diagnose the selected entry

带此选项的 XS 本地候选可把程序、配套说明、记忆库与项目规则放在一次诊断中：

```text
<cli> --project <项目绝对路径> doctor --host codex
```

`--host` 也支持 `claude-code` 和 `workbuddy`。查看 `storage`、`usage` 与 `host_entry`：未接入、暂停、规则陌生或不安全、项目或程序不匹配、优先规则遮蔽会给出相应线索与下一步。`ok:true` 只表示诊断运行完成，不表示可以恢复；`active` 只表示规则位于活动路径。诊断不启动助手、不调用模型、不建库、不修复或改写规则，`host_loading_verified` 始终为 false。条件规则仍需在真实新会话中核对触发，不能靠文件存在证明加载。不要把包含本机路径的原始输出直接公开。

Where listed in CLI help, `doctor --host codex|claude-code|workbuddy` adds read-only project-entry inspection to runtime, guide and storage diagnosis. `ok:true` means the inspection completed, not that recovery is safe or the host loaded a rule. Follow reported issues before considering the next step; this command does not launch a host, modify rules or initialize storage. Without `--host`, the existing diagnosis remains unchanged. This is a local XS candidate feature, not an update to published Alpha.7 assets or a new MCP parameter.

Codex 的规则合并预览、`entry status` 和 `doctor --host codex` 会在完整文件超过官方默认 32 KiB 合并指令预算时提示 `ENTRY_DEFAULT_BUDGET_EXCEEDED`。这是按 UTF-8 字节计算的风险提醒，不代表已观测到截断；当前配置、其他层级规则及实际加载仍未知。请保留原规则，检查完整指令链和实际预算，再验证新会话；没有提示也不证明能加载。插件不读取或修改全局配置，不自动缩短用户规则。[Codex 官方加载规则](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

For Codex, integration previews and installed-entry inspection warn when the complete document exceeds the documented default 32 KiB combined instruction budget. This measures UTF-8 bytes, not tokens or characters. The effective limit and other instruction files are not inspected; the notice does not prove truncation, and its absence does not prove loading. Preserve user rules and verify the actual instruction chain in a fresh session. This Codex-specific warning does not apply another host's limits.

**XS 项目入口候选**还可以预览一份给特定助手读取的项目规则：

```text
<cli> --project <项目绝对路径> setup --host codex
<cli> --project <项目绝对路径> setup --host codex --write-instructions
```

第一行只预览；第二行才明确新建文件。`codex` 对应项目 `AGENTS.md`，`claude-code` 对应 `.claude/rules/recaloom.md`，`workbuddy` 对应代码开发项目 `.codebuddy/CODEBUDDY.md`。不修改全局设置，也不要求安装 Harness。已有目标或 Codex 的 `AGENTS.override.md` 会拒绝，不能通过删除旧规则来凑成功；需要人工审查整合。父目录是链接或普通文件时同样拒绝。无项目记忆、配套说明不可用或响应预算不足时不写入。

这份入口只记录程序、说明和项目身份，不复制业务正文、聊天或密钥。新建成功返回 `written_unverified`，**不是已被助手加载**：请在同一项目新开会话，核对它是否真实读取并恢复；不同版本、规则排除和上下文限制都会影响结果。入口本身不开自动保存；XS 另有[授权候选保存接口](docs/authorized-save.md)及需单独配置的[Claude 事件适配](adapters/claude-code/authorized-save.md)。预览可跨平台使用；安全自动写入目前仅开放支持目录句柄和禁止跟随链接的 POSIX 运行时，Windows 返回 `ENTRY_WRITE_UNSUPPORTED`。Windows 基础安装的限定 CI 不补足这一缺口。

XS project-entry candidates add `--host codex|claude-code|workbuddy`; only `--write-instructions` creates a new project rule. Existing rules and priority overrides are refused, never merged or replaced automatically. Binding metadata includes private local paths: review before sharing or committing the generated file. A full temporary file is published without overwriting; an interrupted write may leave an inert `.pending` file or empty parent directories, not a partially published rule. This is not a sandbox against another process with the same user's filesystem rights. Verify actual host loading separately. On upgrade, a changed runtime hash must stop recovery until the selected binding is deliberately reviewed. Before uninstalling, follow [preserve-data removal](#preserve-data-removal): inspect and pause the recognized entry while the tool is still available. An integrated managed block shares a file with user rules; do not delete that file or hand-edit the block. Uninstalling the Python package does not remove project rules or memory.

写入结果与临时文件清理分开报告：`written_unverified` 配 `cleanup_state: incomplete` 表示完整规则已经写入，但清理失败；查看 `temporary_path`，不要重复安装或覆盖规则。发布前失败仍返回原始错误，并说明是否还有临时文件待检查。响应预算先覆盖较长的清理失败结果，不能写完后才发现结果装不下。

<a id="pause-and-enable"></a>

### 暂停与重新启用 / Pause and enable

带 `entry` 命令的 XS 本地候选提供以下入口；公开 Alpha.7 未更新：

```text
<cli> --project <项目绝对路径> entry status --host codex
<cli> --project <项目绝对路径> entry pause --host codex --expect-sha256 <刚审阅的data.sha256>
<cli> --project <项目绝对路径> entry status --host codex
```

`--host` 同样支持 `claude-code` 和 `workbuddy`。先读 status 并审阅结果，只有明确要暂停且入口为 `active` 时才执行 pause，再只读检查。`active`、`paused`、`not_installed` 描述入口状态；`data.layout=embedded` 时是插件块状态，不是整份用户文件的位置，不证明 Agent 实际加载。`runtime_binding_matches` 单列当前程序与规则绑定是否匹配；不读取或执行规则里任意路径指向的程序。

重新启用不是卸载步骤。需要恢复时，先重新执行 `entry status --host codex`（沿用上面的完整前缀和项目参数），审阅当前 `paused` 状态、绑定及 `data.sha256`，再明确执行：

```text
<cli> --project <项目绝对路径> entry enable --host codex --expect-sha256 <刚审阅的暂停态data.sha256>
<cli> --project <项目绝对路径> entry status --host codex
```

嵌入布局暂停后整份文件的摘要会变化，不能沿用暂停前摘要。遇到摘要变化先审阅差异，不自动重取摘要重试；启用要求 `runtime_binding_matches: true`，不通过改模板绕过绑定检查。

对于 setup 新建的独立完整模板，pause 将其移到同目录的 `.recaloom-<host>.paused`，enable 移回原路径；不删记忆、不改全局配置。需要未被编辑的规范模板、正确项目和准确的 `--expect-sha256`。两位置都存在、链接、模板内修改、优先 override 或摘要变化均停止；不要自动重新取摘要凑通过。旧运行时失效仍可暂停，但不能自动启用或重新绑定。对于下方 integrate 生成的嵌入块，不移动整份文件，暂停/启用只替换插件块，用户规则仍在原位。已有暂停文件时 setup 不另建一套活动入口。

移动使用 macOS `renameatx_np(RENAME_EXCL)` 或 Linux `renameat2(RENAME_NOREPLACE)`；符号/目录句柄接口不支持就明确拒绝，不回退到覆盖式移动。Windows 移动后端尚未实现；Linux CI 的限定运行见[平台记录](docs/platform-validation.md#xs-ci-20261007)，不认证所有文件系统。无跨文件系统复制、删除或自动回滚；在有并发编辑、远程文件系统或系统错误时，操作可能需要人工复核。

独立模板的移动必须看 `data.operation.outcome`，不能仅看外层 `ok:true`；嵌入块替换则看下方说明的 `data.upgrade.outcome`：

- `move_observed`：原生移动成功，后续检查观察到预期字节和文件位置；不是“校验加移动”的原子事务，也不保证后续没有其他修改。
- `already_in_state`：已在目标位置，本次没有移动。
- `moved_needs_review`：移动成功但后检查不匹配或无法读回；保留文件，不得当作暂停/启用成功。`source_path`、`target_path` 只是请求时的名称，不能单凭它们认定文件仍在那里。
- `outcome_unknown`：系统错误或操作后状态不确定；先只读检查，不能自动重试、删除或覆盖。`native_result` 与 `native_errno` 单列原生调用观察。

`requested_paths_current: false` 表示观察到父目录绑定变化；`null` 表示无法确认。此时 `observed_target_path` 不提供一个猜测位置，保留文件的当前位置记为未知，需要核对目录移动/改名。后续 status 只检查请求路径，返回 `not_installed` 不能证明旧文件被删除，也不授权重新安装。`observed_target_path` 有值时也仅表示当次检查观察到的位置，不是永久定位保证。规则存在硬链接副本时，status和重复操作同样拒绝，不只在真正移动时才检查。

暂停对独立模板移走入口，对嵌入布局只停用原位的插件块，**不会撤回已进入旧会话的上下文，也不会停止正在执行的任务**。需在各宿主新会话验证实际行为；不能把它作为运行中权限撤销机制。

These candidate-only CLI operations relocate a recognized standalone template, or replace only the managed block in an embedded rule while preserving user text at its original path. Review the current whole-file digest before each change; an embedded pause changes it, so enabling requires a fresh reviewed status digest. They do not delete project memory, stop a host, authenticate ownership, or revoke loaded context. Inspect `data.operation.outcome` for standalone moves or `data.upgrade.outcome` for embedded changes even when the outer envelope is successful; review-required or unknown outcomes require reconciliation, not automatic retries. A changed binding is not silently upgraded. Native platform availability and actual host loading are separate acceptance gates.

### 审阅后升级项目入口 / Reviewed binding upgrade

以下属于 XS 本地候选，尚未更新公开 Alpha.7。它更新项目规则所指的程序、说明和项目绑定，不下载软件、不安装宿主、不迁移数据库，也不会启用原本暂停的规则。

```text
<新版本cli> --project <项目绝对路径> entry upgrade --host codex
<新版本cli> --project <项目绝对路径> entry upgrade --host codex --apply --expect-state <预览的active或paused> --expect-sha256 <预览的旧摘要> --expect-new-sha256 <预览的新摘要>
```

第一行只预览完整新内容与绑定。核对项目、程序来源和两份摘要，再明确应用；三宿主入口均沿用 `--host`。不要自动刷新摘要、换位置或循环重试。旧版本程序已卸载不妨碍识别旧规则；新版本配套说明必须可用。只接受工具生成的规范完整模板或下方 integrate 的规范嵌入块，不覆盖未知自写文件。嵌入块外的用户改动可以保留并重新审阅；块内改动、活动与暂停并存、链接、优先override、错误项目或预览后新旧内容/位置状态变化都停止。

应用在同一目录排他创建随机 `.recaloom-<host>.upgrade-<id>`，请求0600模式，完整写入并刷文件后才调用一次 macOS `RENAME_SWAP` / Linux `RENAME_EXCHANGE`。正常观察结果是规则位置获得新文件、保留位置获得旧文件；两份都保留，没有自动unlink/回滚/覆盖式回退。原来paused仍paused，重复应用相同绑定返回 `already_current`。Windows尚无此原生后端；Linux限定CI与宿主实接分开记录，平台或文件系统不支持就拒绝，不用普通rename代替。

查看 `data.upgrade`，不只看外层 `ok`：`exchange_observed` 表示当次双向身份/字节及父目录检查一致；`staged_needs_review` 表示已创建升级件但尚不能完成交换；`exchanged_needs_review` 表示系统交换成功、后续检查不全；`outcome_unknown` 则不能推断是否已交换。`stage`、`native_result/native_errno`、`error_code/io_errno` 分别描述阶段、系统交换和其他I/O。`retained_role`可能是previous、candidate、partial_or_unknown或unknown，**不能把任意残留都叫“旧规则备份”**。

XS 在交换真实规则前，用同一文件系统上的私有临时目录检查双向交换语义。有些共享目录会返回成功，却只移动一个文件；此时 `ENTRY_EXCHANGE_UNRELIABLE` 会阻止真实规则交换，原规则不动，候选和探针保留待查。`probe_phase` 区分准备、交换、观察、清理；`probe_errno` 保留空间或权限等系统原因，`probe_state: cleanup_failed` 不等于交换语义已失败。正常探针立即清理自身两个临时文件和空目录；失败查看 `probe_retained_path`，不要盲目重试。这个检查只是一时观察，不替代真实交换后的验证，也不证明任意共享盘、崩溃或同用户恶意竞争都安全。

`rule_path`与`retained_path`为请求时的名称，`observed_*`只在成功检查后给出；父目录漂移或无权确认时，位置明确未知。失败后保留所有文件，先核对实际位置和内容，再作新的恢复决定；不要盲目再次交换，否则可能把新旧换回或交换别人的新文件。非Markdown扩展名不是所有宿主绝不读取它的保证。现有会话不会因此自动重载，真实宿主读取仍须分别验证。

此流程面向可信、无外部并发编辑或配合串行化的项目目录，不是对同用户恶意进程的沙箱，也不是校验摘要与交换的CAS。竞态可能交换当时名字对应的其他对象，只能保留、检测并报告已观察到的情况；不承诺永久保留或断电安全。旧对象的原权限/ACL随对象保留，新的规则采用新建对象的权限；请求0600不等于完整ACL隐私验证，也不会复制旧ACL或静默修改它。用于共享权限目录前需单独核对访问策略。

The new runtime previews canonical replacement bytes; apply requires the reviewed location state and both digests. A single native exchange retains both named objects without automatic cleanup or rollback. This is an observed local-file upgrade, not digest CAS, crash-durability certification, host auto-loading, a private-backup guarantee, or automatic merging of user instructions. Read the retained-file role and actual observation fields before any recovery action.

### 已有个人规则：审阅后加入 / Integrate existing project instructions

XS 本地候选功能，公开 Alpha.7 尚无此命令。用于上述三个固定入口已经存在、并且含有用户自己的说明的情况；不扫描或修改其他规则文件。

```text
<cli> --project <项目绝对路径> entry integrate --host codex
<cli> --project <项目绝对路径> entry integrate --host codex --apply --expect-state active --expect-sha256 <原件摘要> --expect-new-sha256 <预览的新摘要>
```

先审阅完整提议再应用。原有 UTF-8 文字、换行、BOM 和已闭合 YAML frontmatter 保持原字节，插件放在 frontmatter 之后、正文之前的独立版本块中。`user_content_sha256` 可用于复核保留的用户部分，不能证明规则之间没有语义冲突。frontmatter 原有的路径条件仍有效；这不是让条件规则变成全局规则。输入及完整合成文件上限64KiB，不代表符合各宿主的指令预算。

Claude Code 的这个入口若含 frontmatter，候选版会在接入预览和 `entry status` 等结果中给出 `loading_notice`（`ENTRY_FRONTMATTER_SCOPE_UNVERIFIED`）。它只表示这次读取看到了 frontmatter，不解析 YAML 含义：哪怕只有描述或空块也会提醒，并不据此判定规则有路径限制。请检查原条件，并在正确项目的新会话确认实际加载；不自动删条件、扩大适用范围。没有此提示也不代表已加载，`host_loading_verified` 仍为 false。Codex、WorkBuddy 不套用这条 Claude 特定提示。

For Claude Code only, preserved frontmatter yields a `loading_notice` in integration previews and recognized entry inspection/lifecycle results. It does not infer YAML semantics or prove conditional loading. Review the original scope and check a fresh host session. No notice is not proof of loading; no scope is silently broadened.

应用复用上方原生交换过程，原文件保留在报告指定的位置；同样受权限、并发、平台和失败恢复边界约束。错误编码、控制字符、未闭合 frontmatter、重复/被改插件块、暂停旁文件、优先 override 或新旧摘要不符时拒绝。已有插件块不再次 integrate，使用 status/upgrade。预览含用户规则和本机路径，不要贴到公开反馈或不受信任的模型。

嵌入布局的 `entry pause/enable` 需要审阅整份当前文件的摘要，只改变插件块。暂停块保留绑定数据但不包含自动恢复指令，个人规则不会被移出原路径；`entry upgrade` 同样保留用户部分和暂停状态。结果写在 `data.upgrade`，出现 needs_review 时先处理原件和保留件，不循环重试。`status.layout=embedded` 下的 paused 指插件块，不表示整个用户文件搬进 paused_path。

暂停只是宿主指令层状态，不是硬权限屏障；已经读入的会话不被撤销，宿主也可能忽略、截断或被别的规则覆盖。文件操作通过不等于真实新会话自动恢复通过，更不等于已启用自动保存。

插入后，块前新增的空行、普通段落或标题也可保留，升级不擅自移动插件块。若前缀含围栏、HTML、缩进、列表或其他这里未支持的位置语法，则拒绝自动操作，请先审阅位置；本工具不是通用Markdown可见性解析器。只把独立行上的分隔符识别为结构，不把JSON绑定中的路径文字算成插件块。写入失败时 `proposed_layout` 只表示提议，实际 `layout` 可为unknown；它与needs_review一起使用，不把未交换的文件说成已接入。

Candidate-only integration preserves user bytes and closed frontmatter, places one canonical managed block before the body, and retains the original object through the reviewed exchange. Embedded pause/enable and upgrade replace only that block; outside edits require fresh review, inside edits are refused. Preservation is not semantic conflict resolution, host loading, or permission revocation. Never publish previews containing private instructions or local paths.

### WorkBuddy 桌面：已接入但没读到？

本机 WorkBuddy 5.6.2 安装代码的项目指导读取顺序是当前会话工作目录的 `CODEBUDDY.md` → `.codebuddy/CODEBUDDY.md` → `AGENTS.md`，取首个能读取的文件，不合并；空的根 `CODEBUDDY.md` 也会挡住第二个位置。这不是 CodeBuddy CLI 的规则，不外推其他版本。

XS 候选因此检查根优先路径：setup、integrate、暂停/启用和升级遇到它时返回 `ENTRY_SHADOWED`，不删改、移动或自动接管它。即使它是目录、链接或不可读，也先保留并要求审阅，不跟随去读内容、不猜它实际会不会被宿主采用。已接入项目的 `entry status --host workbuddy` 仍报告插件文件的 active/paused 状态，同时在 `priority_issue` 给出冲突原因；active 从来不等于宿主已加载。预检与写入前后观察不是并发CAS，也不保证其他进程之后不会创建优先文件。

接续测试必须用正确项目目录的新会话：安装代码中 Ask/Quick 不经过这条项目指导注入，已有对话可能不重读，正文还有8000个JavaScript字符串单元的截断限制。优先路径检查和下方长度提示不会自动切模式、改预算，也不证明这些边界下的完整模型恢复；路径/模式/长度和实际加载仍要分别核实。不要为了“装上了”覆盖自己的规则。

XS 的合并预览、`entry status` 和 `doctor --host workbuddy` 现在还会检查完整文件长度。超过已核 WorkBuddy 5.6.2 桌面读取器的 8000 UTF-16 单元时，返回 `ENTRY_HOST_BUDGET_EXCEEDED`；汉字通常占1单元，部分表情等非BMP字符占2单元，不按UTF-8字节或token估算。默认输出预算装不下完整预览时，拒绝消息仍保留这条风险和增加 `--max-chars` 的下一步，不回显规则原文。用户规则不会被自动截短；需要你审阅如何调整，以及在正确模式的新会话核实实际加载。该观察仅绑定上述版本，当前宿主、模式和会话没有被本命令探测；没有提示也不证明已接通。暂停状态下的体积提示只描述保留文件，不代表它正在被读取。

For WorkBuddy, XS integration previews and recognized-entry inspection warn when the complete document exceeds the 8000 UTF-16 code-unit limit observed in the 5.6.2 desktop reader. Non-BMP characters count twice; UTF-8 bytes and tokens are different units. A too-small preview response retains an actionable, content-free warning. No user guidance is shortened, no host mode/configuration is changed, and the current host/version/session is not probed. This version-bound observation and any paused-file notice do not certify actual loading.

For the inspected WorkBuddy desktop 5.6.2, root `CODEBUDDY.md` may shadow `.codebuddy/CODEBUDDY.md`, even when empty. The candidate refuses automatic lifecycle changes in the presence of that priority path and reports it in `entry status`; it does not overwrite either file. This is a current-directory path check, not CLI equivalence, whole-host configuration discovery, a race-free transaction, or proof of model-side restoration.

首次使用需要三项具体信息，按[首次使用卡](docs/first-use.md)填写：

1. 所选项目的绝对路径。
2. 匹配版本的 `skills/project-continuity/SKILL.md` 的绝对路径。
3. 可执行命令前缀，包括解释器及所需参数，而不只是“工具目录”。

Supply the absolute project path, the matching Skill's absolute path, and the complete executable prefix.

**XS 本地候选**的 wheel 随包带 Skill 和说明。先用已选命令前缀运行 `<cli> --project <absolute-project> doctor`：`data.usage.state` 为 `available` 时，直接使用其中的 `skill_path`，无需再下载第二份文档。`unavailable` 时看 `issues`，保留当前环境及项目，不自动换用别处的 Skill。`source_unsealed` 只表示找到当前源码目录的说明，doctor 未核对该源码包清单。检查不读取聊天、不初始化项目，也不会替你配置宿主。

XS candidate wheels bundle their guide. Run the selected executable's doctor and use `data.usage.skill_path` only when the reported state is appropriate: `available` means guide/core manifest checks matched; `source_unsealed` is only a source-layout location, not a package check. `unavailable` requires reviewing the issue, not borrowing another install's documentation. No host configuration or project initialization occurs.

**公开 Alpha.7 旧包没有这项更新**，doctor 没有 `usage` 字段。旧包用户仍从同一 Release 的具名便携附件或明确匹配的固定源码取得文档，保留相对目录，不切换已选的可执行程序。版本名、同名 Skill 或会变化的 main 分支均不足以证明字节匹配。新检查是本地清单一致性检查，不是签名认证；修改清单的人也可以修改其中的哈希。

Existing public Alpha.7 assets are unchanged and do not return `usage`. For those packages obtain the matching named portable asset or explicitly matched source documentation separately. Matching local hashes is not publisher authentication. Editable installs and zip-based Python loaders are not validated by this guide path; use a normal wheel installation for the bundled route.

选择一种命令前缀 / Choose one executable prefix:

- Wheel：`/absolute/tool-env/bin/glom-continuity`，或 `/absolute/tool-env/bin/python -B -m glom_continuity`。
- Windows wheel：环境内 `Scripts/glom-continuity.exe` 或 `Scripts/python.exe -B -m glom_continuity` 的绝对路径。
- 便携或源码：`python3 -B /absolute/tool/scripts/continuity.py`；Windows 用 `py -3 -B ...`。

下文的 `<cli>` 代表整个前缀，必须替换后使用；路径含空格时分别引用。wheel 用户即使另外解压了文档，仍使用已选环境内的可执行文件，不因 Skill 位置切换到另一份程序，也不猜全局命令。

Below, replace `<cli>` with that entire prefix and quote paths safely. Wheel users keep the environment executable even when documentation lives elsewhere. Do not switch runtimes based on the Skill's location.

Skill 不赋予命令或文件权限，包内插件元数据和项目模板也不等于已安装到宿主。无需全局钩子、聊天导入或整机权限；自动新会话加载须另行验证。

A Skill grants no execution/file permissions. Plugin metadata and templates do not install themselves into a host. No global hook or chat import is required; automatic new-session loading is not guaranteed.

## 保存与恢复 / Save and recover

先检查选定版本的帮助，再只读查看项目。确认有 `doctor` 和 `resume` 时：

```text
<cli> --project <absolute-project> doctor
<cli> --project <absolute-project> resume --max-chars 10000
```

`doctor` 返回实际调用版本、程序路径/哈希和存储状态；`ok:true` 仅表示诊断执行完，仍须检查 `storage.compatible`。这是程序自报与格式识别，不是发布者认证。公开反馈前遮去私人路径。陌生、损坏或不兼容存储不能当作新项目重建，见[诊断说明](docs/result-return.md)。

Doctor identifies the invoked runtime and recognized storage. Successful diagnosis can still report incompatible storage; preserve it rather than reinitializing. Redact private paths before sharing reports.

`resume` 不初始化、不保存、不领取交接。状态分为 `not_initialized`、`no_checkpoint`、`needs_review`、`no_references`、`restored`：没有存储、没有节点、需复核引用、仅恢复无引用规划、已读回记录。恢复记录不是完成认证，未知状态或坏库存储应停止并报告。

Resume is read-only. Its states distinguish missing storage, no checkpoint, required review, unreferenced planning and recovered records. None certifies task completion; unknown states and corrupt storage require review.

<a id="storage-recovery-after-a-crash"></a>

### 异常退出后需要恢复存储 / Storage recovery after a crash

Alpha.7严格区分只读恢复和数据库修复。`STORAGE_RECOVERY_REQUIRED`
表示当前只读连接无法继续，不能把它当成空项目重新 `init`，也不能删除日志文件。
SQLite 在异常写入后可能需要先回滚尚未提交的事务；这一步本身需要写权限。
自动恢复和 MCP 只读工具不会代你执行，也不会返回旧缓存冒充已恢复。

先停止该项目的所有读写进程，把整个 `.continuity/`（包括存在的 `-journal`、
`-wal`、`-shm`）和引用文件一起保存在新备份位置。不要拷贝后只保留数据库主文件。
核对准确的项目路径，再明确执行：

```text
<cli> --project <absolute-project> recover-storage
<cli> --project <absolute-project> resume --max-chars 10000
```

`recover-storage` 是独立 CLI 写操作：允许 SQLite 原生恢复，随后核对现有结构和
检查点。它不新建项目、不迁移 schema、不添加检查点、不修复任意损坏，也不代表
业务完成。成功结果只返回实际可读的项目状态；若原本正常，不声称发生过回滚。
失败则保留备份与原件继续排查；不要循环修复、重建或删库。MCP 不提供这个命令。

In Alpha.7, `STORAGE_RECOVERY_REQUIRED` preserves the strictly
read-only boundary. After stopping all users and backing up the whole storage
directory and referenced files to a new location, explicitly authorize the
CLI-only `recover-storage` for the exact project. It permits native SQLite
recovery and validates existing storage, without initialization, migration or a
new checkpoint. It is not arbitrary corruption repair or a completion verdict.
Never remove a hot journal as a workaround. See [SQLite crash recovery](https://sqlite.org/lockingv3.html).

首次保存只有在确实未初始化且获准时，才运行 `<cli> --project <absolute-project> init --name "My project"`。已有项目不要再次 init。初始化不会保存目标；在项目内另写六字段 `checkpoint.json`：

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

先读 `status.data.revision`，再用实际修订号保存，不把 0 当通用常量：

```text
<cli> --project <absolute-project> status
<cli> --project <absolute-project> checkpoint --from-file <absolute-project>/checkpoint.json --expect-revision <revision>
<cli> --project <absolute-project> resume --max-chars 10000
```

XS 候选若在 `checkpoint --help` 列出 `--expect-project-id`，保存时追加此前已审阅绑定的项目 ID。版本号相同的两个项目仍然是不同项目；`PROJECT_MISMATCH` 应停止并核对位置，不自动换 ID 重试。旧发行件没有该参数，保留手动路径核对，不能宣称有此保护。

If checkpoint help advertises `--expect-project-id`, add the previously reviewed project ID to the save. Equal revisions do not identify the same project. Stop on `PROJECT_MISMATCH`; do not silently adopt the replacement ID. Older releases without the option require their documented manual scope checks.

Initialize only an authorized first save into genuinely absent storage. Write the reviewed six-field draft inside the project, read the actual revision, save and read back. An existing initialized project needs no further init.

这是无引用规划，`no_references` 不代表验过成品。真实输入用 `{"path":"input.csv","role":"input"}`，输出用 `artifact`；文件必须存在、路径相对项目，指纹由工具计算。习惯与流程的 `memory` 格式见[项目记忆](docs/project-memory.md)。重要限制留在 `constraints`，不依赖关键词召回。

An empty evidence list represents planning, not verified artifacts. Register existing project-relative files as input/artifact, or use the documented memory format. Keep essential constraints in the checkpoint.

下一会话只给项目、Skill 与命令前缀，让助手只读恢复。按任务找流程可加 `resume --query "video" --max-chars 10000`。默认预算为完整响应 6000 字符；示例预算不是最低值。CLI 统计成功 stdout，MCP 还计工具包装，均不是 token 数。不足时报 `BUDGET_TOO_SMALL`，不截断、不丢约束。

In a fresh session supply the same bindings and request read-only recovery. Optional query uses literal keywords. Budgets cover the full response and fail without truncation; character counts are not token counts.

旧包按帮助分流：先 `status`，有 checkpoint 才 `check` → `context`。Alpha.5 不支持记忆/query 或 resume。`NO_CHECKPOINT` 表示尚未保存，不是网络故障。保存的下一步仍须按当前要求和引用状态审阅。

Older packages use status, then check/context only with a checkpoint. Alpha.5 has no memory/query or resume. No checkpoint is not a network failure; recorded next steps still need review.

## 可选双助手 / Optional handoff

两位助手须获准访问同一份项目。A 保存后用当前 revision 创建交接，B 显式领取，再恢复上下文：

```text
<cli> --project <absolute-project> handoff --recipient reviewer --expect-revision <revision>
<cli> --project <absolute-project> accept --id HANDOFF_ID --recipient reviewer
<cli> --project <absolute-project> resume --max-chars 10000
<cli> --project <absolute-project> receipt --id HANDOFF_ID
```

`reviewer` 是合作标签，不是认证身份。文件变化、过期、陈旧修订或重复领取会拒绝；回答丢失先查 receipt，不重复外部动作。B 的单阶段产物可按[成果回存](docs/result-return.md)关联原交接，A 再读真实文件并验收。工具不发消息、不启动助手，也不保证邮件、付款或发布恰好执行一次。

Both assistants need authorized access to the same project. Labels are not authenticated identities. Check receipts after lost responses; result registration does not verify content or authorize repeating external actions.

`export --output review.json` 只在项目根创建新的审阅包，不覆盖文件。里面的文字和相对文件名仍可能敏感；它不是原始文件备份、数据库导入或权限凭证。只读文件/聊天宿主可人工审阅快照，但不能声称实时检查或自动回写；远端 HTTP 和跨设备同步尚未提供。

Export creates a new review snapshot, not a database import, full backup or authority token. File-only hosts can review it manually; they cannot claim live validation or writes. No remote HTTP or cross-device sync is supplied.

## 可选 MCP / Optional MCP

CLI 可以单独使用。需要本地 stdio MCP 的宿主，按[MCP 接入](adapters/mcp.md)配置，并在同一专用环境另装依赖：

```text
<已选环境的Python> -m pip install "mcp==2.2.0"
```

这一步联网下载第三方依赖。Windows 换用环境内 Python。启动命令是环境内 `glom-continuity-mcp` 的绝对路径（Windows 为 `.exe`），启动参数带 `--project` 与项目绝对路径；单次工具调用不传项目。

MCP is optional. Install its SDK in the dedicated environment; this downloads third-party dependencies. Start the environment's absolute MCP executable bound to one project. Individual calls take no project argument.

先发现工具再调用，如 `continuity_resume(query="video", max_chars=20000)`。默认只读，获准保存或领取时才显式为该连接启用 `--allow-writes`，不要绕过只读限制。启用写工具不授予邮件、付款或发布权限。MCP 包装计入字符预算。

Discover tools before calling them. Read-only is the default; opt into writes only for the selected authorized connection. This does not authorize unrelated external actions. Cloud assistants still apply their own fees/privacy rules to received context.

## 便携包或源码 / Portable package or source

若已取得匹配版本的完整便携包或固定源码，可从 README 所在目录运行，无需安装依赖：

```sh
python3 -B scripts/continuity.py --version
python3 -B scripts/continuity.py --help
python3 -B scripts/smoke_demo.py --output ./my-first-demo
```

Windows 将 `python3` 换成 `py -3`。输出目录必须不存在。演示文件与解释同上；这不是实机模型验收。普通使用不必从源码构建 wheel。

Use a matching portable package or pinned source directory. On Windows substitute `py -3`. The demo requires a new directory and is a synthetic protocol check. Ordinary users need not build a wheel.

<a id="upgrade-existing"></a>

## 升级，不重建项目 / Upgrade without resetting the project

1. 结束保存，停止该项目所有写入者和 MCP 写连接；备份完整 `.continuity/` 与引用文件，保留相对路径，不覆盖已有备份或收集密钥。
2. 把新版本放在独立工具目录或新虚拟环境，核对版本与配套清单，保留旧工具供审阅后回退。
3. 对同一个项目路径检查版本/帮助、doctor 和恢复结果。已有项目不要再次 init，也不要删除数据库。
4. 核对后只调整这一个助手连接的可执行路径，保留原项目路径与权限模式；重启该连接，使用匹配 Skill，不覆盖其他项目指令。
5. 异常时停止写入，保留报错和数据。旧读者可能不展示新版回存关联；不等于记录被删除。回退须核对兼容性，不能把旧备份盖到新进展上。

Stop all writers, back up storage and referenced files, install separately, then inspect the same project. Update only the selected host connection after verification, retaining its project binding and permissions. Keep old tools for a reviewed rollback; never overwrite new progress with an old backup.

Recaloom 是显示名；仓库、Python 包、命令、MCP 名称和存储标识仍为 glom-continuity。改名不需要迁移或第二份数据库，也不提供跨电脑自动同步。旧同名软件的数据不能当成本工具项目。

## 隐私、停用与故障 / Privacy, removal and errors

状态在项目 `.continuity/state.sqlite3`。原材料留在原处，数据库只存登记文本与文件指纹，不备份原文件。草稿、数据库、导出包和恢复内容都可能敏感，不直接公开。工具不上传项目内容，但连接的云端助手可能发送收到的上下文给模型服务。不要并发网盘同步正在写入的 SQLite。

State stays in the selected project; original files remain in place. Back up both, with writes stopped. Local storage does not mean a connected cloud assistant keeps all context on-device.

<a id="preserve-data-removal"></a>

### 保留原规则与记忆的停用 / Stop without deleting rules or memory

先停用项目入口并核验，再卸载工具。不要删除或清空原用户 `AGENTS.md`、`CLAUDE.md`、`.claude/`、`.workbuddy/`、`.codebuddy/` 规则，也不要删除项目 `.continuity/`、检查点草稿或原材料。当前 XS 实际管理的目标分别是 `AGENTS.md`、`.claude/rules/recaloom.md`、`.codebuddy/CODEBUDDY.md`；宿主名称不代表另一个可清理目录。

带 `entry` 的候选在工具仍可用时，按上面的“暂停与重新启用”流程，先 `entry status` 审阅项目、入口布局及整份文件的 `data.sha256`，获准后 `entry pause`，再 `entry status` 读回；沿用同一 `<cli> --project <项目绝对路径>` 前缀及所选 `--host`。补充只读诊断：

```text
<cli> --project <项目绝对路径> doctor --host codex
```

对所选宿主将 `codex` 换成 `claude-code` 或 `workbuddy`，不是逐个修改所有宿主。检查 pause 的结果字段：独立模板看 `data.operation.outcome`，嵌入块看 `data.upgrade.outcome`；确认结果无待审问题且 status 为 `paused`，并审阅 doctor 的全部问题，不能只看 `ok:true`。`data.layout=embedded` 时保留整份文件和用户正文，由工具替换为规范暂停块；不要手工删块、改标记/绑定或搬走整份文件来“卸载”。暂停用于以后重新启用，不等于彻底移除块。

#### 解除项目接入，而不是一直留着暂停块

先查看实际安装的 `entry --help`。只有列出 `detach` 的 XS 候选才有以下命令；旧版本不要猜命令，也不要照新版说明手工删块。使用同一项目、同一环境：

```text
<cli> --project <项目绝对路径> entry detach --host codex
<cli> --project <项目绝对路径> entry detach --host codex --apply --expect-state <预览的active或paused> --expect-sha256 <预览的data.sha256>
```

第一条只预览，第二条才修改所选入口。核对 `data.removal.content`：嵌入块显示将原样留下的用户正文；独立模板为 `null`，表示整个规范模板将移到同目录的唯一 `.recaloom-<host>.detached-*` 保留件，不再占用原指令文件名。不要把 `null` 理解为删除项目资料。

- 嵌入块只去掉工具自己的完整规范块；当前用户文字、BOM、换行及 YAML 前置信息保留，不用安装时的旧备份覆盖后来的用户修改。交换后旧完整入口留在 `data.removal.retained_path`。
- 确认 `data.state=detached`，以及 `data.removal.outcome` 是 `exchange_observed`（嵌入）或 `move_observed`（独立）；读回用户正文和保留件核对。仅 `ok:true` 不够。
- 恢复成普通用户文件后，旧版 `entry status` 可能返回 `ENTRY_UNRECOGNIZED`：它只能识别规范 Recaloom 入口，不能把这当作再次安装或覆盖用户文件的许可。
- 摘要、状态或路径变化就重新审阅，不自动重试。结果 `needs_review` 或未知时保留全部对象；这些文件操作不是对抗同一用户并发写者的 CAS 保证。
- 原生安全移动/交换目前在支持相应接口的 macOS/Linux 文件系统使用；不支持的平台只提供预览并拒绝修改，不能降级为覆盖或删除。

`detach` 不删除 `.continuity/`，不卸载 Python 包，不移除其他 MCP/Skill 配置，不停正在运行的助手，也不撤回它已经读过的内容。要恢复接入，重新预览 `setup` 或 `integrate`；不直接把保留件搬回去绕过运行时校验。

命令缺失、规则无法识别、摘要/项目不符、平台不支持、`needs_review` 或结果未知时，停止并保留原件及保留件，报告尚未确认停用；不要删除规则、重建入口/数据库或循环重试来凑成功。仅为卸载不要执行 enable。暂停不撤回旧会话上下文、不停止任务、不撤销权限；在该项目新会话确认 Recaloom 不再自动恢复，原用户规则仍有效。

确认入口停用后，仅从所选客户端配置中移除你为 Recaloom 添加的 Skill/连接项，保留同文件里的其他配置；关闭对应 MCP 子进程。没有 XS 入口的旧版只处理自己明确添加的连接，不猜测新命令。wheel 卸载只使用专用环境：

```text
<已选环境的Python> -m pip uninstall glom-continuity
```

Windows 换用环境内 Python；便携版只移走已确认的工具文件，不搬走整个项目或用户规则目录。卸载包不会移除项目入口或记忆；保留暂停模板/块和项目数据，不删库排错。本工具不安装自启动守护进程。

Before uninstalling an XS tool, either pause the recognized entry for later re-enabling or, when the installed CLI lists `entry detach`, preview and explicitly detach it. Detach requires `--apply`, the reviewed `--expect-state` and `--expect-sha256`. It restores exact current user text around an embedded block, retaining the previous full file; a standalone template is moved to a unique inert backup, never deleted. Check `data.state=detached` and `data.removal.outcome` (`exchange_observed` or `move_observed`), then read back the files; `ok:true` alone is insufficient. Safe native mutation is limited to supported macOS/Linux filesystems; unsupported platforms retain preview and refuse mutation. Unknown/edited rules, changed bindings and uncertain results require review, not forced removal. Project memory remains, and this does not revoke already loaded context or stop a host. The pause route still uses `data.operation` / `data.upgrade` and leaves a recognized paused entry. Never delete a shared rule file or a rules directory. Enable is a separate action, not an uninstall step.

After verification, remove only the Recaloom Skill/connection items you added, preserving other client configuration, close its MCP child process and uninstall from its dedicated environment or move only the portable tool files. Package removal does not remove project rules or memory. Pausing does not stop running tasks or revoke loaded context/permissions; verify in a fresh project session that Recaloom no longer restores automatically and user rules still apply. Older packages without entry commands use only their existing, identified connection-removal route. No autostart daemon is installed.

| 提示 / Error | 处理 / Action |
| --- | --- |
| `BUDGET_TOO_SMALL` | 增加字符预算，保留限制 / Increase budget, keep constraints |
| `REVISION_CONFLICT` / `STALE_HANDOFF` | 读最新节点并合并，再交接 / Read and reconcile current progress |
| `needs_review` / `EVIDENCE_CHANGED` | 审阅引用变化后保存 / Review changes before saving |
| `ALREADY_ACCEPTED` | 查 receipt，不重复外部动作 / Read receipt; do not repeat actions |
| `NOT_INITIALIZED` / `NO_CHECKPOINT` | 仅在获准首次保存时初始化或保存 / Initialize or save only when authorized |
| `UNSAFE_PATH` / `SENSITIVE_CONTENT` | 修正路径或清除敏感内容，不绕过 / Fix the input, do not bypass checks |
| `IO_ERROR` / `UNRECOGNIZED_STORAGE` / `UNSUPPORTED_SCHEMA` / `UNSAFE_STORAGE` | 保留数据，停止写入并检查 / Preserve data, stop and investigate |
| `STORAGE_RECOVERY_REQUIRED` | 先停止读写并完整备份，再[明确恢复存储](#storage-recovery-after-a-crash)；不删日志、不自动重试 / Back up, explicitly recover; never delete journals |

完整规则见[接口说明](adapters/README.md)与[Skill](skills/project-continuity/SKILL.md)。公开反馈只附版本、系统、助手、失败步骤、错误码及虚构复现，不发密钥、公司资料或原始聊天。

## 实测范围 / What was tested

[实测记录](docs/verification.md)按日期、版本和哈希区分协议、真实助手、安装包与公开发行，包含原始失败和未验项。历史 Codex → DeepSeek Harness → 新 Codex 接力不是 alpha.7 的新实测。Windows runner 的协议/安装通过也不代表普通 Windows 实机全部验证。外部真人首用、完整公平效果对照及其他宿主仍待验证，没有 token 节省或优于竞品的结论。

The verification record retains dated, version-bound evidence and failures. Historical relay/CI results do not certify alpha.7, physical devices or all hosts. No measured token-saving or competitive claim is made.

需要重跑源码协议测试时，仅在包含 tests 的匹配便携包/源码目录运行：

```sh
python3 -B -m unittest discover -s tests -v
```

未装可选 SDK 的 MCP 跳过项不算通过；wheel 环境不保证附带测试。语义正确性、身份认证、加密、调度、远端同步及外部动作只执行一次都不在本工具保证内。相同系统用户的磁盘访问是信任前提，见[安全说明](SECURITY.md)。

## 历史版本对照 / Historical versions

[Alpha.5 发布页](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.5)的具名 `glom-continuity-0.1.0-alpha.5.zip` 与对应 wheel 保留原有预览功能，不包含本页新增能力。历史附件保留其验收候选原字节，包内发布状态文字是当时快照；后续证据见该发布说明和实测记录。GitHub 自动生成的 Source code 不等于这些具名附件。

Alpha.5 remains the historical compatible preview. Its named assets preserve their tested candidate bytes and packaging-time prose; later evidence is recorded separately. It has no newer memory, resume, diagnosis or linked return capabilities.

### 获取固定的 dev4 源码 / Get the pinned dev4 source

以下保留为历史复现路径，不是普通用户的 alpha.7 安装入口。需要 Git；在工具存放目录执行，不在业务项目或旧安装目录内运行。`recaloom-dev4` 必须不存在；已有时先检查，不覆盖、不删除。

This pinned source route is retained for historical comparison, not normal alpha.7 onboarding. Use a new tools directory, outside working projects and existing installations.

```sh
git clone --no-checkout https://github.com/fugui6688661/glom-continuity.git recaloom-dev4
cd recaloom-dev4
git checkout --detach 0a516e693f918e8406794f583469afa2aeaf28cd
git rev-parse HEAD
python3 -B scripts/continuity.py --version
python3 -B scripts/continuity.py --help
```

应看到相同完整提交号和 `0.1.0.dev4`，帮助包含 resume、doctor、return-work。Windows 最后两行换用 `py -3`。Git 会联网取公开源码，不启动服务或初始化项目。固定提交不是发行签名，这个快照也不是 alpha.7 包的验收。

Expect the exact commit and dev4 version. On Windows use `py -3`. Git downloads source without starting a service or initializing a project. A pinned commit is not publisher authentication or alpha.7 package validation.
