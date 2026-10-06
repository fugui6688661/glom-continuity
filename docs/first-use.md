# 第一次使用 Recaloom

先试一个没有私人资料的小项目。一个助手就能保存和恢复，第二位助手是可选步骤。安装以对应 Release 的具名附件及配套清单，或明确提供的固定候选为准；步骤本身不代表实测通过。

## 1. 先确认你用哪条接入方式

XS 新安装先走 [INSTALL 的一条 create](../INSTALL.md#xs-candidate)：成对提供可信本地绝对 wheel 路径和该文件的 64 位 SHA-256。这是本地候选接口，不是公开 Alpha.7 更新；平台验收以具名候选记录为准。返回 `TOOL_READY` 后，保留完整结果（尤其 `data.cli_argv`），直接到[第2步首次保存](#first-save)，不再建环境或手动 pip 安装。仅 `RUNTIME_READY` 表示环境准备好，不能当作工具已装。

`TOOL_READY` 仍为 `host_integrated=false`：没有初始化项目、改动 host、配置入口或启用自动保存。首次保存与后续宿主接入是分别授权的步骤；不要先拿空项目反复尝试 setup。已有环境目标一律拒绝，hash 不符在创建前停止；失败保留本次已建环境，不重试。旧分步 create/check 仅作 [诊断或兼容](../INSTALL.md#xs-candidate)。

如果你的 XS 候选已把项目入口装好，助手也能读取该项目的规则，日常只需指定项目，说“继续这个项目”。程序和说明位置已写在入口里，不必每次重贴。首次接入仍需核对工具、项目与文件权限；新会话的检验见第3步。

尚未配置入口时，XS 候选的 `<cli> --project <项目绝对路径> setup` 会预览接手卡，不改文件。已有检查点的项目可按[安装说明](../INSTALL.md)选择宿主并显式写入项目规则；已有规则先预览合并，不要覆盖。空项目先完成第2步。接手卡只给获准访问该项目的助手，它不是跨电脑同步。

公开 Alpha.7 没有 `setup`；不支持项目规则的宿主也走下面的手动路线。它们仍可使用工具，不需要为此换成 Harness。

尚未安装的手动路线按[安装说明](../INSTALL.md)将工具装进新建的专用虚拟环境，不修改系统 Python；已有 `TOOL_READY` 则跳过。基础 CLI 无第三方运行时依赖、不调用模型，也不需要模型账号；[MCP](../adapters/mcp.md)可选。云端助手仍有自己的费用和隐私规则。

走手动路线时，交给助手的三项位置要分清：

| 信息 | 应填写什么 |
| --- | --- |
| 项目 | 已有测试目录的绝对路径 |
| Skill | 与工具版本匹配的 `skills/project-continuity/SKILL.md` 的实际绝对路径 |
| 命令前缀 | wheel 用 `/absolute/tool-env/bin/glom-continuity`；便携版用 `python3 -B /absolute/tool/scripts/continuity.py` |

Windows wheel 使用环境内 `Scripts/glom-continuity.exe` 的绝对路径；也可用环境内 Python 加 `-I -B -m glom_continuity`。路径有空格时分别引用，不猜全局 PATH。

XS 候选 wheel 用户先运行 `<cli> --project <项目绝对路径> doctor`，从 `data.usage` 找到随包 Skill。只有 `available` 才表示这份说明与所调用核心的清单一致；`source_unsealed` 只定位源码说明，`unavailable` 要先处理列出的原因。公开 Alpha.7 等没有 `usage` 的旧包仍需另取匹配文档。不要因文档旁边有脚本就换用另一份程序；细节见 INSTALL。

已装过的用户先核对现有 `--version` 和 `--help`，不要覆盖环境或重建项目。将版本与所选具名包核对，并确认帮助包含 `resume`、`doctor`、`return-work`；候选和已发行包可能有相同版本文字，仍需核对来源与清单，不能只看名称。

<a id="first-save"></a>

## 2. 让当前助手保存一次

XS 的 `TOOL_READY` 路线把完整 create 结果和选定项目绝对路径交给助手即可，不需用户手工拼程序路径。下文 `<cli>` 逐项沿用返回的 `data.cli_argv`，不能丢参数或把整串当一个可执行文件名；shell 中逐项引用，PowerShell 用 `&` 调用首项。`<project>` 是该项目绝对路径，尖括号不可原样执行。手动路线仍使用第1步已核对的前缀与匹配 Skill；两条路线都不重复安装。

XS 助手先沿用此 `<cli>` 运行 `--project <project> doctor`，检查所选项目，并从 `data.usage.skill_path` 读取 `available` 的配套 Skill；这是首次保存的项目检查，不是再安装或证明 host 已接入。说明不可用、项目绑定不符、存储损坏或不兼容就停下，不借用另一份程序；确实未初始化则按下方授权分流。没有本地文件与命令权限的聊天窗口不能完成保存。

把下面的话交给有本地文件和命令权限的助手，替换括号。不要把 API key、公司资料或原始聊天放进试用，也不要公开含本机路径的 create 结果。

> 工具绑定：[XS 填本次 TOOL_READY 的完整 create 结果；手动路线填匹配 Skill 的绝对路径及完整命令前缀]。测试项目：[已有测试目录的绝对路径]。先按上述路线核对实际程序并读匹配 Skill，检查版本和帮助，再只读检查项目状态。请保存：准备一份活动安排，预算上限5000元、50个人、场地未定；下一步比较两个候选场地。不得付款或联系商家。只有确实未初始化且为了本次首次保存，才允许初始化；已有项目不要再次 init。保存后告诉我项目、修订号、保存的限制和未确认事项，异常时先说明。

看到实际保存结果才算完成这一步。`init` 只创建存储，助手回答“记住了”不能代替保存。这个例子只有规划文字，没有引用文件，恢复状态可以是 `no_references`。

### 助手应实际执行的顺序

先运行 `<cli> --project <project> resume --max-chars 10000` 检查当前项目。只有返回 `not_initialized`，且用户允许本次首次保存时，才执行 `<cli> --project <project> init --name "活动安排试用"`。已有项目不重新 init；`no_checkpoint` 表示尚无保存节点；引用变化或其他错误先审阅，不覆盖来修复。

将审阅过的要求写入该项目内一个**新** JSON 草稿文件，例如 `first-checkpoint.json`（已存在就不要覆盖）。例子恰好六个字段；换成自己的需求，不要把示例数字当作用户事实：

```json
{
  "objective": "准备活动安排，预算上限5000元，50人，场地未定",
  "next_action": "比较两个候选场地",
  "constraints": ["不得付款或联系商家"],
  "decisions": [],
  "unresolved": ["场地未定"],
  "evidence": []
}
```

读取草稿确认内容后，用同一前缀依次执行：

```text
<cli> --project <project> status
<cli> --project <project> checkpoint --from-file <project>/first-checkpoint.json --expect-revision <刚读到的data.revision>
<cli> --project <project> resume --max-chars 10000
```

如果当前 `checkpoint --help` 支持 `--expect-project-id`，在保存命令中追加已核对的项目 ID，避免同版本号的另一个项目收下这份记录。ID 不符先检查位置，别自动改 ID 重试；旧版不支持时不要照填。

每条成功才继续。读回应与刚保存的项目 ID、修订号和要求一致；版本冲突先重新核对，不盲重试。`evidence: []` 只保存规划，不能称引用或产物已验证。登记文件时，只填存在的项目内相对路径及 `input` / `artifact`，指纹由工具计算。

### XS：首次保存后接入所选助手

```text
<cli> --project <project> setup --host codex
```

先审阅预览。只有获准接入该项目、入口不存在且预览无阻碍时，才执行同一命令加 `--write-instructions`。选择 Claude Code 或 WorkBuddy 则将 `codex` 换成 `claude-code` 或 `workbuddy`；不推定一家的授权涵盖全部。已有个人规则先按 [INSTALL 的 integrate 流程](../INSTALL.md)审阅合并；已有 Recaloom 入口用 `entry status` 检查，升级用 `entry upgrade`，不再写第二份。Windows 上自动写入/原生生命周期支持以实际命令限制为准，不以这段示例宣称支持。

最后用 `<cli> --project <project> doctor --host codex`（或刚选的宿主）检查，处理所有 `issues`。`written_unverified`、`active` 均不代表助手读过；接下来用第3步的新会话检验。公开 Alpha.7 没有这些 XS 命令，直接走第3步的三项位置路线。响应太长返回 `BUDGET_TOO_SMALL` 时，按帮助增加 `--max-chars`，不要删掉约束凑预算。

## 3. 新开会话，只给位置

不要复制上一段活动要求。先选中同一个项目，再开新会话。

### 已配置 XS 项目入口

把下面这句交给能读取项目规则、执行本地命令的助手：

> 继续这个项目：[项目绝对路径]。先按项目规则只读恢复，告诉我上次保存的预算、人数、未确定事项和下一步。本次不保存、不初始化、不领取交接。

这次只给项目位置，不再提供 Skill 和程序路径。核对助手实际调用的工具、项目 ID、修订号与恢复输出；它应读回5000元、50人、场地未定和比较两个候选场地。若它没有读取入口，或找不到绑定的程序，要说明缺在哪一步；不能靠猜测、重建存储或反复安装凑出答案。

### 没有配置入口，或使用公开 Alpha.7

新会话仍需下面三项位置：

> Skill：[同一匹配 Skill 的绝对路径]。命令前缀：[同一可执行命令前缀]。测试项目：[同一项目绝对路径]。先读 Skill，确认工具可用，然后只读恢复；不要初始化、保存或自动领取交接。告诉我预算、人数、尚未确定的事和下一步，并说明用了哪个项目的哪一版记录。

两条路线都只恢复已保存的记录。安装工具不保证每个宿主都会自动加载规则，也不启用自动保存。没有本地文件或命令权限时，恢复尚未成功。

### 接着做出一份东西

确认恢复内容后，再指定允许的交付，例如“比较场地资料，写到 venue-comparison.md；不要联系商家或保存新记忆”。检查实际文件是否保留预算和未知项，而不是只看助手说“已经接上”。恢复成功不等于任务已经做对。

要检查文件变化，可在这个测试项目登记一份虚构输入，保存并创建交接，然后修改这份测试输入。旧交接应因引用变化被拒绝，助手应说明需要审阅。不要修改真实工作文件做演示。

## 4. 需要第二位助手时

两位助手都要能访问同一份本地项目。B 的项目入口已配置且能读取时，给它项目路径和本次 handoff ID；否则给同样的三项位置和 handoff ID。聊天链接不会共享文件，也没有跨电脑自动同步。

A 保存 checkpoint 并创建 handoff。B 检查、领取，再读回目标和限制后工作。单阶段任务可按[成果回存](result-return.md)用 `return-work` 关联原交接和真实产物；A 查询原交接的 `receipt.result`，再查看实际文件。输入或基础版本已变化时，先解决冲突，不能硬套旧交接。

由你把接手或回传指令送到另一位助手，工具不会自动唤醒它。领取表示接上交接，回存表示有登记结果可看，内容是否合格仍须核查。单助手保存不需要这些步骤。

## 卡住了，先分清是哪一步

| 现象 | 怎么处理 |
| --- | --- |
| 新会话仍问旧要求，没读取项目记录 | 确认选中了正确项目、宿主能读项目规则；没有入口时用手动接手卡，不让它猜 |
| 找不到命令或 MCP 工具 | 核对可执行前缀、版本和当前会话的工具列表；不要连续重装 |
| wheel 环境里找不到 Skill | 新候选先查 doctor 的 usage；旧包取得匹配文档，不猜路径或借用其他环境 |
| `NO_CHECKPOINT` | 存储存在但尚未保存记录；经授权保存首个节点，不重新 init |
| MCP 只有读取工具 | 默认如此；获准保存时才为这一条连接显式启用写权限 |
| `BUDGET_TOO_SMALL` | 增加响应字符预算，保留限制和未知项；字符数不是 token 数 |
| 文件变化或 `needs_review` | 审阅后再保存新版本，不沿用旧交接假装成功 |
| 陌生、损坏或不兼容存储 | 保留数据并停止，不删除数据库或重新初始化来“修复” |
| 找不到接手成果 | 查当前 checkpoint/回执并核对实际文件；“已领取”不表示交付完成 |

反馈只提供版本、系统、助手名称、失败步骤和错误码。[提交脱敏试用反馈](https://github.com/fugui6688661/glom-continuity/issues/new?template=field_trial.yml)。本卡不新增宿主兼容或模型效果结论，实测范围见[验证记录](verification.md)。

## 已有项目与旧版迁移

已有项目保留原路径和 `.continuity/`，先停写备份，再按 INSTALL 升级工具和匹配 Skill，不重复 init。旧 alpha.5 仍按 `status` 分流，有节点才 `check`、`context`；它没有记忆/query、resume、doctor 或 return-work。旧版双助手回传仍可保存普通 checkpoint，再创建给 A 的返程 handoff。这些旧功能不会因改名或更新文档而升级。

## 停用或卸载：保留原规则与项目记忆

不再使用时，先停用入口，再卸载工具；不要删除原用户规则文件/目录或项目 `.continuity/`、草稿和原材料。带 `entry` 命令的 XS 候选在工具仍可用时，沿用已选 `<cli>` 和 `<project>`：

```text
<cli> --project <project> entry status --host codex
<cli> --project <project> entry pause --host codex --expect-sha256 <刚审阅的data.sha256>
<cli> --project <project> entry status --host codex
<cli> --project <project> doctor --host codex
```

先审阅第一条结果；只有明确要暂停且入口为 `active` 时才执行第二条，已经 `paused` 就只读核验。按所选宿主将 `codex` 换成 `claude-code` 或 `workbuddy`。独立模板检查 `data.operation.outcome`，嵌入块检查 `data.upgrade.outcome`，再确认 status 为 `paused` 并审阅 doctor 的全部问题；外层 `ok:true` 不够。错误、平台不支持或待审结果先停下保留文件，不自动重试或删规则。

`data.layout=embedded` 表示与用户规则共用文件，暂停只替换插件块，用户正文留在原路径。不要删整份 `AGENTS.md`、Claude/WorkBuddy 规则、手工切除/改写 managed block，或清空规则目录。重新启用不是卸载步骤：另经授权后重新审阅 status 的暂停态摘要和绑定，再按 [INSTALL](../INSTALL.md#pause-and-enable) 的 enable 流程操作，不沿用暂停前摘要。

如果要退出项目入口，而非保留暂停态供以后启用，先检查**已安装程序**的 `entry --help` 是否列出 `detach`。包含此命令的 XS 候选支持下面的预览和审阅后应用；公开 Alpha.7 和更早候选不能照搬：

```text
<cli> --project <project> entry detach --host codex
<cli> --project <project> entry detach --host codex --apply --expect-state <预览的active或paused> --expect-sha256 <预览的data.sha256>
```

预览不写文件；只在用户授权退出、预览无问题且状态和摘要已核对后运行第二条。将宿主换成实际所选项。检查 `data.state=detached`、`data.removal.outcome=move_observed` 或 `exchange_observed`，并核对实际文件：独立入口移到不再被发现的备份名；嵌入入口只移除插件块，当前用户正文仍在原位置，旧整份入口另存备份。任何 `needs_review`、冲突、未知块、平台拒绝都先停下，不删除备份或自动重试。数据、工具包、MCP 连接均不由 detach 删除；它也不会撤回已经进入旧会话的内容。

解除后，留下的普通用户规则不再含 Recaloom 块，后续 `entry status` 可能返回 `ENTRY_UNRECOGNIZED`；这不是重新覆盖它的理由。新会话需确认不再加载 Recaloom 入口且原规则仍有效。详细范围见 [INSTALL](../INSTALL.md#preserve-data-removal)。

核验后仅移除所选客户端里自己添加的 Recaloom Skill/连接项、关闭对应 MCP 子进程，再从专用环境卸载包或只移走便携工具。保留其他配置、暂停模板/块和项目数据。暂停不撤回旧上下文、停止任务或撤销权限；新会话还需确认不再自动恢复且原规则仍有效。旧版缺少 XS 命令时不猜命令，完整边界与卸载方式见 [INSTALL](../INSTALL.md#preserve-data-removal)。

## English checklist

Use the matching Release's named assets/checksums or an explicitly supplied fixed candidate through [INSTALL](../INSTALL.md). This walkthrough is not a claim of successful testing or a stable release.

The XS wheel/hash `create` route is a local candidate interface, not a public Alpha.7 update. Platform acceptance requires the named candidate's results. `TOOL_READY` supplies `data.cli_argv`: preserve every array element as `<cli>`, not one executable string. Give its full result and the project path to the authorized assistant, which uses that prefix for project doctor/guide checks and [first save](#first-save). `RUNTIME_READY` alone does not mean the tool is installed; `host_integrated=false` means no host was integrated. Do not repeat installation, create the public Alpha.7 environment or copy a legacy adapter. The first-save section retains the six-field draft: inspect with resume, initialize only genuinely absent storage with authorization, read the actual revision, checkpoint and read back. Only then preview a separately authorized host entry; preserve existing rules via reviewed integration or status/upgrade. Installation does not save a checkpoint, enable automatic saving or prove host loading or platform support.

1. If an XS project entry is already configured and the assistant can read its rules, select that project and provide its path; the entry carries the tool and guide bindings. Otherwise prepare three bindings: the absolute synthetic-project path, the matching Skill file's absolute path, and the entire executable prefix. A wheel prefix is `/absolute/tool-env/bin/glom-continuity` or that environment's Python with `-I -B -m glom_continuity`; Windows uses its absolute Scripts executable. Portable/source users supply the absolute script path with its interpreter. Public Alpha.7 has no setup command and uses the manual route.
2. XS candidate wheels return their bundled Skill path through doctor's `data.usage` after local manifest checks. `source_unsealed` only locates a source guide; `unavailable` requires reviewing its issue. Older packages without `usage` still need matching portable/source documentation. Keep the chosen executable; installation does not grant host permissions or load new chats automatically.
3. Ask an authorized assistant to save a planning checkpoint: budget 5000, 50 attendees, venue unknown, next step compare two venues, no payments or contacting vendors. Initialize only genuinely absent storage for this authorized first save. Record the actual project revision; initialization and a verbal promise are not saving.
4. Open a fresh conversation in the same project. With a configured, readable XS entry, supply only the project path; otherwise supply the three bindings. Ask for read-only recovery, not init/save/accept. Check the actual tool output, project ID, revision, budget, headcount, unknown venue and next step without pasting the old request. With no command/file access or an unread entry, recovery has not been demonstrated. Planning may return no_references; changed registered inputs require review. Next authorize a named output and check the artifact itself. Restoring records does not certify the resulting work or turn on automatic saving.
5. For an optional second assistant, both need the same local project. A creates a handoff; B checks, accepts and works. A bounded result can use return-work; A then reads receipt.result and the actual artifact. You deliver the instructions. Acceptance and result registration do not certify content quality.

Existing projects need no new init. Alpha.5 keeps status/check/context and ordinary checkpoint plus return-handoff workflows, without the newer capabilities. Follow INSTALL for a separate-environment upgrade and matching Skill.

To stop, follow [preserve-data removal](../INSTALL.md#preserve-data-removal) before uninstalling the tool: review status, explicitly pause with the current whole-file digest, read status again and inspect doctor for the selected host. Preserve original user rules, the paused template/block and project memory; never delete a shared file or hand-edit an embedded block. Check the operation outcome, not just `ok:true`; errors or unsupported operations require review, not deletion. Enable is optional later and needs a freshly reviewed paused-state digest.

To leave the project entry instead of keeping it paused, first check that the installed candidate's `entry --help` actually provides `detach`; public Alpha.7 and earlier candidates do not. Preview `entry detach --host <host>`, then, only with authorization and the reviewed current state/digest, apply it with `--apply --expect-state <active-or-paused> --expect-sha256 <digest>`. Require `state=detached` and `removal.outcome=move_observed` or `exchange_observed`, and inspect the resulting files. A standalone entry moves to a non-discovered backup; an embedded entry leaves current user text in place and retains the previous whole entry separately. An unknown or changed entry fails for review; do not retry or delete files to force success. A remaining ordinary user rule can later report `ENTRY_UNRECOGNIZED` because it no longer contains a managed block; do not overwrite it.

After verification remove only your Recaloom connection items, retain other configuration and check a fresh session. Neither pause nor detach uninstalls the package, removes project memory, stops tasks or revokes old context.

The base CLI has no third-party runtime dependencies or model calls; MCP is optional. A cloud assistant retains its own fees/privacy rules. No chat import, automatic cross-device sync or universal host compatibility is implied. Share redacted feedback only.
