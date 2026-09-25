# 安装与第一次使用 / Installation and first use

需要 Python 3.10+。Recaloom 是本地 CLI 与可选 MCP 连接器；把工具、演示和工作资料分开存放。基础 CLI 没有第三方运行时依赖，不调用模型，也不需要模型账号。

Requires Python 3.10+. Keep the tool, demos and working data separate. The base CLI has no third-party runtime dependencies and makes no model calls.

## 版本与发布状态 / Version and release status

本页下载的是已公开的 v0.1.0-alpha.6 预览版，不是稳定版；开发分支 `0.1.0-alpha.7` 尚未发行。Alpha.6 把现有 dev4 的项目记忆、`resume`、`doctor`、`return-work` 打包进 alpha。安装以[对应 Release](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.6)的具名附件及配套清单为准，不把仓库文档或源码版本当作本机已更新的证明。

This page downloads the published v0.1.0-alpha.6 preview, not a stable release. Development version `0.1.0-alpha.7` is not yet released. Use Alpha.6's named Release assets and checksums; updated source or documentation does not prove your installed copy was updated.

已有项目不要重新 `init`；先看本页升级步骤。没有自动更新器，文档更新不会升级已安装程序。本页不提供 PyPI、Homebrew 或应用商店安装入口，不从同名陌生软件安装。

Do not reinitialize existing projects. Documentation changes do not upgrade an installed copy; no automatic updater or PyPI/Homebrew/app-store entry is offered here.

## 推荐入口：专用环境中的 wheel / Wheel in a dedicated environment

先在工具存放位置新建专用虚拟环境。`.recaloom-alpha6` 必须尚不存在；已有此目录时先检查它，不覆盖、不删除。不要在系统 Python 中安装，不需要管理员权限或修改全局 PATH。

Create a new dedicated environment in your tools directory. If that path already exists, inspect it instead of replacing it. Do not install into system Python; no administrator access or global PATH changes are needed.

Mac / Linux：

```sh
python3 -m venv .recaloom-alpha6
```

确认对应 Release 已提供下列具名 wheel 后，使用这一条安装命令。附件不可用时先核对发布页和版本，不换成旧包来完成新版教程。已从维护者取得本地候选 wheel 的审阅者，使用下一节的本地安装方式。

Use this command after confirming the matching named wheel is available on its Release page. If it is unavailable, check that page and version instead of substituting an older package. Reviewers with a supplied candidate wheel can use the local route below.

```sh
.recaloom-alpha6/bin/python -m pip install --no-index --no-deps "https://github.com/fugui6688661/glom-continuity/releases/download/v0.1.0-alpha.6/glom_continuity-0.1.0a6-py3-none-any.whl"
```

此命令会联网下载指定 wheel，不查包索引、不安装其他依赖、不调用模型。

This downloads the specified wheel over the network, without an index lookup, other dependencies or model calls.

Windows PowerShell 先建环境：

```powershell
py -3 -m venv .recaloom-alpha6
```

然后将上方 pip 命令开头的 `.recaloom-alpha6/bin/python` 换成 `.\.recaloom-alpha6\Scripts\python.exe`，保留同一 URL 和参数。无需激活脚本或修改 PowerShell 执行策略。

Then use the same pip command with `.\.recaloom-alpha6\Scripts\python.exe` as its executable. No activation script or PowerShell-policy change is required.

### 已提供的候选文件 / Supplied candidate files

本地方式和上方直链方式二选一。先核对收到的候选版本和配套 SHA-256 清单；不要套用 alpha.5 的哈希。在已新建的专用环境安装：

Choose either the local route or the release URL, not both. Verify the supplied candidate and its own checksums before installing it in the new environment:

```sh
.recaloom-alpha6/bin/python -m pip install --no-index --no-deps ./glom_continuity-0.1.0a6-py3-none-any.whl
```

