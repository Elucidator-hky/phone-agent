#!/usr/bin/env python3
"""用通义千问 VL 看屏幕找按钮 —— 给读不到控件树的页面用（闲鱼 H5 / Flutter 分屏）。

用法:
  python3 see.py "发布按钮"           # 返回坐标
  python3 see.py "发布按钮" --tap      # 找到并点击
  python3 see.py --ask "现在这个页面在干什么？有哪些按钮？"   # 纯问答

能读控件树的页面（小红书等全屏 App）用 tap.py，比这个快且精确。
key 从 ~/.config/secrets/dashscope.env 读，走 --noproxy（国内服务不过代理）。
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.request

SHOT_W = 1400          # 发给模型的图宽度
API = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen-vl-max"  # 注意：qwen-vl-max-latest 这个 key 没权限


def load_key():
    env = os.path.expanduser("~/.config/secrets/dashscope.env")
    for line in open(env, encoding="utf-8"):
        if line.startswith("DASHSCOPE_API_KEY"):
            return line.split("=", 1)[1].strip()
    raise SystemExit("dashscope.env 里没找到 DASHSCOPE_API_KEY")


def screenshot():
    """截图并缩放，返回 (base64, 缩放系数)。系数 = 真实坐标 / 图上坐标"""
    tmp = "/tmp/_see_raw.png"
    small = "/tmp/_see.png"
    with open(tmp, "wb") as f:
        f.write(subprocess.run(["adb", "exec-out", "screencap", "-p"],
                               capture_output=True, timeout=30).stdout)
    subprocess.run(["sips", "-Z", str(SHOT_W), tmp, "--out", small],
                   capture_output=True, timeout=30)
    dims = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", tmp],
                          capture_output=True, timeout=15).stdout.decode()
    raw_w = int(re.search(r"pixelWidth:\s*(\d+)", dims).group(1))
    raw_h = int(re.search(r"pixelHeight:\s*(\d+)", dims).group(1))
    scale = max(raw_w, raw_h) / SHOT_W
    return base64.b64encode(open(small, "rb").read()).decode(), scale


def ask(prompt, img_b64):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
            {"type": "text", "text": prompt},
        ]}],
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {load_key()}",
        "Content-Type": "application/json",
    })
    # 国内服务不走代理
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=90) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    do_tap = "--tap" in args
    pure_ask = "--ask" in args
    target = " ".join(a for a in args if not a.startswith("--"))

    img, scale = screenshot()

    if pure_ask:
        print(ask(target, img))
        return

    prompt = (
        f"这是一张 Android 平板的截图。请找到页面上的「{target}」。\n"
        f"只输出它中心点的像素坐标，格式严格为 x,y（两个整数，逗号分隔，不要任何其他文字）。\n"
        f"如果页面上没有这个元素，只输出 NONE。"
    )
    out = ask(prompt, img).strip()
    m = re.search(r"(\d+)\s*[,，]\s*(\d+)", out)
    if not m:
        print(f"没找到：{target}（模型回复：{out}）")
        sys.exit(1)

    x, y = int(int(m.group(1)) * scale), int(int(m.group(2)) * scale)
    print(f"{target} → ({x},{y})   [图上 {m.group(1)},{m.group(2)} × {scale:.3f}]")
    if do_tap:
        subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], timeout=15)
        print("已点击")


if __name__ == "__main__":
    main()
