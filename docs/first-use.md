# 第一次使用 Recaloom

先试一个没有私人资料的小项目。一个助手就能保存和恢复，第二位助手是可选步骤。本页使用 alpha.6 预览版；安装以对应 Release 的具名附件及配套清单为准，步骤本身不代表实测通过。

## 1. 安装并确认三项位置

按[安装说明](../INSTALL.md)将工具装进新建的专用虚拟环境，不修改系统 Python。基础 CLI 无第三方运行时依赖、不调用模型，也不需要模型账号；[MCP](../adapters/mcp.md)可选。云端助手仍有自己的费用和隐私规则。

交给助手的三项位置要分清：

| 信息 | 应填写什么 |
| --- | --- |
| 项目 | 已有测试目录的绝对路径 |
| Skill | 与工具版本匹配的 `skills/project-continuity/SKILL.md` 的实际绝对路径 |
| 命令前缀 | wheel 用 `/absolute/tool-env/bin/glom-continuity`；便携版用 `python3 -B /absolute/tool/scripts/continuity.py` |

Windows wheel 使用环境内 `Scripts/glom-continuity.exe` 的绝对路径；也可用环境内 Python 加 `-B -m glom_continuity`。路径有空格时分别引用，不猜全局 PATH。

wheel 用户不一定有 `skills/` 或源码目录。先另外取得匹配版本的便携附件或固定源码，保留完整文档布局，找到 Skill 的绝对路径。Skill 可以在环境外，命令前缀仍指向所选 wheel 环境；不要因文档旁边有脚本就换用另一份程序。只有网页链接、缺失的相对路径或“工具目录”都不足以确定可执行文件。具体方式见 INSTALL。

已装过的用户先核对现有 `--version` 和 `--help`，不要覆盖环境或重建项目。alpha.6 应显示 `0.1.0-alpha.6`，帮助包含 `resume`、`doctor`、`return-work`。版本不符先停下来检查路径。

## 2. 让当前助手保存一次

把下面的话交给有本地文件和命令权限的助手，替换三项括号。不要把 API key、公司资料或原始聊天放进试用。

> Skill：[匹配版本 Skill 文件的绝对路径]。命令前缀：[完整可执行命令前缀]。测试项目：[已有测试目录的绝对路径]。先读 Skill，核对版本和帮助，再只读检查项目状态。请保存：准备一份活动安排，预算上限5000元、50个人、场地未定；下一步比较两个候选场地。不得付款或联系商家。只有确实未初始化且为了本次首次保存，才允许初始化；已有项目不要再次 init。保存后告诉我项目、修订号、保存的限制和未确认事项，异常时先说明。

看到实际保存结果才算完成这一步。`init` 只创建存储，助手回答“记住了”不能代替保存。这个例子只有规划文字，没有引用文件，恢复状态可以是 `no_references`。

## 3. 新开会话，只给位置

不要复制上一段活动要求。在同一个助手的新会话中说：

> Skill：[同一匹配 Skill 的绝对路径]。命令前缀：[同一可执行命令前缀]。测试项目：[同一项目绝对路径]。先读 Skill，确认工具可用，然后只读恢复；不要初始化、保存或自动领取交接。告诉我预算、人数、尚未确定的事和下一步，并说明用了哪个项目的哪一版记录。

检查它是否读回5000元、50人、场地未定和比较两个候选场地。助手没有工具或项目权限时，这一步没有成功；不能把模型猜对当成恢复成功。确认有 `resume` 后可用它恢复，安装不会让所有新会话自动加载项目。

要检查文件变化，可在这个测试项目登记一份虚构输入，保存并创建交接，然后修改这份测试输入。旧交接应因引用变化被拒绝，助手应说明需要审阅。不要修改真实工作文件做演示。

## 4. 需要第二位助手时

两位助手都要能访问同一份本地项目。给 B 同样的三项位置和本次 handoff ID；聊天链接不会共享文件，也没有跨电脑自动同步。

A 保存 checkpoint 并创建 handoff。B 检查、领取，再读回目标和限制后工作。单阶段任务可按[成果回存](result-return.md)用 `return-work` 关联原交接和真实产物；A 查询原交接的 `receipt.result`，再查看实际文件。输入或基础版本已变化时，先解决冲突，不能硬套旧交接。

