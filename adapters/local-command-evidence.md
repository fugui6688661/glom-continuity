# 本机只读命令证据

日期：2026-09-12。以下按核查轮次保留执行记录；九命令同步见第 8 节，前面的五/七命令是历史快照，不是模拟两助手日志。公开安装文件的元数据/代码可读；未打开账号配置、token 文件、环境变量值或原生会话数据库，未操作 App UI、重启进程或运行第三方仓库。

可移植性说明：原始本地核查已实际执行；本文命令现为**脱敏展示**，将个人主目录表示为 `<HOME>`，当时的 Continuity 工具工程根表示为 `<TOOL_ROOT>`。它们是文档占位符，不是环境变量，也不是已替用户选定的安装路径。不要直接照抄执行；复核者须另行明确自己的路径。保留应用安装位置和 macOS 命令是为了标明原核查平台，不宣称这些位置在其他电脑上相同。

## 1. 只读探测保护

版本、帮助及 Continuity 的只读错误路径用如下 macOS 外层沙箱运行。它禁止写文件、禁止网络，并拒绝读取列出的原生私有目录；不是依靠模型遵守只读口头约束。

```sh
/usr/bin/sandbox-exec -p '(version 1) (allow default) (deny file-write*) (deny network*) (deny file-read-data (subpath "<HOME>/.codex") (subpath "<HOME>/.dsh") (subpath "<HOME>/.ssh"))' <下表中的程序及参数>
```

上面的 `<下表中的程序及参数>` 是说明占位符，不是可直接执行的命令。以下各命令均加此前缀；不执行任何模型任务。

## 2. Codex

```sh
/Applications/ChatGPT.app/Contents/Resources/codex --version
/Applications/ChatGPT.app/Contents/Resources/codex --help
/Applications/ChatGPT.app/Contents/Resources/codex exec --help
```

- 三条退出码均为 `0`；版本输出：`codex-cli 0.153.4`。
- 都出现警告：`WARNING: proceeding, even though we could not create PATH aliases: Operation not permitted (os error 1)`。这是沙箱阻止启动器写 PATH 别名；未放宽保护重跑。
- 顶层帮助：`Usage: codex [OPTIONS] [PROMPT]` 与 `codex [OPTIONS] <COMMAND> [ARGS]`；列有 `exec`、`resume`、`mcp` 等，`-C, --cd <DIR>` 指定工作根。
- `exec --help` 明确列 `--json`（事件 JSONL）、`--ephemeral`（不保存会话文件）、`--ignore-user-config`（仍使用 `CODEX_HOME` 的认证）。这些只是帮助实核，没有执行 `exec` 任务，也没读取对应环境变量。

```sh
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' /Applications/ChatGPT.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' /Applications/ChatGPT.app/Contents/Info.plist
```

分别输出 `26.903.71938`、`8576`，退出码 `0`。这两个是桌面包元数据，不是模型名称或 CLI 版本。

## 3. DSH / Harness

```sh
'/Applications/DSH Desktop.app/Contents/Resources/runtime/bin/node' '/Applications/DSH Desktop.app/Contents/Resources/dsh/0.1.0-rc.6/node_modules/@deepseek-ai/dsh/lib/bin.js' --version
'/Applications/DSH Desktop.app/Contents/Resources/runtime/bin/node' '/Applications/DSH Desktop.app/Contents/Resources/dsh/0.1.0-rc.6/node_modules/@deepseek-ai/dsh/lib/bin.js' --help
```

两条退出码均为 `0`；版本输出 `0.1.0-rc.6`。帮助摘录：

```text
Usage: dsh [options] [command] [args...]
--profile <name>
--patch <path>
--dump-config
--dump-default-config
web [options] [args...]
plugin [options] [args...]
```

未运行以上 profile、web、plugin、dump 模式。入口代码 `lib/bin.js` 显示顶层帮助/版本在解析时退出，正常 profile 分支之后才调用 `loadLayeredEnv("dsh")`。

只读 `cat`/`sed`/`rg` 核对了以下随包文件（不是用户配置）：

