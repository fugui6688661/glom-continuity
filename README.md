# Recaloom XS · 续珞

**换一个会话，也能从项目上次保存的位置继续。**

Recaloom XS 是面向个人与工程团队的本地 CLI：保存经确认的目标、限制、决定和下一步，让有项目访问权限的 AI 助手在新会话中读回。引用文件变了，就先审阅变化。一个助手即可使用，不需要 Harness 或 MCP。

> **本页对应 XS v0.2.0。** 下载以该具名 Release 附件为准；若无附件，不要用旧包冒充。稳定产品范围是项目级 CLI 保存与恢复；宿主自动加载、事件保存等可选能力按[支持矩阵](adapters/support-matrix.md)分别看待。

[安装详情](INSTALL.md) · [第一次保存与接续](docs/first-use.md) · [English](README.en.md)

## 安装

需要 **Python 3.10+（含 venv / pip）**，以及允许读写所选项目的本地终端或助手。以下在工具存放目录运行，使用新的专用环境，不改系统 Python。每步失败就停止；旧安装走[升级流程](INSTALL.md#upgrade-existing)。

### macOS / Linux

确认 [v0.2.0 Release](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.2.0) 已有对应 wheel 附件后运行：

~~~sh
(
  set -eu
  if [ -e .recaloom-xs-0.2.0 ] || [ -L .recaloom-xs-0.2.0 ]; then
    echo "Environment exists; follow the upgrade guide." >&2
    exit 1
  fi
  python3 -m venv .recaloom-xs-0.2.0
  .recaloom-xs-0.2.0/bin/python -I -m pip install --no-index --no-deps "https://github.com/fugui6688661/glom-continuity/releases/download/v0.2.0/glom_continuity-0.2.0-py3-none-any.whl"
  .recaloom-xs-0.2.0/bin/python -I -B -m glom_continuity --version
  .recaloom-xs-0.2.0/bin/python -I -c "import sys; print(sys.executable)"
)
~~~

### Windows PowerShell

确认该 Release 已有对应 wheel 附件后运行；无需激活脚本、管理员权限或修改执行策略：

~~~powershell
if (Test-Path -LiteralPath ".recaloom-xs-0.2.0") { throw "Environment exists; follow the upgrade guide." }
py -3 -m venv .recaloom-xs-0.2.0
if ($LASTEXITCODE -ne 0) { throw "Environment creation failed." }
& ".\.recaloom-xs-0.2.0\Scripts\python.exe" -I -m pip install --no-index --no-deps "https://github.com/fugui6688661/glom-continuity/releases/download/v0.2.0/glom_continuity-0.2.0-py3-none-any.whl"
if ($LASTEXITCODE -ne 0) { throw "Installation failed; preserve the environment for diagnosis." }
& ".\.recaloom-xs-0.2.0\Scripts\python.exe" -I -B -m glom_continuity --version
if ($LASTEXITCODE -ne 0) { throw "Version check failed." }
& ".\.recaloom-xs-0.2.0\Scripts\python.exe" -I -c "import sys; print(sys.executable)"
~~~

版本应为 `0.2.0`；保留最后一行的 **Python 绝对路径**，下一步交给助手。附件尚未发布或不可用时不要改装旧包完成新版教程；已有维护者提供的固定 wheel 可按[本地安装及 SHA-256 核对](INSTALL.md#wheel-install)试用。

Windows 可用基础安装与 CLI；项目规则的安全自动写入、移动/交换未提供，受管 Harness 和完整进程树清理也不在 Windows 支持承诺内。详见[平台范围](adapters/support-matrix.md)。

## 复制给你的助手

`v0.2.0` wheel **已包含匹配的 Skill 与指南**，不必另找一份。把下段两个方括号换成实际绝对路径，再交给有本地文件和命令权限的助手：

~~~text
项目：[由我提供的项目绝对路径；不要猜当前目录或扫描其他项目]
工具 Python：[安装命令最后一行输出的 Python 绝对路径]

请始终用这个 Python 加 -I -B -m glom_continuity 调用工具。
先运行 --project <上述项目> doctor，核对版本 0.2.0、程序和存储状态。
仅在 data.usage.state=available 时，读取 data.usage.skill_path 指向的随包指南。
然后只读 resume，报告保存的目标、限制、未决事项、下一步及项目 ID/修订。
尚未初始化或没有保存记录时说明情况；本次不初始化、不保存、不领取交接，
不覆盖项目规则，不换程序或删除数据库来修复错误。
~~~

这是检查与恢复入口。**第一次还没有记录？** 按[首次使用卡](docs/first-use.md#first-save)授权保存一个虚构小项目，再开新会话只给位置，核对是否真的读回。安装工具不等于所有宿主自动加载，也不开启自动保存。

## 日常能做什么

- **保存 / 恢复**：`checkpoint` 保存经审阅的进度，`resume` 读回并检查引用。
- **项目习惯与方法**：[项目记忆](docs/project-memory.md)记录已确认偏好，按关键词选择；不会导入私人聊天或训练模型。
- **团队交接**：`handoff` / `accept` / `receipt` 登记交接，[return-work](docs/result-return.md)关联真实产物。双方须获准访问同一份项目，由你传递指令；不是跨电脑自动同步或模型调度。
- **减少重复粘贴**：保存首个节点后，可审阅 `setup` 生成的绑定卡，或[接入所选宿主的项目规则](INSTALL.md#project-entry)。已有规则先预览合并，不覆盖用户内容。

MCP、Harness 与事件保存是[可选接入](INSTALL.md#optional-hosts)，不是基础安装步骤。具体宿主、版本、系统和未验项见[支持矩阵](adapters/support-matrix.md)与[验证记录](docs/verification.md)；不将试点能力当作所有平台通用功能。

## 数据、费用与停用

基础 CLI 无第三方运行时依赖，不调用模型、不上传项目内容，不需要模型账号。安装下载会联网；可选 MCP 另装 SDK。云端助手读到的上下文仍受其服务的隐私和计费规则约束。

记录在项目的 `.continuity/state.sqlite3`，原文件留在原处。不要放入密钥或未经允许的私人资料；草稿、导出和规则绑定也可能敏感。备份前停写，连同整个 `.continuity/` 和引用文件一起保留，不并发网盘同步正在写入的数据库。

[升级](INSTALL.md#upgrade-existing)保留项目与旧工具；[停用/卸载](INSTALL.md#preserve-data-removal)先核验入口，再卸载专用环境里的包，保留用户规则和项目记忆。不要删除整个 `AGENTS.md`、规则目录或数据库。

## 旧版与验证边界

Recaloom 的仓库、包、命令及存储兼容名称仍为 `glom-continuity`。已有项目不要再次 `init`。历史 [Alpha.7](INSTALL.md#public-alpha7) 保留原功能和附件，但没有 XS 的随包指南与项目入口命令；更新网页不会升级旧安装。

文件指纹相符不等于内容正确；恢复、领取和回存都不能代替任务验收。没有外部真人首用、token 节省或优于竞品的普遍结论，也不提供加密存储、身份认证、远端 HTTP 或全平台自动记忆保证。[安全边界](SECURITY.md)

[脱敏试用反馈](https://github.com/fugui6688661/glom-continuity/issues/new?template=field_trial.yml) · [可复用项目方法](docs/field-lessons.md) · [来源记录](PROVENANCE.md) · [MIT License](LICENSE)
