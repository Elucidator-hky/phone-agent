#!/usr/bin/env python3
"""按文字点击控件 —— 不截图，直接读 UI 树定位。

用法:
  python3 tap.py 发布              # 点击文字为"发布"的可点击元素
  python3 tap.py 发布 --index 1    # 有多个匹配时选第 2 个
  python3 tap.py 发布 --dry        # 只查位置不点击
  python3 tap.py --find 租房       # 列出所有包含"租房"的元素

坐标可信度：全屏 App（小红书等）dump 坐标 = 真实坐标，直接可用。
闲鱼是分屏 + Flutter，dump 坐标有缩放偏移，那边仍需截图定位。
"""
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


def dump():
    subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
                   capture_output=True, timeout=30)
    out = subprocess.run(["adb", "shell", "cat", "/sdcard/ui.xml"],
                         capture_output=True, timeout=30).stdout.decode("utf-8", "ignore")
    return out[out.index("<?xml"):] if "<?xml" in out else out


def elements():
    root = ET.fromstring(dump())
    out = []
    for n in root.iter("node"):
        label = (n.get("text") or "").strip() or (n.get("content-desc") or "").strip()
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.get("bounds", ""))
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        if x2 - x1 == 0 or y2 - y1 == 0:      # 不可见元素
            continue
        out.append({
            "label": label,
            "rid": (n.get("resource-id") or "").split("/")[-1],
            "clickable": n.get("clickable") == "true",
            "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2,
            "w": x2 - x1, "h": y2 - y1,
        })
    return out


def main():
    args = [a for a in sys.argv[1:]]
    dry = "--dry" in args
    find = "--find" in args
    idx = 0
    if "--index" in args:
        i = args.index("--index")
        idx = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    args = [a for a in args if not a.startswith("--")]
    kw = args[0] if args else None

    els = elements()
    if find or not kw:
        for e in els:
            if not kw or kw in e["label"] or kw in e["rid"]:
                flag = "●" if e["clickable"] else " "
                print(f"{flag} ({e['cx']},{e['cy']}) {e['w']}x{e['h']} {e['label']} {e['rid']}")
        return

    # 优先精确匹配 + 可点击，其次包含匹配
    exact = [e for e in els if e["label"] == kw and e["clickable"]]
    exact_any = [e for e in els if e["label"] == kw]
    partial = [e for e in els if kw in e["label"] and e["clickable"]]
    partial_any = [e for e in els if kw in e["label"]]
    hits = exact or exact_any or partial or partial_any

    if not hits:
        print(f"未找到：{kw}")
        sys.exit(1)
    if idx >= len(hits):
        print(f"只有 {len(hits)} 个匹配，index {idx} 越界")
        sys.exit(1)

    t = hits[idx]
    print(f"{'[dry] ' if dry else ''}点击 ({t['cx']},{t['cy']}) ← {t['label']}"
          f"{f'  [共{len(hits)}个匹配]' if len(hits) > 1 else ''}")
    if not dry:
        subprocess.run(["adb", "shell", "input", "tap", str(t["cx"]), str(t["cy"])], timeout=15)


if __name__ == "__main__":
    main()
