# Recaloom：安装诊断与成果回存

适用于 `0.1.0.dev4` 源码/对应候选；不是已发布的 Alpha.5 功能，也不是正式版公告。旧版本继续按其帮助与工具列表操作。品牌变为 Recaloom · 续珞，仓库、Python包、CLI/MCP名称和 `.continuity/` 保持不变。

## 两件实际的事

一是知道自己调用了哪份工具。二是让接手方把产物明确存回这次交接。原助手不只看到“我接了”，还可以找到“我存了哪份文件、哪个版本，以及文件后来有没有变”。

本工具不负责生成文件或判断报告是否正确。产物回存也不等于发消息：仍需在原助手中恢复同一份项目，或把交接编号给它。

## 先认清安装

从已提供的工具目录运行：

```sh
python3 -B scripts/continuity.py --version
python3 -B scripts/continuity.py --help
python3 -B scripts/continuity.py --project /absolute/project doctor
```

Windows 可用 `py -3`；wheel 使用环境内 `glom-continuity` 的绝对命令前缀。MCP 先发现 `continuity_doctor`，再调用，不传项目参数。

诊断返回 `product_id`、`display_name`、`version`、`source_url`、程序路径/哈希及选定项目的存储状态。MCP另有 `write_tools_enabled`。它不扫描整机安装，不查密钥，不改数据库，也不替你修复。

- `ok:true` 只表示诊断已执行；继续检查 `storage.compatible`。
- `compatible_v1` 表示识别到兼容结构，不证明全部文件正常或厂商身份。
- `not_initialized` 表示还没有本工具的存储。只有用户要开始保存时才初始化。
- 陌生目录、坏库、不支持的版本或不安全链接会报告问题，不能把它们当空项目重建。

兼容注意：已有 `.continuity/` 但缺少数据库，从旧版的 `NOT_INITIALIZED` 改报 `UNRECOGNIZED_STORAGE`。这是刻意收紧，避免自动化把数据丢失误当首次安装；目录完全不存在才返回 `NOT_INITIALIZED`。旧错误处理若遇到新码，应停止并保留文件，不可自动重建。

这是程序自报与格式识别，**不是防伪签名**。攻击者可以伪造显示名；哈希要与可信来源的清单对照。程序路径可能包含本机用户名，向公开问题区粘贴前先遮去。

## 保存、接手、产出、回存

1. A 保存项目检查点，记录目标、限制、未知项和输入文件；创建给 B 的交接。
2. B 读状态、检查、领取；按原目标工作。收件标签只是本地合作标签，不是认证账号。
3. B 检查产物，准备六字段 JSON 草案（格式沿用[通用 Skill](../skills/project-continuity/SKILL.md)）。保留原约束/未知项；`evidence` 保留输入，新增实际存在的 `artifact`。比如 `plan.md`，不能只写“已完成”。
4. B 用本次交接编号和领取时的基础 revision 明确回存。
5. A 读取回执，恢复对应项目并查看实际文件，之后才进行业务验收。

假设领取基础版本是 1；`result.json` 已在项目内写好，引用的产物文件真实存在：

```sh
python3 -B scripts/continuity.py --project /absolute/project return-work --id HANDOFF_ID --recipient reviewer --from-file /absolute/project/result.json --expect-revision 1
python3 -B scripts/continuity.py --project /absolute/project receipt --id HANDOFF_ID
python3 -B scripts/continuity.py --project /absolute/project resume --max-chars 12000
```

MCP 对应 `continuity_return_work(id, recipient, from_file, expect_revision)`，仅启用 `--allow-writes` 时出现；相对 `from_file` 从绑定项目根解析。只读宿主不能绕过配置写入。

首次成功会把新检查点和交接关联写入同一个数据库事务。`result.state:saved` 包含产物路径、checkpoint ID、revision，以及查询时的引用检查。回执的交接 `state` 仍是 `accepted`，不新增“自动完成”的含义；`semantic_completion_verified:false` 始终保留。

