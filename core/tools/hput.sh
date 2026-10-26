#!/bin/bash
# 人类化 ADB 操作封装 —— 防风控 + 提高准确率
# 用法: ./hput.sh tap X Y | swipe X1 Y1 X2 Y2 | text "内容" | key HOME | shot [名字] | wait

set -euo pipefail
SHOT_DIR="${PHONE_AGENT_SHOT_DIR:-${TMPDIR:-/tmp}/phone-agent}"
ADB=adb

usage() {
  echo '用法: hput.sh tap X Y | swipe X1 Y1 X2 Y2 | text "内容" | key HOME | shot [名字] | wait | focus | ime_back'
  echo '环境变量: ANDROID_SERIAL 指定设备；PHONE_AGENT_SHOT_DIR 指定截图目录；ANDROID_IME 指定要恢复的输入法。'
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  '') usage; exit 2 ;;
esac

# 随机小数延迟 rnd_sleep 最小 最大 (毫秒)
rnd_sleep() {
  local min=$1 max=$2
  local ms=$(( min + RANDOM % (max - min + 1) ))
  sleep "$(( ms / 1000 )).$(printf '%03d' $(( ms % 1000 )))"
}

# 坐标抖动 ±12px，模拟手指落点不精确
jitter() {
  echo $(( $1 - 12 + RANDOM % 25 ))
}

case "$1" in
  tap)
    x=$(jitter $2); y=$(jitter $3)
    rnd_sleep 400 1100            # 点击前的"看一眼"停顿
    $ADB shell input tap $x $y
    rnd_sleep 1200 2600           # 点击后等页面响应
    ;;
  swipe)
    # 滑动时长随机 380-720ms，落点抖动
    dur=$(( 380 + RANDOM % 340 ))
    rnd_sleep 500 1400
    $ADB shell input swipe $(jitter $2) $(jitter $3) $(jitter $4) $(jitter $5) $dur
    rnd_sleep 1500 3000           # 滑完"浏览"一会儿
    ;;
  text)
    # 中文走 ADBKeyboard 的 base64 通道。
    # 关键：借用键盘 → 输入 → 立刻还回去，绝不长期占用（用户随时可能要自己打字）
    [ "$#" -eq 2 ] || { usage; exit 2; }
    PREV_IME=$($ADB shell settings get secure default_input_method | tr -d '\r')
    RESTORE_IME="${ANDROID_IME:-$PREV_IME}"
    case "$RESTORE_IME" in
      ''|null|*adbkeyboard*) echo 'ERR 请先切回常用输入法，或设置 ANDROID_IME 为其组件名。' >&2; exit 1 ;;
    esac
    restore_ime() { $ADB shell ime set "$RESTORE_IME" >/dev/null; }
    trap restore_ime EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    $ADB shell ime set com.android.adbkeyboard/.AdbIME >/dev/null
    rnd_sleep 800 1500
    B64=$(printf '%s' "$2" | base64 | tr -d '\n')
    $ADB shell am broadcast -a ADB_INPUT_B64 --es msg "$B64" >/dev/null
    rnd_sleep 900 1800            # 模拟打字后的停顿
    # EXIT trap 在正常结束、输入失败或收到终止信号时归还输入法。
    ;;
  ime_back)
    : "${ANDROID_IME:?请设置 ANDROID_IME 为常用输入法组件名}"
    $ADB shell ime set "$ANDROID_IME" >/dev/null
    ;;
  key)
    rnd_sleep 400 1000
    $ADB shell input keyevent "KEYCODE_$2"
    rnd_sleep 1200 2400
    ;;
  shot)
    name="${2:-s}"
    mkdir -p "$SHOT_DIR"
    $ADB exec-out screencap -p > "$SHOT_DIR/$name.png"
    echo "$SHOT_DIR/$name.png"
    ;;
  wait)
    # 长停顿，模拟人在读内容
    rnd_sleep 3000 7000
    ;;
  focus)
    $ADB shell dumpsys window | grep mCurrentFocus
    ;;
  *) usage; exit 2 ;;
esac
