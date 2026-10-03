# phone-agent

用 Mac 通过 adb 操控安卓设备，让 Claude Code 代替人在手机 App 里完成发帖、编辑、私信等操作。

核心思路：**经验累积**。每完成一个任务，就把操控某个 App 的路径、坑、红线写回 `core/apps/<App>.md`，下次直接复用。

## 结构

```
CLAUDE.md               给 Claude Code 的工作规则（开工先读什么、收工写回哪）
core/通路.md             设备通路、坐标口径、输入法、硬规则
core/技术路线.md          方案选型与已否决的路线
core/项目目标与边界.md    不可越界的事
core/apps/              各 App 操作手册：小红书、闲鱼、微信、拼多多
core/tools/             截图识别（qwen-vl）、控件树定位、点击/输入封装
```

## 依赖

- adb + ADB Keyboard（中文输入）
- Python 3
- 阿里云百炼 API key（截图识别），放在 `~/.config/secrets/dashscope.env` 的 `DASHSCOPE_API_KEY`

## 边界

支付、密码、指纹一律人工；消息默认只起草不自动发送；操作加随机延迟。