已链接的产物还会沿明确的交接关系检查原基础检查点的引用，返回 `source_revisions_checked`。因此，即使新草案漏列原输入，原输入之后发生变化，回执与恢复也会提示复核；连续交接不会悄悄丢掉这条来源关系。这不是全文需求推理或全项目依赖图，只检查已登记、已关联的引用。单独保存一个普通检查点是显式选择新的记录范围，不自动关联所有历史任务；旧回执仍保留自己的来源检查。

## 失败、重复与版本

| 情况 | 实际行为 |
|---|---|
| 只接受了交接，没明确回存 | `result.state:not_recorded`；不排除普通检查点或尚未登记文件 |
| 原输入变了，即使新草案没列它 | 拒绝首次回存，要求先审阅 |
| 不是已领取交接，或标签不同 | 拒绝，不添加版本 |
| 其他人已保存新版本 | 拒绝旧基础版本，不自动覆盖 |
| 保存成功但回答丢了 | 先读回执；显式重发同一草案/哈希/基础版本可返回原记录，不多写一版 |
| 同一交接再次交不同内容 | `RETURN_CONFLICT`，原记录保留 |
| 产物后来变了或丢了 | 历史回存仍存在，引用检查提示 `needs_review` |
| 后续又保存了普通节点 | 历史回执可查；`resume` 只在当前 revision 本身有链接时带 `result` |

响应里的 `revision` 是回存版本，`current_revision` 是查询时项目最新版本；重发旧回存时两者可以不同。TTL 是领取截止时间，不是已领取任务的执行时限，已领取任务可在 TTL 后回存，但仍检查版本/引用。

目前这条路径是“一个基础检查点→一个明确结果”。要修改输入、分阶段保存或合并其他人的进展时，使用普通检查点记录变更并创建新交接；不能把旧编号强行套到新进展上。它不合并分支，不自动定位需求变化的全部下游影响，不检查约束是否在语义上全部保留。

## 数据兼容与备份

旧三张表及六字段草案不改；第一次成功 `return-work` 才添加可选 `handoff_results` 关联表，与新检查点一起提交。旧读者仍可读取原检查点，但不会展示新关联。没有第二套数据库，没有全局记忆迁移，不因改名清空数据。

备份在所有写进程停止后一起复制选定项目的 `.continuity/` **和被引用的文件**。数据库只保存文本与文件指纹，不备份产物原文；导出的审阅 JSON 不是恢复整个数据库的备份。不应把正在写入的数据库放进网盘同步来充当并发服务。

## English quick reference

Dev4 adds optional `doctor` / `continuity_doctor` and `return-work` / `continuity_return_work`. Discover them first; public Alpha.5 lacks these tools. Compatibility identifiers remain glom-continuity.

Doctor reports the invoked script/version/hash and selected project's recognized storage shape; it does not authenticate a publisher or prove artifacts healthy. A successful diagnosis may report incompatible storage. Preserve unknown or corrupt storage; never reinitialize it as a repair.

After accepting a handoff, create the requested artifact and a reviewed six-field draft. Return it with the handoff ID, receiver label, draft path and accepted base revision. The project must still be at that base; original references must be unchanged. At least one artifact is required. The checkpoint and its handoff link commit in one transaction. This does not verify semantics, send a message, launch a model or execute external actions.

Read `receipt.result`: `saved` identifies a linked revision and current reference checks; `not_recorded` does not rule out ordinary checkpoints or unregistered files. Checks follow explicit accepted-handoff source links as well as the result's own references, so omitting an original input does not hide its later changes. This is not a semantic dependency graph. Identical explicit replay returns the existing result; changed content conflicts. Always read a receipt after a lost response before doing more work. The result `revision` can differ from `current_revision`. Acceptance expiry is a claim deadline, not an execution deadline.

Input edits or intervening checkpoints need explicit reconciliation and a fresh handoff, not a forced old result link. An optional same-database table is added only on the first successful return; existing v1 fields remain readable. No automatic cross-device synchronization, project migration or identity authentication is provided. See [verification](verification.md) for tested scope rather than inferring support from these instructions.
