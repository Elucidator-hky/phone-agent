#!/usr/bin/env python3
"""用通义千问 VL 看屏幕找按钮 —— 给读不到控件树的页面用（闲鱼 H5 / Flutter 分屏）。

用法:
  python3 see.py "发布按钮"           # 返回坐标
  python3 see.py "发布按钮" --tap      # 找到并点击
  python3 see.py --ask "现在这个页面在干什么？有哪些按钮？"   # 纯问答

能读控件树的页面（小红书等全屏 App）用 tap.py，比这个快且精确。
key 从 DASHSCOPE_API_KEY 环境变量或 DASHSCOPE_ENV_FILE 指定文件读取。
截图临时目录可通过 PHONE_AGENT_SHOT_DIR 配置；请求直接连接百炼。
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import urllib.request

SHOT_W = 1400          # 发给模型的图宽度
API = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen-vl-max"


def load_key():
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if key:
        return key
    env = os.environ.get("DASHSCOPE_ENV_FILE")
    if env:
        for line in Path(env).expanduser().read_text(encoding="utf-8").splitlines():
            match = re.match(r'^\s*(?:export\s+)?DASHSCOPE_API_KEY\s*=\s*(.*?)\s*$', line)
            if match:
                key = match.group(1).strip('\"\'')
                if key:
                    return key
    raise SystemExit("请设置 DASHSCOPE_API_KEY，或通过 DASHSCOPE_ENV_FILE 指定包含该变量的文件")


def screenshot():
    """截图并缩放，返回 (base64, 缩放系数)。系数 = 真实坐标 / 图上坐标"""
    parent = os.environ.get("PHONE_AGENT_SHOT_DIR")
    if parent:
        parent = str(Path(parent).expanduser())
        Path(parent).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="phone-agent-see-", dir=parent) as folder:
        tmp = str(Path(folder) / "raw.png")
        small = str(Path(folder) / "small.png")
        with open(tmp, "wb") as f:
            f.write(subprocess.run(["adb", "exec-out", "screencap", "-p"],
                                   capture_output=True, timeout=30, check=True).stdout)
        subprocess.run(["sips", "-Z", str(SHOT_W), tmp, "--out", small],
                       capture_output=True, timeout=30, check=True)
        dims = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", tmp],
                              capture_output=True, timeout=15, check=True).stdout.decode()
        scaled = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", small],
                                capture_output=True, timeout=15, check=True).stdout.decode()
        raw_size = max(map(int, re.findall(r"pixel(?:Width|Height):\s*(\d+)", dims)))
        small_size = max(map(int, re.findall(r"pixel(?:Width|Height):\s*(\d+)", scaled)))
        return base64.b64encode(Path(small).read_bytes()).decode(), raw_size / small_size


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
    if "--help" in args or "-h" in args:
        print(__doc__)
        return
    if not args:
        raise SystemExit(__doc__)
    do_tap = "--tap" in args
    pure_ask = "--ask" in args
    target = " ".join(a for a in args if not a.startswith("--"))
    if not target:
        raise SystemExit("请提供要找的元素或问题")
    load_key()
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