| 文件（相对 `/Applications/DSH Desktop.app/Contents/Resources/`） | 结果 |
|---|---|
| `dsh/0.1.0-rc.6/package.json` | `dsh-desktop-bundled-dsh` 外层壳包自身为 `0.0.0`，依赖 `@deepseek-ai/dsh: 0.1.0-rc.6`；不拿壳包版本冒充 CLI |
| `dsh/0.1.0-rc.6/node_modules/@deepseek-ai/dsh/package.json` | 包名 `@deepseek-ai/dsh`，版本 `0.1.0-rc.6`，bin 为 `lib/bin.js`，repository 指向官方 deepseek-ai/deepseek-harness |
| 同包 `README.md` 与 `lib/bin.js` | profile 入口和顶层帮助的区分；headless 是持久化模型会话 |
| `dsh/0.1.0-rc.6/node_modules/@deepseek-ai/dsh-skill-filesystem/package.json` | skill provider 同为 `0.1.0-rc.6` |
| 同 provider `lib/index.js` 行 150–165、799–805 | `.dsh/skills` 与 `.agents/skills`；最近 `.git` 祖先，无 `.git` 用 cwd |
| `runtime-bin/dsh` | 包内启动包装器依赖两个 DSH_DESKTOP 参数变量；未读取它们的值，也未运行该包装器，改用明确的内置 Node 和入口绝对路径 |

```sh
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' '/Applications/DSH Desktop.app/Contents/Info.plist'
/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' '/Applications/DSH Desktop.app/Contents/Info.plist'
```

均输出 `0.2.6`，退出码 `0`。不据此推断活动 App 的 runtime、profile、工具权限或模型可用性。

## 4. PATH 与 Python

`command -v codex`、`command -v dsh`、`command -v harness` 均未命中。`command -v python3` 返回 `/opt/homebrew/bin/python3`；`python3 --version` 返回 `Python 3.14.6`。

入口是通过安装目录和仅含可执行文件路径的进程清单定位的，没有读取进程参数或环境，也没有对活动进程发命令。未向 shell PATH 添加任何目录。

## 5. Continuity 早期快照（已被后续七命令帮助更新）

以下也加第 1 节的外层沙箱。`-B` 避免 Python 生成字节码。此探测只用未初始化的本工具目录检查错误返回，不等于为用户选定或安装了项目。

```sh
/opt/homebrew/bin/python3 -B "<TOOL_ROOT>/scripts/continuity.py" --help
/opt/homebrew/bin/python3 -B "<TOOL_ROOT>/scripts/continuity.py" --project "<TOOL_ROOT>" status
```

首次探测的帮助退出 `0`，列出 `{init,status,check,context,checkpoint}`；当时 `handoff`/`accept` 尚未出现。随后 `status` 退出 `2`，原文：

```json
{"code":"NOT_INITIALIZED","error":"Initialize this project first","ok":false}
```

该快照错误 JSON 缺少约定的 `data` 字段，不能补造字段当作已通过。探测前代码 SHA-256：`f57f3b8263ec3d16c0f3aad0167e1822471a488dfc3a37eafc3741abee4a5b97`；主线程并行开发中，此哈希仅标记当时文件观察点，不保证随后每条命令执行期间代码完全不变。后续复核如下。

本轮没有执行 `init/checkpoint/handoff/accept` 的业务操作，只查它们的 `--help`；没有通过终端制造项目状态或测试写入。既有项目状态的完整成功路径、并发、交接领取和模型调用不在这份命令证据的通过范围内。

## 6. 历史：七命令接口实核

同样使用第 1 节外层沙箱；程序与项目路径同第 5 节。逐条运行 `python3 -B <项目自有CLI> --project <本工具目录> <下表子命令> --help`：

| 子命令 | 本机帮助显示的参数 | 退出码 |
|---|---|---|
| `init` | `--name NAME` | 0 |
| `status` | 无业务参数 | 0 |
| `check` | 无业务参数 | 0 |
| `checkpoint` | `--from-file FROM_FILE --expect-revision EXPECT_REVISION` | 0 |
| `context` | `[--max-chars MAX_CHARS]` | 0 |
| `handoff` | `--recipient RECIPIENT --expect-revision EXPECT_REVISION [--ttl-seconds TTL_SECONDS]` | 0 |
| `accept` | `--id ID --recipient RECIPIENT` | 0 |

顶层帮助已显示 `{init,status,check,context,checkpoint,handoff,accept}`，不再将早期缺命令视为当前阻塞。`handoff --help` 对 recipient 的原文说明是 `Cooperative label, not authentication`。

只读源码回读确认默认 TTL 为 3600 秒、`context.data.text` 为恢复正文，预算检查针对完整 JSON stdout 并计入换行；`handoff` 返回 `data.handoff_id`，`accept` 没有 `--expect-revision` 参数。上述是帮助/源码证据，不是写操作行为验收。

更新模板后再次执行第 5 节的 `status` 探测，退出码仍为 `2`，返回仍是 `{"code":"NOT_INITIALIZED","error":"Initialize this project first","ok":false}`；错误缺 `data` 的问题尚未得到修复证据。较晚源码读取点 SHA-256：`1b064509d518c90dc420ad3aaeee9f99b1483ce64e328215d55ff9986c7308a6`，同样不把并行开发中的读取点冒充冻结发行版。