由你把接手或回传指令送到另一位助手，工具不会自动唤醒它。领取表示接上交接，回存表示有登记结果可看，内容是否合格仍须核查。单助手保存不需要这些步骤。

## 卡住了，先分清是哪一步

| 现象 | 怎么处理 |
| --- | --- |
| 找不到命令或 MCP 工具 | 核对可执行前缀、版本和当前会话的工具列表；不要连续重装 |
| wheel 环境里没有 Skill | 取得匹配的文档布局，填写 Skill 的实际绝对路径；不猜脚本位置 |
| `NO_CHECKPOINT` | 存储存在但尚未保存记录；经授权保存首个节点，不重新 init |
| MCP 只有读取工具 | 默认如此；获准保存时才为这一条连接显式启用写权限 |
| `BUDGET_TOO_SMALL` | 增加响应字符预算，保留限制和未知项；字符数不是 token 数 |
| 文件变化或 `needs_review` | 审阅后再保存新版本，不沿用旧交接假装成功 |
| 陌生、损坏或不兼容存储 | 保留数据并停止，不删除数据库或重新初始化来“修复” |
| 找不到接手成果 | 查当前 checkpoint/回执并核对实际文件；“已领取”不表示交付完成 |

反馈只提供版本、系统、助手名称、失败步骤和错误码。[提交脱敏试用反馈](https://github.com/fugui6688661/glom-continuity/issues/new?template=field_trial.yml)。本卡不新增宿主兼容或模型效果结论，实测范围见[验证记录](verification.md)。

## 已有项目与旧版迁移

已有项目保留原路径和 `.continuity/`，先停写备份，再按 INSTALL 升级工具和匹配 Skill，不重复 init。旧 alpha.5 仍按 `status` 分流，有节点才 `check`、`context`；它没有记忆/query、resume、doctor 或 return-work。旧版双助手回传仍可保存普通 checkpoint，再创建给 A 的返程 handoff。这些旧功能不会因改名或更新文档而升级。

## English checklist

Use the alpha.6 preview and the matching Release's named assets/checksums through [INSTALL](../INSTALL.md). This walkthrough is not a claim of successful testing or a stable release.

1. Prepare three bindings: the absolute synthetic-project path, the matching Skill file's absolute path, and the entire executable prefix. A wheel prefix is `/absolute/tool-env/bin/glom-continuity` or that environment's Python with `-B -m glom_continuity`; Windows uses its absolute Scripts executable. Portable/source users supply the absolute script path with its interpreter.
2. A wheel need not contain skills or source scripts. Obtain matching portable/source documentation separately and keep its layout for the Skill's relative references. Keep using the chosen wheel executable even if the Skill lives elsewhere. Verify version/help before work; installation does not grant host permissions or load every new chat automatically.
3. Ask an authorized assistant to save a planning checkpoint: budget 5000, 50 attendees, venue unknown, next step compare two venues, no payments or contacting vendors. Initialize only genuinely absent storage for this authorized first save. Record the actual project revision; initialization and a verbal promise are not saving.
4. Open a fresh conversation. Supply only the three bindings and ask for read-only recovery, not init/save/accept. Check the budget, headcount, unknown venue and next step against the recorded project without pasting the old request. With no command/file access, recovery has not been demonstrated. Planning may return no_references; changed registered inputs require review.
5. For an optional second assistant, both need the same local project. A creates a handoff; B checks, accepts and works. A bounded result can use return-work; A then reads receipt.result and the actual artifact. You deliver the instructions. Acceptance and result registration do not certify content quality.

Existing projects need no new init. Alpha.5 keeps status/check/context and ordinary checkpoint plus return-handoff workflows, without the newer capabilities. Follow INSTALL for a separate-environment upgrade and matching Skill.

The base CLI has no third-party runtime dependencies or model calls; MCP is optional. A cloud assistant retains its own fees/privacy rules. No chat import, automatic cross-device sync or universal host compatibility is implied. Share redacted feedback only.
