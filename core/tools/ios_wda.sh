#!/bin/bash
# Manage this checkout's WDA runner and USB forwarding processes.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
ACTION=${1:-start}
case "$ACTION" in
  help|-h|--help)
    cat <<'HELP'
用法：core/tools/ios_wda.sh [start|status|check|stop]
  start   启动已构建的 WDA 与 USB 转发；就绪输出 READY
  status  只读查询本机 WDA /status，不创建会话
  check   检查本地工具、配置和构建目录，不连接或操作手机
  stop    仅停止此仓库记录且核对归属的进程
配置：复制根目录 .env.example 为 .env，填入自己的设备和签名信息。
HELP
    exit 0;;
  start|status|check|stop) ;;
  *) echo "ERR 未知命令：$ACTION；使用 --help 查看用法" >&2; exit 2;;
esac
# The .env file is local shell configuration. Environment values take precedence.
for key in IOS_UDID WDA_TEAM_ID WDA_PROJECT_DIR WDA_DERIVED_DATA WDA_RUNNER_BUNDLE_ID WDA_LOCAL_PORT WDA_BASE_URL; do
  if declare -p "$key" >/dev/null 2>&1; then
    printf -v "saved_$key" '%s' "${!key}"
  fi
done
if [[ -f "$ROOT/.env" ]]; then
  set -a
  source "$ROOT/.env"
  set +a
fi
for key in IOS_UDID WDA_TEAM_ID WDA_PROJECT_DIR WDA_DERIVED_DATA WDA_RUNNER_BUNDLE_ID WDA_LOCAL_PORT WDA_BASE_URL; do
  saved="saved_$key"
  if declare -p "$saved" >/dev/null 2>&1; then printf -v "$key" '%s' "${!saved}"; fi