## 7. 历史：七命令材料静态校验

尝试用 `skill-creator/scripts/quick_validate.py` 校验两模板；本机 Python 与随包 Python 都缺 `yaml`，错误为 `ModuleNotFoundError: No module named 'yaml'`。未安装依赖、未把此校验器记为通过。

改用系统 `/usr/bin/ruby -ryaml -rjson -rpathname -e ... <本工具目录>` 进行只读结构检查，退出 `0`：两模板 YAML frontmatter 的 name/description 和目录匹配；安装绑定严格为未启用及两个待选择路径；七命令列表精确匹配确认接口；README 的草稿 JSON 恰好六字段、数组/role/相对路径类型合格；六个 Markdown 文件的本地链接存在且不越出本工具目录、代码围栏闭合。输出：

```text
PASS frontmatter, disabled binding, command contract: adapters/codex/continuity-codex/SKILL.md
PASS frontmatter, disabled binding, command contract: adapters/harness/continuity-harness/SKILL.md
PASS exact draft JSON shape (example only, not evidence-file existence)
PASS Markdown fences and local links: 6 files
```

这不是客户端发现测试、不是安装撤回测试，也不是模型行为测试；示例 evidence 路径没有被伪装为已经存在的用户文件。

## 8. 当前：九命令与无引用语义同步

继续使用第 1 节外层沙箱（禁止写盘、联网及读取原生私有目录）和 `python3 -B`，逐一运行原七命令与新增两命令的 `--help`，九项退出码均为 `0`。新增命令实参如下，执行时仍加外层沙箱前缀：

```sh
/opt/homebrew/bin/python3 -B "<TOOL_ROOT>/scripts/continuity.py" --project "<TOOL_ROOT>" receipt --help
/opt/homebrew/bin/python3 -B "<TOOL_ROOT>/scripts/continuity.py" --project "<TOOL_ROOT>" export --help
```

帮助原文：`usage: continuity.py receipt [-h] --id ID`；`usage: continuity.py export [-h] --output OUTPUT`，output 说明为 `New JSON filename in project root`。

只读源码核对（非业务回放）：

- `check_references` 在有检查点但 evidence 为空时返回 `no_references`、空 issues、`semantic_completion_verified: false`；context 内复用此检查。模板据用户指定语义允许明确缺证的纯规划继续，不把它当作产物通过。
- receipt 分支只查记录并返回 project_id、state、accepted_at 等，附 `external_actions_verified: false`、`recipient_is_authentication: false`。代码也可返回 open 记录，因此模板必须确认 accepted 状态，不从 `ok: true` 推断接受成功。
- export 分支限制简单项目根文件名，使用 `O_CREAT | O_EXCL` 新建，存在则 `OUTPUT_EXISTS`；review 包保留检查点与引用元数据/check 标记，没有原始 evidence 文件正文，`grants_permission: false`。本成员没有执行 export 写操作，也没有创建状态去测试 receipt 成功路径。

该轮源码读取点 SHA-256 为 `3338941b08c4a788a2367e725558470b6da2ca8bb20b561c36a9b53d10f2321c`，不等同并行开发中的冻结发行版。同轮重跑第 5 节 status 只读错误路径，退出 `2`，仍返回 `{"code":"NOT_INITIALIZED","error":"Initialize this project first","ok":false}`，尚缺 data；该反例仍交主线程处理。

主线程已说明会独立做干净项目 CLI 协议回放。这里不预填回放成绩，不称 DSH 模型实接；模板未安装边界不变。

## 9. 追加：失败 envelope 修复实核与材料复核

主线程更新后，在同一禁止写盘/联网沙箱中重跑第 5 节的 status 只读错误路径，退出码为 `2`，原文现为：

```json
{"code":"NOT_INITIALIZED","data":null,"error":"Initialize this project first","ok":false}
```

因此此前“NOT_INITIALIZED 缺 data”的**这一已测反例**已修复；历史失败输出保留，不抹去也不再作为最新阻塞。只读源码显示 Fault 与通用 IO_ERROR 分支均补 data:null，但本轮仅实测上述错误路径，不替主线程宣称全部失败分支回归通过。

系统 Ruby 的只读材料校验已重新检查两份模板的 YAML/禁用绑定、九命令列表和示例 draft JSON，并核对六个 Markdown 文件的本地链接及围栏，退出 `0`。该检查不运行模型、不写状态、不模拟 receipt/export 成功。个人路径脱敏只改变展示，不改变既有命令结果或版本支持边界。
