# 跨平台 CI 草案与验证边界

## 2026-09-25：Alpha.7 开发候选的两条检查线路

本节是新代码的验证配置，不是新一次 GitHub Actions 成功记录。Alpha.6
的旧结果不能替代本候选。源码版本已改为 `0.1.0-alpha.7`，尚未公开发行。

- **Portable**：保留 Linux/Python 3.10、Linux/Python 3.12、Windows/Python
  3.12、macOS/Python 3.12 四环境，执行显式清单内的 Python 测试、安装验证和
  合成协议回放，不据此声称 Harness 宿主已通过。
- **Required Harness / macOS**：固定 Node 26.6.0，使用独立 `npm ci` 安装
  锁定的官方 DSH 0.1.5-rc.1 及配套依赖。禁用 npm 生命周期脚本。逐个运行六个
  Node 测试文件和真实受管宿主 CLI 测试；缺 SDK、空套件、跳过、失败或超时
  均拒绝通过。运行时仅允许本机回环和 Unix socket，无模型密钥或日常 profile。

`ci/test-plan.json` 把每个 `tests/test_*.py` / `tests/test_*.mjs` 分配到一条
线路。唯一排除项是被直接 Node 检查替代的 Python 包装测试，并记录了理由。
新增文件漏分配、重复、缺失、符号链接、畸形清单会先失败，不靠人工记得改命令。

Windows 只允许精确 ID 和理由对应的 POSIX 跳过：原有九项，加私有目录安装器
十三项；并单独披露打包测试中未在 Windows 执行的宿主子检查。任何整轮零执行、
未知跳过、MCP SDK 或构建依赖缺失仍失败。适用范围不是“全平台自动恢复”。

本机预检已跑过 156 项 Portable、34 项 Node 和一个真实宿主复合检查，均无跳过；
这是开发树 macOS 结果，不是固定发行包或四平台结果。另将宿主时限设为六秒，
实际得到超时失败而非通过。超时先中断测试以执行收尾；必要时通过本次临时 home
的身份校验控制口停止宿主。不能确认停止则保留控制文件并标失败，不按磁盘 PID
杀进程。强制杀死测试后的所有异常时序仍未穷尽。

本地复现（在源码目录，Python 已装 MCP 与构建工具）：

```sh
python scripts/ci_plan.py check
python scripts/ci_plan.py portable
npm ci --prefix ci/harness --ignore-scripts --no-audit --no-fund --registry=https://registry.npmjs.org
python scripts/ci_harness.py --sdk-package ci/harness/node_modules/@deepseek-ai/dsh/package.json
```

后两步需要受支持的 Node 和 macOS；下载依赖会联网，测试不调用付费模型。
`--host-timeout-seconds 6` 仅用于故障检查，出现失败是该检查的预期结果。
所有 action 固定完整 SHA；新增 setup-node v4 对应
`49933ea5288caeca8642d1e84afbd3f7d6820020`。仍无发布权限、不上传原始测试日志。
下方旧 discovery 命令、跳过数量和旧源码结论均属于其注明日期，不是新版清单。

## 2026-09-15：当前开发提交已完成CI

`fc34543450613cc43f0ff014789b6dbad0bddce9` 的四组CI已完成：Linux两组和macOS各69通过，Windows61通过、8项明确跳过、无失败。准确范围及后续说明变化见[实测记录](verification.md)。下方旧“待运行”保留其时点，不代表当前仍未运行；也不能拿这次结果认证以后更改的程序。

## 2026-09-14：公开仓库后的正式版准备

