# iPhone 安装与工具使用

Mac 通过 USB 连接 iPhone。手机运行 WebDriverAgent（WDA），`iproxy` 把手机固定的 8100 端口转发到 Mac，`ios.py` 调用 WDA。核心 Python 工具只用标准库，不需要 Appium 服务端或付费 API。

## 首次配置

### 1. 准备工具和设备

需要完整 Xcode、Python 3、`curl`、`iproxy`。先用 `command -v python3 curl iproxy xcodebuild` 检查。Xcode 从 App Store 安装，选择兼容自己 macOS 和 iOS 的版本；装好后启动一次完成组件安装。已安装 Homebrew 时，缺少 `iproxy` 可运行 `brew install libimobiledevice`。

在 Xcode → Settings → Apple Accounts 登录自己的 Apple ID。USB 连接并解锁 iPhone，在手机上信任电脑。Xcode 识别手机后，在手机「设置 → 隐私与安全性 → 开发者模式」开启开发者模式，按提示重启并确认。密码和钥匙串授权由本人处理。

### 2. 获取并签名 WDA

上游为 [appium/WebDriverAgent](https://github.com/appium/WebDriverAgent)。下面使用本项目原版跑通的 `v16.15.0`；换版本时按该版本上游说明重新验证。

```bash
mkdir -p "$HOME/code"
git clone --branch v16.15.0 https://github.com/appium/WebDriverAgent.git "$HOME/code/WebDriverAgent"
open "$HOME/code/WebDriverAgent/WebDriverAgent.xcodeproj"
```

在 Xcode 中选择 `WebDriverAgentRunner` target，进入 Signing & Capabilities，启用自动签名并选择自己的 Team。将 Runner 的 Bundle Identifier 改成自己唯一的值，例如 `com.yourname.WebDriverAgentRunner`，处理 Xcode 显示的签名问题。运行目标选自己的 iPhone。Team ID 可在该 target 的 Build Settings → Development Team 中查看；手机 UDID 可从 Window → Devices and Simulators 中复制。

在 phone-agent 仓库根目录运行 `cp .env.example .env`，填入 `IOS_UDID`、`WDA_TEAM_ID`，并按实际位置填写 `WDA_PROJECT_DIR`。`.env` 使用简单的 `KEY=value` 格式；含空格的值加引号。工具自动读取这份文件，进程环境变量优先。

### 3. 构建、启动和验证

在仓库根目录执行。首次构建以及证书续签均用同一条构建命令：

```bash
set -a
source .env
set +a
mkdir -p .runtime
xcodebuild build-for-testing \
  -project "$WDA_PROJECT_DIR/WebDriverAgent.xcodeproj" \
  -scheme WebDriverAgentRunner -destination "id=$IOS_UDID" \
  -allowProvisioningUpdates \
  -derivedDataPath "${WDA_DERIVED_DATA:-$WDA_PROJECT_DIR/build}" \
  "DEVELOPMENT_TEAM=$WDA_TEAM_ID" > .runtime/wda-build.log 2>&1
```

在 `.runtime/wda-build.log` 中确认 `TEST BUILD SUCCEEDED`。保持手机解锁亮屏：

```bash
core/tools/ios_wda.sh check
core/tools/ios_wda.sh start
python3 core/tools/ios.py status
python3 core/tools/ios.py tree
```

`check` 只检查本地工具、配置和构建目录；`status` 只读取 WDA 状态。`start` 输出 `READY` 后才操作手机。本仓库为同一设备启动的转发已就绪时立即返回；冷启动通常约 30–60 秒，最久等待约两分钟。`tree` 能显示当前页面文字才说明操作通路可用。

首次启动若提示未信任开发者，在手机「设置 → 通用 → VPN 与设备管理」中信任自己的开发者证书；若提示自动化超时，在手机「设置 → 开发者」打开「启用 UI 自动化」，并由本人处理弹窗。完成后重跑 `start`。

剪贴板命令需要 Runner 的实际包名：运行 `python3 core/tools/ios.py apps WebDriverAgent`，将列出的 Runner 包名填入 `.env` 的 `WDA_RUNNER_BUNDLE_ID`。通常是 Xcode 中的 Bundle Identifier 再加 `.xctrunner`。

## 日常命令

均从仓库根目录执行 `python3 core/tools/ios.py <命令>`；完整参数用 `--help` 查看。

| 命令 | 作用与验证 |
|---|---|
| `status` | 只读返回 WDA 状态；不创建会话 |
| `tree [关键词]` | 读可见控件文字、类型和中心坐标；默认每项最多显示 60 字 |
| `shot [路径]` | 保存截图，按设备窗口宽度缩放到点坐标；默认 `/tmp/ios.png` |
| `tapt 文字 [序号]` | 优先匹配完整文字，再包含匹配；多个匹配从序号 0 开始 |
| `tap X Y` | 按点坐标点按；之后用 tree 或 shot 验证 |
| `swipe X1 Y1 X2 Y2 [秒]` | 秒数为起点按住时长，默认 0.05；按久会变长按 |
| `type 文字` | 向当前焦点输入框输入，支持中文和换行 |
| `clipboard 文件 包名` | 将 UTF-8 文件写入剪贴板并核对，再切回目标 App，随后手动或通过界面粘贴 |
| `clipboard-check 文件 包名` | 核对从编辑界面复制的完整内容；读取受限时停止并在界面核对 |
| `home` / `launch 包名` | 回桌面或启动 App |
| `url 网址` | 用手机默认浏览器打开网址 |
| `apps [关键词]` | 通过 Xcode 列安装的 App；需要配置 IOS_UDID |

先 `tree` 找控件，文字定位优先，图片和无文字按钮才用截图。每个动作后核对页面，每步间留 2–6 秒。坐标以自己设备的截图尺寸为准，显示缩放会改变点尺寸。

`clipboard` 会激活 Runner 再切回指定 App；允许粘贴的系统提示需要在手机上处理。长文本发布后要在编辑界面或发布页回读全文，截断的 `tree` 摘要不足以验证。

停止本仓库启动的服务：`core/tools/ios_wda.sh stop`。它只处理本仓库记录且仍与记录命令一致的 PID；用户另行启动的 WDA 或转发服务由用户自己的启动方式管理。

## 排错

| 现象 | 做法 |
|---|---|
| `check` 报配置缺失 | 填好仓库根目录 `.env`，确认不是仍在编辑 `.env.example` |
| 找不到构建目录 | 先执行 build-for-testing，核对 WDA_PROJECT_DIR 和 WDA_DERIVED_DATA |
| 日志提示 Unlock | 本人解锁手机，保持亮屏后重试 |
| `Developer App Certificate is not trusted` | 在手机 VPN 与设备管理中信任自己的证书 |
| `Timed out while enabling automation mode` | 打开启用 UI 自动化并处理手机弹窗 |
| `This provisioning profile has expired` / `0xe8008011` | 重跑带 `-allowProvisioningUpdates` 的构建命令，再 start；免费签名需定期续签 |
| 已有未管理的 WDA | 核对该服务的目标设备；需要由此仓库启动时，换空闲的 WDA_LOCAL_PORT；`status` 只报告服务响应，不证明设备身份 |
| 端口被占用且未就绪 | 先核对占用进程用途；另一套服务正在使用时，换 WDA_LOCAL_PORT |
| 连接拒绝 | 查看 `.runtime/wda-<端口>/xcodebuild.log` 和 `iproxy.log`，处理报错后再启动 |
| 启动会话结束后服务消失 | 执行环境可能回收后台子进程；保留启动终端或执行会话，在另一会话操作手机 |
| start 提示已有启动锁 | 先确认同仓库没有启动命令在运行，再清理 `.runtime/wda-<端口>/start.lock` |

编译日志保存到文件中再读取。支付、密码、指纹和设备解锁由本人完成；验证码、实名、人脸与风控验证交回手机主人。

## 验证范围

原版工具在 Mac + USB + iPhone 16 上跑通过，WDA 源码为 `v16.15.0`（提交 `e7e2665a00633dc174d7fc579f7e606bc9ba782a`）。分享版已验证 Python 语法、macOS 自带 Bash 3.2、配置读取与环境优先级、只读状态请求、参数错误和进程归属检查。分享版尚未在另一台 Mac / iPhone 完成首次签名及真机全流程；安装后以本页的启动和控件树检查验收。
