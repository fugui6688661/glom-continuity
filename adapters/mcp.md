# MCP 接入

本地stdio适配层使用官方 Python MCP SDK 2.2.0。CLI仍只依赖Python标准库；只有MCP接入需要安装下述可选依赖。没有HTTP端口、云同步、账号服务或后台守护。支持MCP的客户端需要分别配置和验证，不代表所有Agent已经实接。

## 安装到你选择的工具目录

在已解压的工具目录运行；如果`.venv-mcp`已经存在，先确认它属于本工具，不要覆盖别人的环境。

```sh
python3 -m venv .venv-mcp
.venv-mcp/bin/python -m pip install -r requirements-mcp.txt
```

Windows使用`py -3 -m venv .venv-mcp`，Python路径为`.venv-mcp\Scripts\python.exe`。Windows安装说明尚需实机验证，不能将语法说明当作验收。

MCP客户端以如下命令启动服务；项目目录必须已经存在且由用户选定：

```sh
.venv-mcp/bin/python -B scripts/mcp_server.py --project /absolute/path/to/project
```

这是等待客户端消息的stdio服务，直接在终端启动后看似没有输出是正常的。不要把它当网页地址打开。默认只读，不自动初始化项目。首次追踪请显式运行CLI的`init`，或者在用户允许写项目状态时使用`--allow-writes`启动服务。

## 配置示例

支持`mcpServers`格式的客户端可在其指定配置位置合并以下条目。路径是占位符，必须替换成你的真实工具与项目绝对路径；不要直接覆盖现有配置。其他客户端可能使用不同格式。

```json
{
  "mcpServers": {
    "glom-continuity": {
      "command": "/absolute/path/to/tool/.venv-mcp/bin/python",
      "args": ["-B", "/absolute/path/to/tool/scripts/mcp_server.py", "--project", "/absolute/path/to/project"]
    }
  }
}
```

Codex使用TOML，不能直接粘贴上面的JSON：

```toml
[mcp_servers.continuity]
command = "/absolute/path/to/tool/.venv-mcp/bin/python"
args = ["-B", "/absolute/path/to/tool/scripts/mcp_server.py", "--project", "/absolute/path/to/project"]
startup_timeout_sec = 15
tool_timeout_sec = 15
```

配置作用范围和审批遵循[客户端官方MCP说明](https://learn.chatgpt.com/docs/extend/mcp)。本包不修改全局配置，不自动启用写操作。`--allow-writes`只增加下表五个项目状态工具，不授予浏览器、邮件、支付或部署权限，也不会覆盖宿主已有权限。

## 工具和边界

| 默认只读 | 显式加`--allow-writes`后增加 |
|---|---|
| `continuity_status` | `continuity_init` |
| `continuity_check` | `continuity_checkpoint` |
| `continuity_context` | `continuity_handoff` |
| `continuity_receipt` | `continuity_accept`、`continuity_export` |
| `continuity_resume`（dev3） | 不增加写工具 |

dev3 可优先使用 `continuity_resume(query="视频", max_chars=12000)`：在一次只读调用内分清尚未初始化、没有保存节点、需要复核、无文件引用的规划、已恢复记录，并返回适用习惯与待接交接。它不初始化、不保存、不领取交接、不执行任务。`restored` 仅表示记录已恢复，不表示成果验收通过。旧版未公布此工具时仍用 status → check → context，首次保存前不要调用 context。

命令语义和六字段草稿见[完整CLI合同](README.md)。MCP参数用下划线，例如`from_file`、`expect_revision`；项目在启动时绑定，工具调用不能指定其他项目。存储仍是同一个项目的`.continuity/`，不是MCP自己的第二套数据库。

`continuity_checkpoint.from_file` 必须指向普通 JSON 文件。相对路径始终从**绑定的项目根**解析，与客户端在哪里启动服务器无关；也接受该项目内的绝对路径。CLI仍按通常命令行规则解析相对草稿路径，跨入口时推荐明确的绝对路径。命名管道等非普通草稿会被拒绝；不会等待它们产生输入。未知额外参数当前可能被SDK忽略，不能用`project`等额外字段改变绑定项目；只发送工具schema公布的字段。

English: `from_file` is a regular JSON draft inside the bound project. Relative MCP paths start at that project's root, never the server's launch directory. Absolute paths must still be inside the project. The CLI retains ordinary cwd-relative argument semantics. Unknown extra arguments may be ignored by the SDK; they cannot change project binding.

读取结果要同时检查`isError`和完整`structuredContent`中的`ok/code/data`。业务错误保留CLI错误码，SDK对未知工具和无效结构还可能返回协议或工具错误，不得假定所有错误都有`structuredContent`。

`continuity_context.max_chars` 和 `continuity_resume.max_chars` 限制完整成功工具结果的字符数，包含文本、结构化内容两份表示及换行，不包括客户端负责的外层JSON-RPC封装。它与CLI stdout预算的边界不同；都不是模型token预算。无法容纳时返回`BUDGET_TOO_SMALL`，不悄悄截掉限制。错误反馈本身不受极小成功预算限制。

dev3 修正了保存容量与读取预算不一致：`max_chars` 接受严格正整数，不再额外限制为100万字符。默认仍为6000，不自动放大，也不按传入预算预分配内存。大预算可能把很长的正文交给宿主；优先缩短通用习惯、按任务登记和检索流程，仅在宿主可以容纳且用户范围允许时显式提高。它不绕过客户端自身的响应或上下文限制。

`resume` 的交接摘要保留原 `state: open`，另有读取时的 `claimability` 提示：`expired`、`stale`、`requires_reference_review` 或 `requires_explicit_accept`。这是避免误领的提示，不是权限；实际领取仍重查全部条件，旧 receipt 和数据库状态不被恢复操作修改。

开发版 dev2 的同一 `continuity_context` 另接受可选 `query`（最多2000字符），用于从当前 checkpoint 的 `memory` 角色文件中按字面关键词恢复习惯/流程。不增加工具数量，不自动学习，不绕过只读设置。详见[项目记忆](../docs/project-memory.md)。未登记记忆的旧项目保持原有 context 输出；Alpha.5 不支持此参数/角色，不要混用版本。

引用检查只证明检查时的文件状态，不证明内容正确。`needs_review`必须复核；`no_references`只能恢复无文件证据的规划。只读MCP服务器不是OS沙箱；同一系统用户仍是信任边界。

## 自测与撤回

```sh
.venv-mcp/bin/python -B -m unittest discover -s tests -v
```

没有安装可选依赖的Python会跳过MCP用例，不能把跳过说成通过。已有协议测试不是任意客户端的实接证明；真实测试范围见[验证记录](../docs/verification.md)。

停止客户端的此MCP连接，并只移除自己加入的那一条配置即可停用；其他服务器配置和项目文件保持不变。是否清理本工具虚拟环境另行决定。`.continuity/`里的项目记录不应因卸载适配器被删除。

实现依据：[官方SDK](https://github.com/modelcontextprotocol/python-sdk)、[客户端传输](https://py.sdk.modelcontextprotocol.io/client/transports/)、[工具](https://py.sdk.modelcontextprotocol.io/servers/tools/)。协议协商交由SDK处理，不能将SDK宣称的协议覆盖自动等同于本工具的客户端兼容成绩。
