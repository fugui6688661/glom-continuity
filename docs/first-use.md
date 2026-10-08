# 第一次保存与接续 / First save and recovery

本卡对应 **Recaloom XS v0.2.0** 的基础 CLI。先用没有私人资料的虚构小项目，一位助手即可。下载以 `v0.2.0` 具名 Release 附件为准；若无附件，不用旧包冒充。团队固定包须由维护者明确提供并核对摘要。[安装](../INSTALL.md) · [English checklist](#english-checklist)

## 1. 准备两个位置

已按 README/INSTALL 安装成功就不要再安装。准备：

| 位置 | 来源 |
| --- | --- |
| 项目绝对路径 | **由你提供**的已有测试目录；不是用户主目录、工具环境或助手猜的 cwd |
| 工具 Python 绝对路径 | 安装最后一行的输出；macOS/Linux 为环境内 `bin/python`，Windows 为 `Scripts\python.exe` |

助手始终用这个 Python 加 `-I -B -m glom_continuity`。下文 `<cli>` 代表完整前缀，`<project>` 代表你选的绝对路径；尖括号是说明用占位符，不可原样运行。支持参数数组的工具逐项传参；shell 分别引用带空格的路径，PowerShell 用 `&` 调用解释器。

**wheel 已带匹配指南。** 助手先执行 `<cli> --project <project> doctor`，核对版本 `0.2.0`、程序路径/摘要和存储状态；仅在 `data.usage.state=available` 时读取 `data.usage.skill_path`。不用另下载 Skill，也不因指南所在目录改用另一份程序。`unavailable` 先检查 issues；`source_unsealed` 是源码布局定位，不是已校验 wheel。陌生、损坏或不兼容存储不能当空项目重建。

普通网页聊天如果没有本地文件与命令权限，不能完成这条路线；安装 CLI 不会替助手取得权限。

<a id="first-save"></a>

## 2. 复制给当前助手，授权首次保存

将两个方括号换成实际路径。以下是虚构练习，不要替换成密钥、公司资料或原始聊天：

~~~text
测试项目：[由我提供的已有测试目录绝对路径]
工具 Python：[安装最后一行输出的 Python 绝对路径]

请只用该 Python 加 -I -B -m glom_continuity。
先执行 doctor，核对版本 0.2.0、实际程序和项目存储；
data.usage.state=available 后读取 data.usage.skill_path 的匹配指南。

我授权在这个项目保存一次虚构规划：
准备一份活动安排，预算上限5000元，50个人，场地未定；
下一步比较两个候选场地；不得付款或联系商家。
先用 resume 只读检查。只有确实 not_initialized 才允许为本次保存初始化；
已有项目不再次 init，已有资料不覆盖，引用变化或错误先报告。
写入并读回一个新的六字段草稿，使用真实项目 ID/当前修订保存，再 resume 读回。
请报告项目 ID、修订号、限制、未决事项及实质下一步。
本次不配置宿主规则、不启用自动保存、不创建或领取交接。
~~~

“我记住了”不是保存结果；`init` 也只创建存储。应看到一次成功保存和随后的真实读回。

### 给执行助手的最小顺序

1. 用 `resume --max-chars 10000` 分流：`not_initialized` 且上述授权成立才 `init --name "活动安排试用"`；`no_checkpoint` 不再 init；`needs_review` 或其他错误先停下审阅。
2. 在项目内新建并读回 `first-checkpoint.json`，已有同名文件时不覆盖。草稿恰好六个字段：

~~~json
{
  "objective": "准备活动安排，预算上限5000元，50人，场地未定",
  "next_action": "比较两个候选场地",
  "constraints": ["不得付款或联系商家"],
  "decisions": [],
  "unresolved": ["场地未定"],
  "evidence": []
}
~~~

3. 从 `status` 取得项目 ID 和当前 `data.revision`，与已审阅的项目绑定一致后保存：

~~~text
<cli> --project <project> status
<cli> --project <project> checkpoint --from-file <project>/first-checkpoint.json --expect-revision <刚读取的revision> --expect-project-id <已核对的project_id>
<cli> --project <project> resume --expect-project-id <同一project_id> --max-chars 10000
~~~

每条命令退出 0、业务响应 `ok:true/code:OK` 且相应检查通过才继续。`REVISION_CONFLICT` 或 `PROJECT_MISMATCH` 要核对，不换 ID、自动刷新修订或盲重试。

本例没有文件证据，恢复为 `no_references` 是正常的规划状态，不表示产物验收通过。真实引用须是存在的项目内相对路径，用 `input` / `artifact`，指纹由工具计算。后续保存的 `next_action` 应描述项目剩余工作，不是“一直重复保存”。

## 3. 新开会话，只给位置

不要把上面的预算、人数和要求再贴一遍。在同一个项目开新会话，交给有本地权限的助手：

~~~text
项目：[同一项目的绝对路径]
工具 Python：[同一环境的 Python 绝对路径]

用该 Python 加 -I -B -m glom_continuity 执行 doctor，
核对匹配的随包指南并读取它，然后只读 resume。
告诉我上次保存的预算、人数、未确定事项、限制和下一步，
同时列出实际读到的项目 ID/修订。本次不初始化、不保存、不领取交接。
若程序、项目或引用不符，先报告，不从前一段聊天猜答案。
~~~

核对实际恢复输出应包含：**5000元、50人、场地未定、不得付款/联系商家、比较两个候选场地**，项目 ID 与前一步相同。然后才授权下一项工作，例如“写一份比较模板到新文件 `venue-comparison.md`，未知信息留空”；查看真实文件，不只看助手口头回答。

安装和这次手动保存都不意味着其他会话会自动加载，更不启用自动保存。恢复记录也不是业务任务完成证明。

## 4. 可选：以后少贴一次工具位置

首次保存后，用 `<cli> --project <project> setup` 取得只读绑定卡。卡里的 `doctor_argv`、`resume_argv` 是参数数组：保持项目绑定，先核对实际程序摘要、项目 ID 与指南，再恢复。卡片包含本机路径，只给获准访问该项目的人。

若希望宿主读取项目规则，另行授权并按 [INSTALL 的项目入口流程](../INSTALL.md#project-entry)选择一个宿主：

- 没有规则：先预览 `setup --host codex`，获准后才 `--write-instructions`。
- 已有个人规则：先预览 `entry integrate`，审阅完整合并内容和摘要，不覆盖原文件。
- 已有 Recaloom 入口：用 `entry status` 检查；升级用 `entry upgrade`，不再装第二份。
- Windows：使用手动绑定卡；安全自动写入/移动/交换未提供，不用手工剪改 managed block 模拟。

`codex` 可按所选宿主换成 `claude-code` 或 `workbuddy`。规则写入得到 `written_unverified`，不代表宿主读过。只有新会话真的读取该入口时，才可只给“继续这个项目：[绝对路径]”；若未加载，回到第3步的显式位置路线。自动事件保存是单独授权的可选接口，见[支持矩阵](../adapters/support-matrix.md)，不在本卡默认流程内。

## 卡住时

| 现象 | 最小处理 |
| --- | --- |
| wheel 404 / 命令仍显示旧版本 | v0.2.0 附件可能尚未发布；核对文件、摘要和环境，不拿 Alpha.7 顶替 |
| 找不到命令 / 没有本地权限 | 检查提供的完整 Python 路径和宿主工具权限；不要连续重装 |
| 随包指南 `unavailable` | 看 doctor 的 issues，保留环境，不借别处同名 Skill |
| `not_initialized` / `no_checkpoint` | 分别是未建存储/尚无保存；仅在首次保存授权下处理 |
| `needs_review` / 文件变化 | 先审阅变化，再决定是否保存新记录，不执行过时下一步 |
| `BUDGET_TOO_SMALL` | 增加响应字符预算，不删限制或未知项；字符不是 token |
| 损坏/不兼容存储或 I/O 错误 | 停止写入并保留数据，不删库、重建或自动修复 |
| 找到交接却没有产物 | 查 receipt 和真实文件；“已领取”不是“已完成” |

## 团队、旧版与停用

第二位助手可按[交接与成果回存](result-return.md)参与，但双方须访问同一项目；由你传递 handoff ID 和绑定，工具不启动模型、不自动跨电脑同步。单助手使用不需要 handoff。

已有项目不要重新 init；升级先停写备份、另装环境、核对同项目，再审阅入口绑定。历史 Alpha.7 wheel 没有随包指南或 XS setup/entry 命令，需其匹配文档；旧版按 [INSTALL 历史说明](../INSTALL.md#public-alpha7)使用，不照抄新增命令。

不用了，先按[安全停用/卸载](../INSTALL.md#preserve-data-removal)预览并暂停或解除识别到的入口，确认结果后再卸载。保留用户规则、`.continuity/`、草稿和原文件；不要删整个规则文件/目录，或手工剪除插件块。Windows 不支持的文件操作先报告，不能通过覆盖或删除绕过。

CLI 本身不调用模型或上传项目；云端助手有自己的隐私和收费规则。反馈只给版本、系统、宿主、失败步骤和错误码，[脱敏提交](https://github.com/fugui6688661/glom-continuity/issues/new?template=field_trial.yml)，不贴私人路径或原始聊天。

## English checklist

This is the first-use guide for **Recaloom XS v0.2.0**. Follow [installation](../INSTALL.md#wheel-install) once, using assets from the named Release; if they are absent, do not substitute an older package. A team trial may use a fixed package explicitly supplied by the maintainer with its digest verified.

### First save

Use an existing, non-sensitive test directory. You supply its **absolute path** and the **absolute environment Python path** printed at installation; the assistant must not guess either. The wheel includes the matching guide. Copy this prompt after replacing the two brackets:

~~~text
Test project: [the absolute path I provide]
Tool Python: [the absolute environment Python path printed at installation]

Use only that Python with -I -B -m glom_continuity. Run doctor for this project,
check version 0.2.0, runtime and storage, and read data.usage.skill_path only
when data.usage.state=available.

I authorize one synthetic planning checkpoint: plan an event for 50 attendees,
budget cap 5000, venue unknown, next step compare two venues.
Do not pay or contact vendors. First inspect with read-only resume.
Initialize only genuinely not_initialized storage for this save; never reinitialize
an existing project or overwrite data. Stop on changed references or errors.
Write and reread a new six-field draft, save against the reviewed project ID
and current revision, then resume and report the actual saved fields/identity.
Do not configure host rules, enable automatic saving or create/accept handoffs.
~~~

The six fields are `objective, next_action, constraints, decisions, unresolved, evidence`; use `evidence: []` for planning without files. The complete example and CLI order are in [first save](#first-save). Initialization or “I remembered it” is not a checkpoint. Verify a successful save followed by actual recovery; `no_references` means planning only, not verified artifacts.

### Fresh conversation

Do not paste the old requirements. Supply only the same two paths and this request:

~~~text
Project: [the same absolute project path]
Tool Python: [the same absolute environment Python path]

Use that Python with -I -B -m glom_continuity. Check doctor and read its matching
bundled guide, then run read-only resume. Report the saved budget, headcount,
unknowns, constraints, next step, project ID and revision.
Do not initialize, save or accept anything. Report mismatches instead of guessing.
~~~

Expect 5000, 50 attendees, venue unknown, no payment/vendor contact, and compare two venues. Check actual command output and the same project ID. Only then authorize a new artifact and review the file itself.

### Optional integration and lifecycle

A read-only `setup` card can carry runtime/guide/project bindings. Adding a project rule is a separate authorized step: preview new entries, use reviewed `entry integrate` for existing user rules, and `entry upgrade` for recognized old bindings. Windows uses the manual route; safe automated rule mutations are not provided. `written_unverified` does not prove loading. Test a fresh session before relying on a project-path-only prompt.

Installation does not enable all-host loading or automatic saving. Host pilots and platform limits are separated in the [support matrix](../adapters/support-matrix.md). Preserve the existing project during [upgrade](../INSTALL.md#upgrade-existing); [pause or detach safely](../INSTALL.md#preserve-data-removal) before uninstalling, retaining user rules and memory. Alpha.7 keeps its historical separate-guide route and lacks XS entry commands.

The local CLI needs no model account and makes no model calls. A cloud assistant has its own privacy and billing rules. Share only redacted failure metadata; never private project text, credentials or raw chats.