本地 wheel 安装不联网。Windows 同样替换为环境内 Python，并使用收到的文件路径。公开附件的 `SHA256SUMS` 可用 `shasum -a 256 -c SHA256SUMS` 校验，需备齐清单中所列文件；Windows 用 `Get-FileHash 文件名 -Algorithm SHA256` 逐项比较。哈希校验不是发布者签名认证。

A local wheel install is offline. On Windows use the environment Python and the supplied file path. Verify all listed assets with SHA256SUMS, or compare individual Get-FileHash results. Integrity hashes do not authenticate the publisher.

### 检查安装并跑合成演示 / Check the installation and demo

Mac / Linux：

```sh
.recaloom-alpha6/bin/glom-continuity --version
.recaloom-alpha6/bin/glom-continuity --help
.recaloom-alpha6/bin/glom-continuity-demo --output ./installed-demo
```

Windows：

```powershell
.\.recaloom-alpha6\Scripts\glom-continuity.exe --version
.\.recaloom-alpha6\Scripts\glom-continuity.exe --help
.\.recaloom-alpha6\Scripts\glom-continuity-demo.exe --output .\installed-demo
```

alpha.6 的 CLI 版本应为 `0.1.0-alpha.6`，wheel 文件名使用 Python 版本形式 `0.1.0a6`。帮助应列有 `resume`、`doctor`、`return-work`；不符时先查调用路径，不在旧包上猜命令。

Expect CLI version `0.1.0-alpha.6`; the wheel uses Python's `0.1.0a6` spelling. Confirm resume, doctor and return-work in help. A mismatch needs a path/version check, not guessed commands.

`installed-demo` 必须是新目录。打开其中的 `演示结果.md`，核对恢复、文件变化拒绝和重复领取拒绝；`events.json` 保留响应，`handoff-review.json` 是审阅快照。这是合成 CLI 协议回放，不是两个模型在工作，也不单独证明所有恢复或记忆功能通过验收。

Use a new demo directory; existing data is not overwritten. The generated report, events and review snapshot show synthetic protocol behavior, not a live-model trial or complete feature acceptance.

## 给助手正确的位置 / Bind the assistant

首次使用需要三项具体信息，按[首次使用卡](docs/first-use.md)填写：

1. 所选项目的绝对路径。
2. 匹配版本的 `skills/project-continuity/SKILL.md` 的绝对路径。
3. 可执行命令前缀，包括解释器及所需参数，而不只是“工具目录”。

Supply the absolute project path, the matching Skill's absolute path, and the complete executable prefix.

wheel 安装不保证包含 `skills/`、文档或 `scripts/continuity.py`。另外取得同一 alpha.6 Release 的具名便携附件，或与工具匹配的候选/固定源码，完整保留目录结构供助手读 Skill 及其相对引用；不要只复制一个 Skill 文件后让文档链接失效。旧 Skill 或任意更新的 main 不能证明版本匹配。取得文档并不要求再安装第二份工具。

A wheel does not guarantee a sibling skills, docs or scripts directory. Obtain the matching Release's named portable asset, or matching supplied candidate/pinned source, and preserve its documentation layout. Do not assume an old Skill or moving main branch matches the wheel. Reading those files does not require installing another executable.

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

