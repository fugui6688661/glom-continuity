# 先用一个小项目试试

这是命令行工具与可选的助手连接器，不是聊天App，也不会自动记住所有聊天。
先准备Python 3.10或更新版本。工具、示例项目与自己的工作资料分开存放。
本次提供开发者预览版，不是稳定生产版本。请从[本仓库的 alpha.5 发布页](https://github.com/fugui6688661/glom-continuity/releases/tag/v0.1.0-alpha.5)下载 `glom-continuity-0.1.0-alpha.5.zip`，或需要安装命令时下载对应 wheel。不要从同名陌生软件下载安装；目前没有 PyPI 或应用商店版本。

下载页同时提供 `SHA256SUMS`。Mac/Linux 可把它与 ZIP、wheel 放在同一目录，运行 `shasum -a 256 -c SHA256SUMS`（校验全部条目须下载两个文件）。Windows 使用 `Get-FileHash 文件名 -Algorithm SHA256` 与清单逐项比较。哈希用于检查下载完整性，不是发布者数字签名。

## 先看效果：不装依赖，不用API

解压ZIP，进入含README的文件夹，在终端运行：

```sh
python3 -B scripts/smoke_demo.py --output ./my-first-demo
```

Windows使用：

```powershell
py -3 -B scripts/smoke_demo.py --output ./my-first-demo
```

打开新生成的`my-first-demo/演示结果.md`。它展示了项目恢复、源文件被修改时拒绝旧交接、重复领取被拒绝。
示例里的两个接手方是程序回放，**不是两个模型**。这是看工具是否运行正常的第一步。
如果该文件夹已存在，换一个新的名字；工具不会帮你覆盖。

## 安装成命令

收到配套的`.whl`文件后，可以安装到自己新建的工具环境。以下以`glom_continuity-0.1.0a5-py3-none-any.whl`为例；只有拿到该文件后才执行。
基础安装从本地wheel读取，不联网、不调用模型。不要在已有同名环境上重复创建。

Mac / Linux：

```sh
python3 -m venv .continuity-tools
.continuity-tools/bin/python -m pip install --no-index --no-deps ./glom_continuity-0.1.0a5-py3-none-any.whl
.continuity-tools/bin/glom-continuity --version
.continuity-tools/bin/glom-continuity-demo --output ./installed-demo
```

Windows PowerShell：

```powershell
py -3 -m venv .continuity-tools
.\.continuity-tools\Scripts\python.exe -m pip install --no-index --no-deps .\glom_continuity-0.1.0a5-py3-none-any.whl
.\.continuity-tools\Scripts\glom-continuity.exe --version
.\.continuity-tools\Scripts\glom-continuity-demo.exe --output .\installed-demo
```

不需要管理员权限，不要求修改全局PATH或PowerShell执行策略。
也可以用环境中的Python运行`-m glom_continuity`，参数与原CLI一致。
这些步骤的实测平台以[验证记录](docs/verification.md)为准，不把说明中的系统名称当作已验证。

## 让助手使用

最简单的方式是把[通用使用协议](skills/project-continuity/SKILL.md)和工具位置交给具备本地文件/命令权限的助手；让它先在一个非敏感测试项目里保存和恢复节点。
项目必须由你明确选择。不要给助手整台电脑访问权来安装此工具，也不用把聊天数据库导进去。

支持本地MCP的助手可以按[MCP接入](adapters/mcp.md)配置。先在该独立环境安装可选依赖：

```sh
.continuity-tools/bin/python -m pip install 'mcp==2.2.0'
```

这一步会从Python包源下载第三方依赖。Windows换成`.\.continuity-tools\Scripts\python.exe`。
客户端的启动命令可指向环境里的`glom-continuity-mcp`（Windows为`.exe`），参数仍是`--project`与所选项目的绝对路径。
默认只读；需保存节点时才显式加`--allow-writes`。这不会授予发邮件、付款或发布权限。

## 验收你自己的第一次接力

1. 助手A处理一个小项目，把目标、限制、未解决的问题与下一步保存，并创建交接。
2. 关掉这段对话，用助手B的新对话读取同一个项目；不要再复制整段原聊天给它。
3. 看B是否先检查文件，再接着做；特别检查它有没有丢掉你没确认的条件。
4. 让B保存结果，再由A的新对话读回。只“能读到记录”不算完整成功。

如果B没有调用工具，只口头说自己记住了，这次接力未通过。
两个助手必须都能访问同一份本地项目；工具目前不负责跨电脑同步。
仅能聊天、不能运行工具的产品，可以手动读审阅快照，但不具备自动校验/回写。

## 停用与反馈

在助手配置中只删除你添加的这一项连接，然后卸载工具：

```sh
.continuity-tools/bin/python -m pip uninstall glom-continuity
```

Windows同样换用环境内的Python。项目里的`.continuity`是你的记录，卸载不删除它。
不要为排错先删库。备份应先停止写入，再复制完整`.continuity`及引用文件，保留相对位置。

反馈时附系统、Python和助手版本、失败步骤、错误码及虚构复现即可。不要发送密钥、公司资料或原始聊天。
