# 资料变了，怎样接着做

XS 开发中的新接口。先通过 `--help` 或 MCP 工具发现确认当前安装包是否包含 `review`；已发布的 Alpha.7 没有这个命令。它不自动修改项目或重做成果。

```sh
glom-continuity --project /absolute/project review
```

支持 MCP 的助手可调用 `continuity_review`。默认连接仍然只读，不必开启写权限。接口与品牌无关；具备已授权 CLI 或 MCP 通道的助手可以调用，但工具存在不代表每个宿主已自动绑定。

例如项目有两份引用：任务简报变了，报告文件没变。结果会列出：

| 文件 | 检查结果 | 接下来怎样处理 |
|---|---|---|
| 简报 | `changed` | 复核改了哪些要求，检查相关结论 |
| 报告 | `unchanged` | 保留文件；是否仍满足新要求需另查，不能直接算通过 |

`missing` 是文件缺失；`unavailable` 是路径不安全、文件过大、读取失败或读取过程中发生变化。原始问题码保留，不能一律当文件不存在。每项带有原记录与本次读取的摘要、字节数、角色和来源版本，不包含文件正文。

交接回来的一份成果可能省略原输入；`review` 仍会顺着已记录的交接关系检查原输入，避免只看成果文件就误以为可以继续。普通检查点没有逐条结论的依赖图，因此 `impact_status` 为 `not_inferred`：这是复核线索，不是自动因果分析。

## 建议的实际流程

1. 调用 `review`，先确认项目和当前版本。自动化客户端可传 `--expect-project-id`，项目不符时不返回引用信息。
2. 在获准范围内查看变更的资料，判断哪些决定和成果受影响，保留不受影响的工作。不要只改哈希来消除提醒。
3. 更新目标、限制、未决项和下一步，核对真实文件后，再按当前 revision 保存一个新 checkpoint。工具不会自动批准这一步。
4. 需要交给下一位助手时，再创建新交接。旧交接仍受引用与版本校验，不因运行 review 而被领取或放行。

返回的 `next_steps` 是固定的处理类别，不是历史内容生成的新授权。字节相同不证明内容正确、文件未改不证明需求未改。检查结果只代表读取时刻；后续写入、交接与执行必须重新校验。

`--max-chars` / MCP `max_chars` 限制完整成功结果。预算太小时返回 `BUDGET_TOO_SMALL`，不会只返回部分变化并假装检查完整。CLI 默认 12000 字符；MCP 还计入两种结果表示，必要时提高预算。字符不是 token。

## Privacy and compatibility

`review` is read-only. It does not initialize storage, run a model, upload files, accept a handoff or edit a checkpoint. File names, fingerprints and sizes can still be sensitive; review them before sharing. It checks current and explicitly linked source references, not unregistered files or every historic decision. `unchanged` describes bytes only, never semantic validity or execution permission.

The existing schema and CLI identifiers remain compatible. Old saved text is not silently rewritten. New checkpoints reject C0/DEL/C1 control characters while preserving newline, tab, normal Unicode and emoji. Concurrent initialization preserves the winning storage and returns `ALREADY_INITIALIZED`; other disk errors remain errors. Do not delete an unfamiliar `.continuity` directory to make initialization succeed.

Read-only inspection now refuses externally enabled WAL or surviving WAL/shared-memory sidecars with `READONLY_WAL_UNSUPPORTED` before opening SQLite. SQL `mode=ro` alone can still modify shared memory. The default rollback-journal storage is unchanged. Preserve all storage files and stop writers for separate recovery review; this is not an instruction to delete sidecars, silently convert journal mode, or retry writable. `doctor` reports the same reason inside `storage`, retaining its diagnostic response contract. This preflight does not defend against a malicious same-user process changing the filesystem concurrently.