```sh
.recaloom-alpha6/bin/python -m pip install 'mcp==2.2.0'
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

移除自己添加的 Skill/客户端配置，关闭对应 MCP 子进程，在新会话确认不再加载。wheel 卸载只使用专用环境：

```sh
.recaloom-alpha6/bin/python -m pip uninstall glom-continuity
```

Windows 换用环境内 Python；便携版可移走工具文件。保留项目记忆，不删库排错。本工具不安装自启动守护进程。

Remove only the entries you added, close the associated MCP process, and uninstall from its dedicated environment or move the portable files. Keep project data. No autostart daemon is installed.

| 提示 / Error | 处理 / Action |
| --- | --- |
| `BUDGET_TOO_SMALL` | 增加字符预算，保留限制 / Increase budget, keep constraints |
| `REVISION_CONFLICT` / `STALE_HANDOFF` | 读最新节点并合并，再交接 / Read and reconcile current progress |
| `needs_review` / `EVIDENCE_CHANGED` | 审阅引用变化后保存 / Review changes before saving |
| `ALREADY_ACCEPTED` | 查 receipt，不重复外部动作 / Read receipt; do not repeat actions |
| `NOT_INITIALIZED` / `NO_CHECKPOINT` | 仅在获准首次保存时初始化或保存 / Initialize or save only when authorized |
| `UNSAFE_PATH` / `SENSITIVE_CONTENT` | 修正路径或清除敏感内容，不绕过 / Fix the input, do not bypass checks |
| `IO_ERROR` / `UNRECOGNIZED_STORAGE` / `UNSUPPORTED_SCHEMA` / `UNSAFE_STORAGE` | 保留数据，停止写入并检查 / Preserve data, stop and investigate |

完整规则见[接口说明](adapters/README.md)与[Skill](skills/project-continuity/SKILL.md)。公开反馈只附版本、系统、助手、失败步骤、错误码及虚构复现，不发密钥、公司资料或原始聊天。

## 实测范围 / What was tested

[实测记录](docs/verification.md)按日期、版本和哈希区分协议、真实助手、安装包与公开发行，包含原始失败和未验项。历史 Codex → DeepSeek Harness → 新 Codex 接力不是 alpha.6 的新实测。Windows runner 的协议/安装通过也不代表普通 Windows 实机全部验证。外部真人首用、完整公平效果对照及其他宿主仍待验证，没有 token 节省或优于竞品的结论。

The verification record retains dated, version-bound evidence and failures. Historical relay/CI results do not certify alpha.6, physical devices or all hosts. No measured token-saving or competitive claim is made.

需要重跑源码协议测试时，仅在包含 tests 的匹配便携包/源码目录运行：

```sh
python3 -B -m unittest discover -s tests -v
```

未装可选 SDK 的 MCP 跳过项不算通过；wheel 环境不保证附带测试。语义正确性、身份认证、加密、调度、远端同步及外部动作只执行一次都不在本工具保证内。相同系统用户的磁盘访问是信任前提，见[安全说明](SECURITY.md)。

## 历史版本对照 / Historical versions

[Alpha.5 发布页](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.5)的具名 `glom-continuity-0.1.0-alpha.5.zip` 与对应 wheel 保留原有预览功能，不包含本页新增能力。历史附件保留其验收候选原字节，包内发布状态文字是当时快照；后续证据见该发布说明和实测记录。GitHub 自动生成的 Source code 不等于这些具名附件。

Alpha.5 remains the historical compatible preview. Its named assets preserve their tested candidate bytes and packaging-time prose; later evidence is recorded separately. It has no newer memory, resume, diagnosis or linked return capabilities.

### 获取固定的 dev4 源码 / Get the pinned dev4 source

以下保留为历史复现路径，不是普通用户的 alpha.6 安装入口。需要 Git；在工具存放目录执行，不在业务项目或旧安装目录内运行。`recaloom-dev4` 必须不存在；已有时先检查，不覆盖、不删除。

This pinned source route is retained for historical comparison, not normal alpha.6 onboarding. Use a new tools directory, outside working projects and existing installations.

```sh
git clone --no-checkout https://github.com/fugui6688661/glom-continuity.git recaloom-dev4
cd recaloom-dev4
git checkout --detach 0a516e693f918e8406794f583469afa2aeaf28cd
git rev-parse HEAD
python3 -B scripts/continuity.py --version
python3 -B scripts/continuity.py --help
```

应看到相同完整提交号和 `0.1.0.dev4`，帮助包含 resume、doctor、return-work。Windows 最后两行换用 `py -3`。Git 会联网取公开源码，不启动服务或初始化项目。固定提交不是发行签名，这个快照也不是 alpha.6 包的验收。

Expect the exact commit and dev4 version. On Windows use `py -3`. Git downloads source without starting a service or initializing a project. A pinned commit is not publisher authentication or alpha.6 package validation.
