#!/bin/bash
# 人类化 ADB 操作封装 —— 防风控 + 提高准确率
# 用法: ./hput.sh tap X Y | swipe X1 Y1 X2 Y2 | text "内容" | key HOME | shot [名字] | wait

SHOT_DIR="/private/tmp/claude-501/-Users-a1-6-phone-agent/cad8646b-0e2a-49c8-8877-749cd6d3f3ed/scratchpad"
ADB=adb

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
    PREV_IME=$($ADB shell settings get secure default_input_method | tr -d '\r')
    $ADB shell ime set com.android.adbkeyboard/.AdbIME >/dev/null
    rnd_sleep 800 1500
    B64=$(printf '%s' "$2" | base64)
    $ADB shell am broadcast -a ADB_INPUT_B64 --es msg "$B64" >/dev/null
    rnd_sleep 900 1800            # 模拟打字后的停顿
    # 还回原来的输入法（原来是什么就还什么，不写死搜狗）
    case "$PREV_IME" in
      *adbkeyboard*) $ADB shell ime set com.sohu.inputmethod.sogou.xiaomi/.SogouIME >/dev/null ;;
      "" )           $ADB shell ime set com.sohu.inputmethod.sogou.xiaomi/.SogouIME >/dev/null ;;
      *)             $ADB shell ime set "$PREV_IME" >/dev/null ;;
    esac
    ;;
  ime_back)
    $ADB shell ime set com.sohu.inputmethod.sogou.xiaomi/.SogouIME >/dev/null
    ;;
  key)
    rnd_sleep 400 1000
    $ADB shell input keyevent "KEYCODE_$2"
    rnd_sleep 1200 2400
    ;;
  shot)
    name="${2:-s}"
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
esac
