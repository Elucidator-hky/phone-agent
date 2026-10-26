#!/bin/bash
# 接地层：让小模型看屏幕出坐标（替代大模型看每一帧）
# 用法: ./see.sh "第一个商品的价格标签"      → 输出真机坐标 "1183 112"
#      ./see.sh -t "搜索框"                  → 出坐标并直接点击
# 模型: qwen3-vl-plus（百炼），~1100 token/次，比大模型看原图省 60%+ 且便宜十倍

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
case "${1:-}" in
  -h|--help) echo '用法: see.sh [-t] "要找的元素描述"；环境变量 DASHSCOPE_API_KEY 或 DASHSCOPE_ENV_FILE、ANDROID_SERIAL、PHONE_AGENT_SHOT_DIR'; exit 0 ;;
esac

DO_TAP=0
[ "${1:-}" = "-t" ] && { DO_TAP=1; shift; }
TARGET="${1:-}"
[ -z "$TARGET" ] && { echo "用法: $0 [-t] \"要找的元素描述\""; exit 1; }
DASHSCOPE_API_KEY=$(python3 - "$DIR" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from see import load_key
print(load_key())
PY
)
export DASHSCOPE_API_KEY
SHOT_ROOT="${PHONE_AGENT_SHOT_DIR:-${TMPDIR:-/tmp}/phone-agent}"
mkdir -p "$SHOT_ROOT"
TMP=$(mktemp -d "$SHOT_ROOT/see.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

# 1. 截图 + 缩到 1280 高（省 token，坐标按比例还原）
adb exec-out screencap -p > "$TMP/_see.png"
REAL_W=$(sips -g pixelWidth "$TMP/_see.png" | tail -1 | awk '{print $2}')
REAL_H=$(sips -g pixelHeight "$TMP/_see.png" | tail -1 | awk '{print $2}')
sips -Z 1280 "$TMP/_see.png" --out "$TMP/_see_s.png" >/dev/null
SW=$(sips -g pixelWidth "$TMP/_see_s.png" | tail -1 | awk '{print $2}')
SH=$(sips -g pixelHeight "$TMP/_see_s.png" | tail -1 | awk '{print $2}')

# 2. 问模型要坐标
python3 - "$TARGET" "$TMP" "$SW" "$SH" "$REAL_W" "$REAL_H" "$DO_TAP" "$DIR" <<'PY'
import sys, os, json, base64, subprocess, urllib.request

target, tmp, sw, sh, rw, rh, do_tap, d = sys.argv[1:9]
sw, sh, rw, rh = int(sw), int(sh), int(rw), int(rh)

img = base64.b64encode(open(f"{tmp}/_see_s.png", "rb").read()).decode()
body = json.dumps({
    "model": "qwen3-vl-plus",
    "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}},
        {"type": "text", "text": f"这是一张手机截图。找到：{target}。只输出该元素中心点坐标，格式严格为 [x,y]，不要任何其他文字。找不到就输出 [-1,-1]"},
    ]}],
    "max_tokens": 40,
}).encode()

req = urllib.request.Request(
    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    data=body,
    headers={"Authorization": f"Bearer {os.environ['DASHSCOPE_API_KEY']}",
             "Content-Type": "application/json"})
# 国内服务不走代理
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
res = json.load(opener.open(req, timeout=60))

txt = res["choices"][0]["message"]["content"].strip()
tok = res["usage"]["total_tokens"]
nums = [int(n) for n in __import__("re").findall(r"-?\d+", txt)][:2]
if len(nums) < 2 or not all(0 <= n <= 1000 for n in nums):
    print(f"NOT_FOUND ({txt}) tokens={tok}"); sys.exit(2)

# Qwen3-VL 返回的是 0-1000 千分比归一化坐标，不是缩略图像素坐标
x = min(rw - 1, int(nums[0] / 1000 * rw))
y = min(rh - 1, int(nums[1] / 1000 * rh))
print(f"{x} {y}  (tokens={tok})")
if do_tap == "1":
    subprocess.run([f"{d}/hput.sh", "tap", str(x), str(y)], check=True)
PY
