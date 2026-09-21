# 把一次踩坑变成下次能用的方法

Recaloom 保存项目记录，不训练模型，也不会自动学会每次对话里的做法。这份说明面向希望持续改进自己工作流程的人，以及贡献通用修复的维护者。

下面的记忆流程适用于 **dev4 源码/对应候选**；公开下载的 **Alpha.5 不支持 memory 或 resume**。先按[安装说明](../INSTALL.md)确认实际工具版本，不覆盖旧项目。

## 在一个项目里留下有用的经验

例如：一次报告导出后发现表格小计不对。值得留下的是“检查原始数量、单价与小计的关系”，不是“所有报告都必须按这一次的版式做”。

1. **保留问题和适用条件。** 在项目内写一份简短记录：输入是什么、哪里失败、采用什么处理、如何核验，以及还没验证什么。使用虚构或已获准的数据，不复制私聊和密钥。
2. **先作为候选。** 按[项目记忆格式](project-memory.md)添加 `kind: workflow`、`status: candidate` 的条目，`when` 只写适用任务的关键词。原目标、约束和未决问题仍放在 checkpoint，不能让经验把它们挤掉。
3. **核对后再启用。** 用同一问题复现，并检查一个会让旧办法失效的反例。由当前用户确认是否在本项目采用，才改为 `active`。把核验记录单独登记为普通 `input` 引用；正文只保留足以改变下次行为的方法。
4. **保存并读回。** 通过当前 revision 保存新 checkpoint，再用新进程 `resume --query …` 查看选中/省略条目。检查点只登记引用哈希，不备份文件正文；需要保留旧证据时使用有版本的文件名。
5. **不适用就停用。** 新要求优先；过时方法改为 `retired`，临时方法设到期时间，重新保存并读回。停止推荐不等于擦除了历史备份。

`active` 表示作者选择启用，**不是工具认证这个方法正确**。`source` 文字也不是审批凭证。工具只检查登记文件是否变化；它不会理解测试记录、替用户批准规则或自动晋级候选。只有显式登记的核验文件才参与引用检查。

修改已登记文件而未保存新节点时，恢复会要求审阅；不应为了继续而删库重建。方法后来失败时保留失败事实，修订或停用，不把新失败从记录里抹掉。

## 哪些经验值得进入公共插件

一个本地习惯不一定应该成为所有用户的默认值。维护者先分清：

| 观察到的问题 | 合适的去处 |
|---|---|
| 本项目沟通、命名、交付习惯 | 项目记忆，由用户控制 |
| 可复现的恢复、交接或版本识别缺陷 | 最小合成案例 → 失败测试 → 修复与回归 |
| 用户不知道实际调用的是哪份安装 | 安装诊断、版本说明或客户端适配 |
| 工具本身没坏，只是模型没遵守约束 | 记录宿主、版本和行为；不要用协议测试声称已解决模型行为 |
| 私有产品的内部实现或客户材料 | 留在原项目，不进入公开包 |

更新 Skill 时只加能改变正确操作的规则，不把所有事故都堆成一份越来越长的提示词。新增功能按当前 `release-files.json` 审核，检查源码、包和用户安装三个版本是否一致；不要改写旧 release 的附件。

## 怎样给我们反馈

[问题反馈](https://github.com/fugui6688661/glom-continuity/issues/new?template=bug_report.yml)用于可复现错误；[试用记录](https://github.com/fugui6688661/glom-continuity/issues/new?template=field_trial.yml)用于分享成功、失败或卡住的一次使用。只需工具版本、宿主与系统、合成任务、预期保留的约束、实际结果和复现步骤。

不需要上传项目数据库、完整聊天、公司资料或原始 `doctor` 输出。诊断中有本机路径；先用占位符替换。缺少测量就写“未测”，不要把感觉填成节省 token 或耗时的百分比。

维护者用这些记录决定下一次修复：第一次能否装对、能否恢复目标和关键限制、是否需要重新解释、能否再次使用。仓库 Stars 反映关注度，不是可靠性或采用率证明。稳定版仍以[原发布条件](../PROVENANCE.md)为准。

## English summary

Project workflows are reviewed notes, not automatic learning. On dev4 source/candidates, keep an inferred workflow `candidate`; reproduce its failure and a counterexample with permitted data, then obtain the user's project-specific confirmation before marking it `active`. Register verification notes separately if their changes should block recall. Save against the current revision and read back through a fresh process. Retire outdated methods. Neither `active`, a source string nor a matching hash certifies semantic correctness.

Contribute minimal synthetic reproductions rather than private project exports. Use the field-trial form for successes and failures, with exact tool/host versions and measured or explicitly unknown outcomes. Source updates do not upgrade installed packages; the public Alpha.5 has no memory/resume support. No automatic uploads or telemetry are introduced by this guide.
