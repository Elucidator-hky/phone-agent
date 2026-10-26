---
name: phone-cleanup
description: 给 iPhone 或安卓手机做存储体检、分析卡顿并清理空间。用户说手机没空间、iCloud 满了、装不下 App、手机很卡或该不该换时使用。按先盘点、确认范围、备份核对、分批清理、回读容量的流程操作；工具和操作手册随本插件提供。
---

# 手机存储体检与清理

## 配置与设备

`PHONE_AGENT_HOME` 指向本插件所在的 phone-agent 仓库根目录，工具和手册均随插件提供。按 README 启动时已设置；若通过插件加载且未设置，使用本插件的 `${CLAUDE_PLUGIN_ROOT}` 作为根目录，并在每次 shell 命令中设置该路径。目录不存在时先完成仓库 README 的配置，从 `cd "$PHONE_AGENT_HOME"` 启动。

- iPhone：使用同插件的 `iphone-control` Skill，先读 `core/iphone-setup.md` 和 `core/apps/iOS系统.md`；没有加载该 Skill 时直接读这两份手册。
- 安卓：先读 `core/通路.md`、`core/apps/安卓系统.md`，确认 USB 调试和 `adb devices` 的目标设备。多设备时每条命令使用 `adb -s <序列号>`。

## 先盘点

记录型号、系统版本、内存、存储总量与已用量、电池状况，再列出占空间最多的 App 和数据。只读盘点不表示获准删除。

安卓常用命令（按已选设备补上 `-s`）：

```bash
adb shell getprop ro.product.model
adb shell getprop ro.product.marketname
adb shell getprop ro.build.version.release
adb shell cat /proc/meminfo
adb shell df -h /data
adb shell dumpsys battery
adb shell dumpsys diskstats
```

`diskstats` 的 Package Names、App Sizes、Cache Sizes 按索引对应；系统可能使用缓存数据或限制访问，缺失项目标为未知。共享目录大小按 `core/apps/安卓系统.md` 的命令检查。`dumpsys battery` 的电量不等于电池剩余健康容量。

iPhone 在「设置 → 通用 → iPhone 储存空间」读总量和 App 列表；iCloud 容量单独记录，不能当作手机本地容量。按实际界面名称和控件树定位。

判断卡顿结合可用空间、负载、电池状态、用户使用需求和系统更新支持；内存或剩余空间比例只能作为线索。涉及上市年份、当前系统支持或换机建议时查可靠来源，查不到就注明未知。

## 确定清理范围

按能释放的空间、数据是否可恢复排序：缓存、不用的 App、已备份照片和录音、用户指定的大文件。说明会删除什么、预计释放多少；已有授权覆盖的范围直接执行，需要扩大删除范围时先确认。

涉及 iCloud 同步时，先说明其他同账号设备会受到的影响。删除 App 要区分「卸载 App」保留数据和「删除 App」连数据删除。

## 备份、清理、核验

1. 用文件数量、大小、时长和可打开性核对备份；云盘占位文件或 0 字节文件不算有效备份。用户已明确确认备份的按其说明处理。
2. 需要新建备份时保存到用户指定、不会随手机删除而同步消失的位置，记录目录。
3. 分批删除授权范围内的数据，每批回读项目数量或列表；验证失败时停下检查当前界面。
4. 「最近删除」属于永久清除，按用户授权范围处理。要求刷脸或输入锁屏密码时交给用户本人。
5. 等待储存空间重新统计，回读本地和 iCloud 的用量，分别报告前后变化。未重新统计的数字注明待刷新。

## 操作经验与收工

- 录音可分批隔空投送并按名称、日期、时长核对，方法见 `core/apps/iOS系统.md`。
- 相册网格可分批选择；每批核对实际选中数量，控件树的选中标记优先于截图估数。
- 等待任务每 10–20 秒检查状态；一分钟无进展时查原因，避免重复触发删除。
- 家人的手机仅按授权检查设置和存储，聊天内容和相册内容不因体检而默认可读。
- 安卓操作结束按 `core/通路.md` 恢复原输入法；iPhone 的支付、密码和生物识别由本人处理。
- 汇报清理前后用量、已删除类别、备份位置和未完成项；新方法与坑写回对应 App 手册。
