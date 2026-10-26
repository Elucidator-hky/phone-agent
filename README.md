# phone-agent

用 Mac 操控 iPhone 和安卓设备：读取控件、截图、点击、输入，并按 App 保存操作路径和踩坑经验。

Skill、工具、安装教程和实操记录都在这个仓库，下载这一份即可。朋友需要连接自己的设备并完成首次配置；页面随系统、App 版本和屏幕布局变化，每步执行后都要验证。

## 开始使用

```bash
git clone https://github.com/Elucidator-hky/phone-agent.git
cd phone-agent
```

- **iPhone**：按 [首次配置](core/iphone-setup.md) 安装依赖、用自己的 Apple ID 签名 WebDriverAgent，再启动连接。
- **安卓**：准备 Python 3、adb 和 USB 调试；中文输入另装 ADB Keyboard。按 [设备通路](core/通路.md) 选择设备、确认坐标和输入法。
- **Skill**：本仓库的 [iphone-control](skills/iphone-control/SKILL.md) 和 [phone-cleanup](skills/phone-cleanup/SKILL.md) 分别负责 iPhone 操控、iPhone / 安卓清理。

完成设备配置后，在仓库根目录启动 Claude Code 并加载这里的 Skill：

```bash
export PHONE_AGENT_HOME="$PWD"
claude --plugin-dir "$PHONE_AGENT_HOME"
```

启动后可直接说「看一下手机存储空间」或要求操作指定 App。每次启动都带 `--plugin-dir`；也可以将两个 Skill 目录复制到自己的 Skill 安装目录，并保留 `PHONE_AGENT_HOME` 指向本仓库。首次连接按上面的 iPhone 或安卓说明完成。

目录说明：`skills/` 是两个 Skill，`core/tools/` 是可执行工具，`core/apps/` 是各 App 的使用记录，`core/iphone-setup.md` 是 iPhone 首次配置教程。

## 工具怎么用

| 任务 | 工具 / 文档 |
|---|---|
| iPhone 截图、控件树、文字点击、中文输入 | `python3 core/tools/ios.py --help` |
| iPhone 连接、诊断、停止自己的会话 | `bash core/tools/ios_wda.sh --help` |
| 安卓读控件、按文字点击 | `python3 core/tools/ui.py --help` / `python3 core/tools/tap.py --help` |
| 安卓输入中文、点击和截图 | `bash core/tools/hput.sh --help` |
| 安卓控件树读不到时用视觉模型定位 | `python3 core/tools/see.py --help` / `bash core/tools/see.sh --help` |
| 一步一验证、坐标换算、工具使用技巧 | [设备通路](core/通路.md) |

iPhone 的核心操作通过本机 WDA 完成；安卓的 `see.py` / `see.sh` 会把截图发送给阿里云百炼，并使用自己的 API key 产生调用费用。普通控件树和截图命令不依赖百炼。

## 操作经验

记录来自实际操作，验证场景为 2026 年 8–10 月的安卓设备及 iPhone 16；其中界面入口、控件名称和权限弹窗以使用时的屏幕为准。

| 手册 | 包含内容 |
|---|---|
| [iOS 系统](core/apps/iOS系统.md) | 存储、App 删除、iCloud 同步、录音备份、照片传输、粘贴权限 |
| [安卓系统](core/apps/安卓系统.md) | 存储和电池体检、缓存清理、USB 调试 |
| [拼多多](core/apps/拼多多.md) | 百亿补贴搜索、配置价格、商品快照归档 |
| [闲鱼](core/apps/闲鱼.md) | 安卓发布编辑、iPhone 正文和图片编辑、价格核对 |
| [小红书](core/apps/小红书.md) | 图文和视频发布、编辑、文字输入 |
| [微信](core/apps/微信.md) | 起草消息、控件树差异、授权边界 |
| [淘宝](core/apps/淘宝.md) | 网页配置比价、iPhone 验证页处理 |
| [Facebook](core/apps/Facebook.md) | 经授权只读查看账户设置 |

## 维护与边界

操作前读 [CLAUDE.md](CLAUDE.md)、设备通路和目标 App 手册。新的操作路径写进 `core/apps/`；脚本参数、安装依赖和失败处理写进对应工具文档。任务素材放在本地 `tasks/`。

支付、密码、生物识别由用户本人完成。发送、发布和删除按本次授权执行；遇到验证码、登录验证或页面不符时停下。清理数据前确认备份及同步影响，清空「最近删除」需要单独明确授权。
