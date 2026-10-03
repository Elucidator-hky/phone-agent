#!/usr/bin/env python3
"""平板 UI 控件树解析器 —— 像人一样"看"屏幕，但拿到的是结构化元素。

用法:
  python3 ui.py              # 列出所有有文字/可点击的元素 + 中心坐标
  python3 ui.py 关键词        # 只显示包含关键词的元素
  python3 ui.py -a           # 全部元素（含无文字的）
"""
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


def dump():
    subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
                   capture_output=True, timeout=30)
    r = subprocess.run(["adb", "shell", "cat", "/sdcard/ui.xml"],
                       capture_output=True, timeout=30)
    return r.stdout.decode("utf-8", "ignore")


def center(bounds):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2, x2 - x1, y2 - y1


def main():
    kw = None
    show_all = False
    for a in sys.argv[1:]:
        if a == "-a":
            show_all = True
        else:
            kw = a

    xml = dump()
    xml = xml[xml.index("<?xml"):] if "<?xml" in xml else xml
    root = ET.fromstring(xml)

    rows = []
    for n in root.iter("node"):
        text = (n.get("text") or "").strip()
        desc = (n.get("content-desc") or "").strip()
        rid = (n.get("resource-id") or "").split("/")[-1]
        cls = (n.get("class") or "").split(".")[-1]
        clickable = n.get("clickable") == "true"
        c = center(n.get("bounds", ""))
        if not c:
            continue
        label = text or desc
        if not show_all and not label and not (clickable and rid):
            continue
        if kw and kw not in (label + rid + cls):
            continue
        rows.append((label, rid, cls, clickable, c))

    for label, rid, cls, clickable, (cx, cy, w, h) in rows:
        flag = "●" if clickable else " "
        print(f"{flag} ({cx},{cy}) {w}x{h} [{cls}]{('#' + rid) if rid else ''} {label}")

    print(f"\n共 {len(rows)} 个元素")


if __name__ == "__main__":
    main()