本节覆盖下文“私有草案”的旧操作条件；历史结果不改写。Alpha.5 的[四组CI 34688280351](https://github.com/fugui6688661/glom-continuity/actions/runs/34688280351)已通过：Linux Python3.10/3.12、macOS Python3.12 各67通过；Windows Python3.12 为59通过、8项明确跳过。下方 alpha.5“待验证”是之前的时间点。

正式版准备源码为 `0.1.0.dev1`，不是已发布版本。原 workflow 的 `private == true` 会使公开仓库所有 job 跳过；现在移除这一私有属性条件，但仍固定本仓库、仅接受勾选 `reviewed` 的手动运行或同仓库 PR。fork PR 不运行，不使用 `pull_request_target`，不自动发布。

其他约束不变：四组 GitHub-hosted runner、完整 SHA 固定 actions、只有 `contents: read`、checkout 不保留凭据、不传模型密钥、不上传原始日志，Windows 八项跳过白名单不扩大。公开平台会显示已审核的代码、测试名称/版本/哈希及脱敏摘要；这些内容必须先审再推送。

运行入口为 `Verify standalone tool`。手动选定已审查 ref 并确认输入；看具体 job 与摘要，不把“全跳过”当通过。此修改本身不证明新代码经过 CI；新结果须绑定新提交，不能借用 Alpha.5 的成绩。

下文自日期开始是 2026-09-12 历史设计与运行记录，其中 PRIVATE 和旧 workflow 名称不再是当前配置要求。

日期：2026-09-12。**最新：alpha.4第二轮四组CI均通过其适用项目，Windows保留8项明确跳过；alpha.5追加终端编码修复，待新版复验。**后面的“本轮草案”是初始编写快照，不代表现在还没运行。

## 第二次运行

[运行34687974481](https://github.com/fugui6688661/glom-continuity/actions/runs/34687974481)，提交`7c911d5e23fb9d6789e7b39bdecbc27ecf8b39d8`，alpha.4：

| 实际环境 | 结果 | unittest阶段秒数 |
|---|---|---|
| Linux x86_64 / Python3.10.21 | 65通过，0跳过 | 62.41 |
| Linux x86_64 / Python3.12.14 | 65通过，0跳过 | 62.34 |
| macOS arm64 / Python3.12.10 | 65通过，0跳过 | 44.33 |
| Windows AMD64 / Python3.12.10 | 57通过，8项预声明POSIX跳过，0失败 | 66.47 |

四份下载的摘要中CLI SHA-256均为`e0fbc0eab770ee619ea4da46c3dd32d2b2f55c2657f17580566a2606eedc5dca`，确认Windows没有再被换行转换成另一份字节。不是全部Windows权限/断电/物理设备行为通过。

alpha.5另外新增CLI与首次demo编码用例：强制ASCII/CP1252/GBK管道，原alpha.4出现初始化误报失败或UTF-8解码失败。修复为进程内固定UTF-8/LF输出，不改用户系统语言/环境。两项本机红→绿，不把alpha.4的CI结果转记为alpha.5已经通过。

## 第一次运行与修复候选

[运行34687554263](https://github.com/fugui6688661/glom-continuity/actions/runs/34687554263)，提交`6cbd4be5995df70bc4c0dde6dec5e73bcb290321`，alpha.3。Linux/Python3.12与macOS/Python3.12通过；Linux/Python3.10在深层JSON错误处理测试失败；Windows/Python3.12有2项原始stdio通信测试失败、8项预先声明的POSIX项目跳过。不是四平台通过。

alpha.4候选：JSON解析捕获`RecursionError`并返回`INVALID_INPUT`；测试端为原始Windows子进程补充最小系统启动环境（不是继承模型凭据），保留所有原断言；超时捕获使用兼容3.10的`asyncio.TimeoutError`。原Windows checkout被Git转换为CRLF，文件哈希与LF发行包不同，新增`.gitattributes`固定LF以便复核同一字节。必须等待同组CI复跑才报告修复生效。

## 初始草案记录

本轮只新增 `.github/workflows/verify.yml` 与本文，不改源码、测试、安装包清单、pyproject 或任务包；没有 commit、push、dispatch、发布或读取账号凭据。起始目录不是 Git 工作树，因此本地文件写入不等于已经落入远端仓库。

`fugui6688661/glom-continuity` 为 PRIVATE、采用 MIT、尚未公开，是本次用户提供的上下文；本轮没有登录核验仓库设置。本草案是私有验证流程，不是发布流程，也不代替 [PROVENANCE 发布门](../PROVENANCE.md)。CI 绿色不能证明真实跨厂商模型接力、外部试用、隐私审查或发行批准。

## 矩阵和执行内容

| GitHub-hosted runner | CPython | 目的 | 本轮云端结果 |
| --- | --- | --- | --- |
| `ubuntu-24.04` | `3.10` | README 和 MCP SDK 的最低 Python 版本边界 | 未运行 |
| `ubuntu-24.04` | `3.12` | Linux 常用版本回归 | 未运行 |
| `windows-2022` | `3.12` | Windows 路径、进程、中文文本及安装边界 | 未运行 |
| `macos-14` | `3.12` | macOS 回归；该标签当前对应 arm64，不是 Intel 覆盖 | 未运行 |

固定 OS 标签降低 `latest` 大版本漂移，但镜像、Python 补丁版本和依赖仍可能更新；具体以每次结果中的 `image_version`、`machine`、`python`、依赖版本为准。标签和私有仓库适用性依据 [GitHub-hosted runners 官方表](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)。不代表所有 Windows/macOS 版本、CPU 架构、文件系统、网络盘或默认区域设置都已验证。

每个 job 最长 10 分钟，矩阵 `fail-fast: false`：一个平台失败不抹掉其他平台的结果。同一 workflow、事件和 PR/ref 的新运行取消旧运行；手动运行与 PR 不互相取消。只有 `workflow_dispatch` 和 `pull_request`，没有 `push`、schedule、`pull_request_target` 或自动提交循环。超时、失败、意外 skip 都不使用 `continue-on-error` 放行。配置依据 [GitHub workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)。

运行顺序：

1. checkout 当前事件的 revision，深度 1，不取 submodule/LFS，不持久化 checkout 凭据。
2. setup-python 选择矩阵版本，不启用依赖 cache。
3. 从 PyPI 安装 `requirements-mcp.txt`，同时安装用户指定的 `setuptools>=77.0.3,<85` 与 `wheel>=0.45,<0.49`；安装命令明确 `--retries 0 --timeout 20`，另有 150 秒进程总限时。使用 setup-python 的 pip；不提前 `pip install .`，也不从 PyPI 安装本工具。
4. 单独验证实际 MCP API 可导入（`Client`、`StdioServerParameters`、`MCPServer`），检查 pip/setuptools/wheel 存在，记录这四项实际版本。当前 requirements 固定 `mcp==2.2.0`；本地已安装 SDK 的 distribution metadata 声明 `Requires-Python: >=3.10`，这不是四个平台的安装成功证据。
5. 执行 `python -B -m unittest discover -s tests -v`，不筛掉失败测试。缺 SDK/构建工具时不把空跑或 skip 当作验证成功。
6. 在 `RUNNER_TEMP` 下用 `TemporaryDirectory` 创建独占父目录，然后对其**尚不存在的** `new-demo` 子目录运行 `python -B scripts/smoke_demo.py --output ...`。检查成功回执且 `real_model_handoff_verified` 必须为 false。普通依赖/测试失败后仍尝试 smoke；前置设施异常或 job 被取消时不保证继续。
7. 保存脱敏结果，再根据所有必要阶段和 skip 政策决定退出码。依赖安装/预检/测试/smoke 分别限时 150/15/300/45 秒；job 的 10 分钟总上限仍优先适用。

`smoke_demo.py` 是 CLI 合成协议回放，不启动模型、云端客户端或账号登录。MCP 测试启动的是真实本地 stdio 服务与测试客户端，不是让模型推理。测试中命名为 secret/password 的字符串是合成拒绝用例，不读取用户凭据。

### 安装包并行开发的接入

主线程正在补 `pyproject.toml` 和 `tests/test_installation.py`。本 workflow 直接 discovery 已提交的测试，不假定预先已有 wheel，不复制本机 `.venv-mcp`，不修改安装实现。

已读到的新安装测试会将白名单源码复制到临时目录，用 `pip wheel --no-index --no-deps --no-build-isolation` 离线构建，再安装到临时 venv、从无关目录调用命令、卸载，检查合成项目数据库未被删除。依赖下载安装阶段仍联网，不能把整个 CI 称为离线。wheel 构建产物、便携候选 ZIP 和临时数据库均不上传。缺少 pip/setuptools/wheel 触发的 `Installation` 类 skip 会使本 CI 失败，而不是放行。后续测试文件增删会自然进入 discovery；是否覆盖完整安装功能仍须核对对应 revision 的测试内容。

## Windows 与 Python 的真实边界

以下来自本轮读取的 [CLI](../scripts/continuity.py)、[CLI 独立测试](../tests/test_independent.py)、[MCP 独立测试](../tests/test_mcp_independent.py)、[恢复独立测试](../tests/test_recovery_independent.py) 和 [交付测试](../tests/test_delivery.py)。这些是静态检查结论，不是 Windows 运行结果；并行修改后的实现必须重新核对。

| 边界 | 当前源码/测试事实 | CI 如何解释 |
| --- | --- | --- |
| POSIX FIFO | `test_19_nonregular_draft_should_not_leave_cli_or_mcp_save_hung` 和 `test_21_repeated_nonregular_drafts_should_not_starve_status` 用 `skipUnless(hasattr(os, "mkfifo"))` | Windows 没有该 API 时，两项预期 skip；不是通过，也不等于验证了 Windows named pipe。仅这两个完整测试 ID、Windows 平台、既有准确理由允许跳过。 |
| 符号链接权限 | `test_05_drift_missing_and_static_symlink_recovery`、`test_12_cross_project_draft_evidence_and_export_are_blocked`、`test_13_export_preserves_existing_files_and_excludes_raw_evidence` 直接 `symlink_to`，没有权限不足 skip | Windows 能否创建链接取决于权限/Developer Mode。失败照实记 ERROR，不提权、不自动启用 Developer Mode、不增加 skip。 |
| 文件权限语义 | CLI 用 `os.chmod(path, 0o600)` 和 `mkdir(mode=0o700)`；本轮所读实现没有 `os.fchmod`、`fcntl` 或 `fork` 调用 | 不应虚构“fchmod 导致 Windows 必失败”。Windows `chmod` 不提供 POSIX 的完整权限位语义；即使功能通过，也没有证明等价 ACL/隐私隔离。 |
| 草稿文件打开 | `O_NONBLOCK` 和 `O_BINARY` 都以 `getattr(..., 0)` 取值，再用 `os.fstat` 验证普通文件；导出使用 `O_EXCL`、`fdopen`、`fsync` | 不把不存在的 `O_NONBLOCK` 直接当作必然 AttributeError；普通文件回归和 POSIX FIFO 回归须分开。 |
| Windows 子进程环境 | 两份独立测试显式构造仅 PATH、PYTHONDONTWRITEBYTECODE、PYTHONIOENCODING 的 `self.env`，未带 `SystemRoot` | Python 官方要求 Windows side-by-side assembly 的自定义环境包含有效 SystemRoot。存在启动/SDK兼容风险，但不是所有 subprocess 必然失败。本 CI 外层保留系统启动变量，不能修复测试内部重新构造的 env。 |
| 中文和默认编码 | 某些测试的 `read_text()` / `subprocess(..., text=True)` 未指定编码；外层设置 `PYTHONUTF8=1` 与 `PYTHONIOENCODING=utf-8` | CI 覆盖的是显式 UTF-8 配置，不是默认代码页兼容性；独立测试重建的子进程环境不会自动继承全部设置。 |
| Python 3.10 异常分支 | MCP wire 测试用 `except TimeoutError` 接 `asyncio.wait_for` 的超时 | 3.10 的 `asyncio.TimeoutError` 与内置 TimeoutError 不是同一个异常；3.11 起才成为别名。只有进入相应超时分支时才可能暴露差异，不预先把 3.10 标成通过或必失败。 |

对应一手依据：[Python os.mkfifo](https://docs.python.org/3.12/library/os.html#os.mkfifo)、[os.symlink 的 Windows 权限](https://docs.python.org/3.12/library/os.html#os.symlink)、[os.chmod 的 Windows 限制](https://docs.python.org/3.12/library/os.html#os.chmod)、[subprocess 自定义环境要求](https://docs.python.org/3.12/library/subprocess.html#subprocess.Popen)、[Python UTF-8 Mode](https://docs.python.org/3.12/library/os.html#python-utf-8-mode)、[3.10 asyncio 异常](https://docs.python.org/3.10/library/asyncio-exceptions.html#asyncio.TimeoutError)、[3.12 asyncio 异常](https://docs.python.org/3.12/library/asyncio-exceptions.html#asyncio.TimeoutError)。

最终 Windows skip 白名单共 **8 项**，同时匹配完整 module/class/method ID、Windows 平台和准确原理由。没有按文件、类名或 `Rxx` 前缀笼统跳过：

| 测试（完整 method 名见 workflow） | 实际 decorator skip 理由 | summary 分类 |
| --- | --- | --- |
| MCP `test_19`、`test_21` | `Named-pipe acceptance case requires POSIX` | `posix_fifo_unavailable` |
| `test_recovery_independent.RecoveryIndependentTests` 的 `test_07`–`test_10` | `POSIX permissions only; Windows ACLs not verified` | `posix_permissions_unverified` |
| 同类 `test_11`、`test_12` | `SIGKILL is POSIX-only; not verified on Windows` | `posix_sigkill_unverified` |

恢复 R07–R10 的 helper 还可能因 POSIX root 用户给出 `Requires an ordinary POSIX user; skip is not a permission pass`，此理由**不在白名单**：不能以 root 运行后冒充权限验证。R11–R12 helper 内另有 `SIGKILL experiment is POSIX-only; not a cross-platform pass`，但 Windows 在方法 decorator 处已跳过；本轮准确匹配实际生效的 decorator 原文，不放宽到 helper 文案。Windows 没有验证 POSIX 权限、Windows ACL 等价性或 POSIX SIGKILL 崩溃语义。恢复测试中的 `geteuid` 有 POSIX 短路保护，`select` 管道与 `signal.SIGKILL` 位于 POSIX-only 用例内，不应说成 Windows import 时必然失败。

除此之外其他 skip 一律失败，包括 MCP SDK 缺失、安装构建工具缺失、新增未审阅 skip；上述 8 项在 Linux/macOS 跳过也失败。零测试、无可识别 unittest 总结、expected failure、unexpected success 也不能绿灯。允许的平台 skip 保留完整测试名与分类，总状态标记 `passed_with_platform_skips`；它不表示所有测试都通过。

## 留存、权限和隐私

- 全 workflow 仅 `contents: read`；未声明的 GITHUB_TOKEN 权限为 none。不申请写仓库、PR、packages、id-token 权限，不传入 `secrets.*`、PAT、SSH key 或模型 key。私有 checkout/setup-python 会使用 Actions 自身默认的短期 token；artifact 服务也需要平台自身认证。这不是“完全无认证”，更不需要读取本机账号凭据。[最小权限与 SHA 固定依据](https://docs.github.com/en/actions/reference/security/secure-use)
- job 限定目标仓库名、事件中的 `private == true`，并只接受同仓库 PR 或勾选 reviewed 的手动运行。拒绝 fork/public job 是误用防护，不是不可绕过的安全沙箱；有修改 workflow 权限的人也能修改判断。PR 的 opened/synchronize/reopened 等默认事件仍可触发，因此提交内容在进入该私有仓库/PR 前就应完成隐私审查。
- 测试子进程只获得白名单系统启动变量、Python/pip 设置和临时目录，不转发 Actions token 或任意账户/模型环境变量。不调用模型，不加载本地 Codex/Harness 配置，不使用 self-hosted runner；没有向本机取数的步骤。允许的网络行为是 GitHub checkout/runtime、公共依赖下载与 GitHub artifact 留存；并没有实现网络防火墙或恶意代码隔离。
- 原始 pip/unittest/smoke stdout/stderr 仅在验证进程内存中解析，不回显、不写 rawlog 文件、不上传。每项 unittest 失败保留测试 ID、最后异常类型、已知产品错误码（如 `IO_ERROR`/`OK`）、数值 Errno/WinError、安全的数值/布尔比较，以及最后一个测试文件名和行号；例如符号链接权限失败可定位为 `OSError` + `WINERROR_1314`，捕获不到则明确 `unparsed`。SIGKILL 观察窗口未命中映射为 `SIGKILL_OBSERVATION_MISSED`。不复制任意异常消息、完整 traceback、字符串差异、子测试参数、任意 skip 原文、OBSERVATION JSON、绝对路径或 smoke 的 report 路径。主代理可据精确 test ID、位置、版本/哈希和短码复现；这是有损安全摘要，不保证替代全部调试信息。正常 GitHub runner/action 自身日志仍由平台保留，不能承诺 Actions 没有日志。
- 每个 job 只上传 `RUNNER_TEMP/continuity-results/summary.json`，不使用目录/通配符上传；保留 7 天，隐藏文件关闭，不覆盖旧 artifact，名称包含平台、Python、run ID 和 attempt。包含平台/镜像/Python/SQLite、四项依赖版本、提交号、相对源码/测试文件 SHA-256、阶段退出码/耗时、测试计数、失败测试 ID 和 skip 分类；不含项目文件正文、SQLite、任务包、ZIP、wheel 或原始日志。同份 JSON 出现在 Job Summary。[upload-artifact 配置合同](https://github.com/actions/upload-artifact/blob/043fb46d1a93c77aae656e7c1c64a875d1fc6a0a/action.yml)
- 必须仍在私有仓库内审阅这些元数据；私有 artifact 也不等于允许公开转发。report 是白名单格式而非通用脱敏器，不能替代对源码、依赖、测试和 workflow 的信任审查。测试与汇总进程同属 runner 用户，不能防御恶意同机程序。
- 失败时尝试上传既有摘要；缺文件视为错误。取消/硬超时/runner 损坏可能没有 artifact，或留下 `incomplete`/`running` 阶段；这表示未完成，不能推断通过。自动取消的旧运行不保证留档。

## 官方 actions 完整 SHA 依据

2026-09-12 匿名读取以下官方 release 页面对应的 commit 链接，并读取选定 commit 的 `action.yml` 核对 inputs/runtime；未使用账户 API。SHA 是 40 位完整 commit，不是短 SHA 或会漂移的 tag。选择 checkout 6.1.0 作为已含官方 PR 安全检查回移的基线；不宣称所有 action 都是最新版本，也不宣称做过其全量源码安全审计。

| Action | 版本注释 | 固定完整 commit SHA | 官方依据 |
| --- | --- | --- | --- |
| `actions/checkout` | `v6.1.0` | `d23441a48e516b6c34aea4fa41551a30e30af803` | [release](https://github.com/actions/checkout/releases/tag/v6.1.0) · [commit](https://github.com/actions/checkout/commit/d23441a48e516b6c34aea4fa41551a30e30af803) · [action.yml](https://github.com/actions/checkout/blob/d23441a48e516b6c34aea4fa41551a30e30af803/action.yml) |
| `actions/setup-python` | `v7.0.0` | `5fda3b95a4ea91299a34e894583c3862153e4b97` | [release](https://github.com/actions/setup-python/releases/tag/v7.0.0) · [commit](https://github.com/actions/setup-python/commit/5fda3b95a4ea91299a34e894583c3862153e4b97) · [action.yml](https://github.com/actions/setup-python/blob/5fda3b95a4ea91299a34e894583c3862153e4b97/action.yml) |
| `actions/upload-artifact` | `v7.0.1` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` | [release](https://github.com/actions/upload-artifact/releases/tag/v7.0.1) · [commit](https://github.com/actions/upload-artifact/commit/043fb46d1a93c77aae656e7c1c64a875d1fc6a0a) · [action.yml](https://github.com/actions/upload-artifact/blob/043fb46d1a93c77aae656e7c1c64a875d1fc6a0a/action.yml) |

三项所选 action 都使用 Node 24 runtime；本草案只用 GitHub-hosted runner。SHA 固定只锁 action 代码，不锁下载的 Python、runner 镜像、setuptools/wheel 的范围版本或 MCP 的传递依赖。升级 SHA/依赖时需重新审阅并保留版本依据。

## 审阅后首次手动验证

1. 由主代理/所有者在自己的已授权流程中将审核后的独立工具 revision 与这两个文件放入目标 PRIVATE 仓库；本轮不执行提交/推送。先审阅所有将进入 GitHub 的文件，不提交本机虚拟环境、真实项目数据、内部记忆、凭据、原始日志或任务包。不要因 MIT 或 CI 草案而放宽 PROVENANCE。
2. workflow 必须存在于默认分支，才可使用网页 Run workflow；运行者需要适当的仓库写权限。确认 Actions policy 允许这三个官方 action、对应 hosted runner 可用，并由所有者检查私有仓库分钟数/费用限制；本轮没有读取额度或授权购买。[GitHub 手动运行说明](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
3. 在 Actions 选择 `Verify standalone tool (private draft)`，选择**已经审核的分支/ref**，勾选 reviewed 后手动运行；未勾选时 job 不执行。该勾选只是审阅确认，不授予公开发布权。`pull_request` 默认验证事件 merge revision，手动运行验证所选 ref；复核结果里的实际 commit。
4. 查看四个 job 的真实结论、阶段退出码、MCP/构建版本和 skip 列表，下载小型 `verify-...` 摘要。不能只看绿色图标；`passed_with_platform_skips`、取消、缺报告、失败需分别记录。失败时先根据脱敏测试 ID 在获准的干净环境复现，不直接把 rawlog 上传、粘贴到模型或公开 issue。
5. 将运行链接、commit、runner/Python、计数/skip、artifact 对应关系纳入后续审阅记录。即使全矩阵通过，也继续完成 PROVENANCE 中剩余发布验收。本 workflow 不创建 release/tag，不上传 PyPI，不公开仓库。

## 本轮本地校验

已用本机 YAML parser 核验语法和四组矩阵、触发器、只读权限、10 分钟上限、取消并发、完整 SHA 等结构；内嵌 Python 通过 Python 3.10 grammar 检查与内存 compile。用合成 unittest 输出检查正常通过、零测试、不完整总结、8 个准确 Windows skip、同 skip 在 POSIX 被拒绝、MCP/构建依赖 skip 被拒绝、失败/错误计数、expected failure/unexpected success，以及最后异常/短码可定位但原始路径/内容不进入解析结果。白名单还与测试文件 AST 中实际 decorator 理由逐项核对，不执行产品测试。

没有安装本机依赖，没有运行完整产品 unittest、安装测试或 smoke，没有生成本机临时项目/包或额外验证文件；不以静态检查冒充平台运行。也没有 GitHub 服务端 workflow 校验或 actionlint 实测。验收仍须由审核后的私有仓库手动运行提供证据。