done
UDID=${IOS_UDID:-}
TEAM=${WDA_TEAM_ID:-}
WDA=${WDA_PROJECT_DIR:-$HOME/code/WebDriverAgent}
DERIVED=${WDA_DERIVED_DATA:-$WDA/build}
PORT=${WDA_LOCAL_PORT:-8100}
DEVICE_PORT=8100
BASE=${WDA_BASE_URL:-http://127.0.0.1:$PORT}
BASE=${BASE%/}
RUNTIME="$ROOT/.runtime/wda-$PORT"
LOG="$RUNTIME/xcodebuild.log"
fail() { echo "ERR $*" >&2; exit 1; }
[[ "$PORT" =~ ^[0-9]+$ && "$DEVICE_PORT" =~ ^[0-9]+$ ]] || fail "端口必须是数字"
ready() {
  curl --silent --show-error --noproxy '*' --max-time 3 "$BASE/status" 2>/dev/null |
    python3 -c 'import json,sys; d=json.load(sys.stdin); v=d.get("value"); sys.exit(0 if isinstance(v,dict) and not v.get("error") and ("build" in v or "os" in v or v.get("ready") is True) else 1)' 2>/dev/null
}
if [[ "$ACTION" == status ]]; then
  ready && { echo "READY $BASE"; exit 0; }
  fail "WDA 未就绪：$BASE"
fi
# A PID is ours only when the current process command equals the recorded command.
owned() {
  local name=$1 pid actual expected
  [[ -f "$RUNTIME/$name.pid" && -f "$RUNTIME/$name.command" ]] || return 1
  read -r pid < "$RUNTIME/$name.pid"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  actual=$(ps -p "$pid" -o command= 2>/dev/null) || return 1
  expected=$(cat "$RUNTIME/$name.command")
  [[ -n "$actual" && "$actual" == "$expected" ]]
}
if [[ "$ACTION" == stop ]]; then
  for name in runner proxy; do
    if owned "$name"; then
      read -r pid < "$RUNTIME/$name.pid"
      kill "$pid"
      echo "STOPPED $name ($pid)"
      rm -f "$RUNTIME/$name.pid" "$RUNTIME/$name.command"
    else
      echo "SKIP ${name}：没有核实为本仓库启动的进程"
    fi
  done
  exit 0
fi
for tool in python3 curl xcodebuild iproxy; do
  command -v "$tool" >/dev/null || fail "缺少 $tool，见 core/iphone-setup.md"
done
[[ -n "$UDID" && -n "$TEAM" ]] || fail "请配置 IOS_UDID 和 WDA_TEAM_ID，见 .env.example"
[[ -d "$WDA/WebDriverAgent.xcodeproj" ]] || fail "找不到 $WDA/WebDriverAgent.xcodeproj"
[[ -d "$DERIVED/Build/Products" ]] || fail "请先 build-for-testing；构建步骤见 core/iphone-setup.md"
if [[ "$ACTION" == check ]]; then
  echo "OK 本地依赖、配置和构建目录齐全；未检查真机连接及签名有效期"
  exit 0
fi
[[ "$BASE" == "http://127.0.0.1:$PORT" || "$BASE" == "http://localhost:$PORT" ]] || fail "start 管理本机 USB 转发；自建 WDA 请直接使用 ios.py 或 status"
if owned proxy; then
  command_line=$(cat "$RUNTIME/proxy.command")
  [[ " $command_line " == *" -u $UDID "* ]] || fail "当前端口由另一设备的转发占用；请换 WDA_LOCAL_PORT 或先核对后停止旧服务"
fi
if owned runner; then
  command_line=$(cat "$RUNTIME/runner.command")
  [[ " $command_line " == *" id=$UDID "* ]] || fail "已记录的 Runner 属于另一设备；请核对旧服务"
fi
if ready; then
  owned proxy || fail "检测到未由此仓库管理的 WDA；请先核对其设备，或改用空闲的 WDA_LOCAL_PORT 后重试"
  echo READY
  exit 0
fi
mkdir -p "$RUNTIME"
mkdir "$RUNTIME/start.lock" 2>/dev/null || fail "同一仓库的启动正在进行：$RUNTIME/start.lock"
trap 'rmdir "$RUNTIME/start.lock" 2>/dev/null || true' EXIT
record() {
  local name=$1 pid=$2
  printf '%s\n' "$pid" > "$RUNTIME/$name.pid"
  # Let nohup exec the actual process before recording its command.
  sleep 1
  ps -p "$pid" -o command= > "$RUNTIME/$name.command" || fail "$name 已退出，查看 $RUNTIME 下的日志"
}
if ! owned proxy; then
  if python3 - "$PORT" <<'PY'
import socket, sys
with socket.socket() as s:
    s.settimeout(1)
    sys.exit(0 if s.connect_ex(('127.0.0.1', int(sys.argv[1]))) == 0 else 1)
PY
  then fail "本机 $PORT 端口已被占用但 WDA 未就绪；请检查占用者或修改 WDA_LOCAL_PORT"; fi
  nohup iproxy "$PORT" "$DEVICE_PORT" -u "$UDID" > "$RUNTIME/iproxy.log" 2>&1 </dev/null &
  record proxy "$!"
fi
if ! owned runner; then
  nohup xcodebuild test-without-building -project "$WDA/WebDriverAgent.xcodeproj" \
    -scheme WebDriverAgentRunner -destination "id=$UDID" -derivedDataPath "$DERIVED" \
    "DEVELOPMENT_TEAM=$TEAM" > "$LOG" 2>&1 </dev/null &
  record runner "$!"
fi
for ((attempt=1; attempt<=20; attempt++)); do
  ready && { echo READY; exit 0; }
  owned runner || fail "WDA 进程已退出，查看 $LOG"
  owned proxy || fail "USB 转发已退出，查看 $RUNTIME/iproxy.log"
  if grep -q 'TEST EXECUTE FAILED' "$LOG"; then fail "WDA 启动失败，查看 $LOG"; fi
  sleep 3
done
fail "WDA 启动超时，查看 $LOG；处理解锁、证书信任或 UI 自动化后重试"
