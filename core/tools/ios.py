#!/usr/bin/env python3
"""iPhone 操作命令行（经 WebDriverAgent，先跑 core/tools/ios_wda.sh 拿到 READY）

坐标一律用「点」(pt)，以设备实际窗口尺寸为准。shot 存的图已缩到点尺寸，图上坐标 = tap 坐标。

  ios.py status                  只读检查 WDA 状态，不创建会话
  ios.py shot [路径]              截图（默认 /tmp/ios.png），打印尺寸
  ios.py tree [关键词]            读控件树，只列有文字的控件：类型 文字 中心坐标；给关键词则只列包含它的
  ios.py tap X Y                  点坐标
  ios.py tapt 文字 [序号]          点文字完全匹配的控件（找不到退而用包含匹配），多个时取第 序号 个（默认 0）
  ios.py swipe X1 Y1 X2 Y2 [秒]   滑动；秒数是起点按住时长，默认 0.05（按久了会变成长按）
  ios.py type 文字                往当前焦点输入框输入（支持中文、换行）
  ios.py clipboard 文件 包名      把 UTF-8 文件放入手机剪贴板、核对全文后切回指定 App，供界面粘贴
  ios.py clipboard-check 文件 包名  核对从编辑框全选复制的全文；不一致立即报错
  ios.py home                     回桌面
  ios.py launch 包名               启动/切到 App，如 com.xingin.discover
  ios.py url 网址                 用手机默认浏览器打开网址
  ios.py apps [关键词]             列出手机上的 App 和包名
每个动作执行完打印 OK；失败打印 ERR 和原因，退出码 1。
"""
import json, os, shlex, subprocess, sys, urllib.request
from pathlib import Path


def load_config():
    """读取仓库根目录 .env 的简单 KEY=value 配置；进程环境优先。"""
    path = Path(__file__).resolve().parents[2] / ".env"
    if not path.exists():
        return
    allowed = {"IOS_UDID", "WDA_TEAM_ID", "WDA_PROJECT_DIR", "WDA_DERIVED_DATA",
               "WDA_RUNNER_BUNDLE_ID", "WDA_LOCAL_PORT", "WDA_BASE_URL"}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw.startswith("export "):
            raw = raw[7:]
        key, sep, value = raw.partition("=")
        key = key.strip()
        if not sep or key not in allowed:
            continue
        parts = shlex.split(value, comments=True)
        if len(parts) > 1:
            raise RuntimeError(f".env 第 {number} 行：包含空格的值需要引号")
        os.environ.setdefault(key, os.path.expanduser(os.path.expandvars(parts[0] if parts else "")))


load_config()
BASE = os.environ.get("WDA_BASE_URL") or "http://127.0.0.1:" + os.environ.get("WDA_LOCAL_PORT", "8100")
BASE = BASE.rstrip("/")
UDID = os.environ.get("IOS_UDID", "")
RUNNER_BUNDLE_ID = os.environ.get("WDA_RUNNER_BUNDLE_ID", "")
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕过本机全局代理


def req(method, path, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    with _opener.open(r, timeout=timeout) as resp:
        v = json.loads(resp.read()).get("value")
    if isinstance(v, dict) and v.get("error"):
        raise RuntimeError(f"{v['error']}: {v.get('message', '')[:200]}")
    return v


_sid = None


def sid():
    """复用 WDA 当前会话，没有才新建"""
    global _sid
    if _sid is None:
        r = urllib.request.Request(BASE + "/status")
        with _opener.open(r, timeout=10) as resp:
            _sid = json.loads(resp.read()).get("sessionId")
        if not _sid:
            _sid = req("POST", "/session", {"capabilities": {"alwaysMatch": {}}})["sessionId"]
    return _sid


def walk(node, out):
    label = " | ".join(dict.fromkeys(str(v) for v in (node.get("label"), node.get("name"), node.get("value")) if v))
    r = node.get("rect") or {}
    if label and r.get("width") and r.get("height") and node.get("isVisible", "1") in ("1", True, 1):
        out.append((node.get("type", "").replace("XCUIElementType", ""), str(label),
                    int(r["x"] + r["width"] / 2), int(r["y"] + r["height"] / 2)))
    for c in node.get("children") or []:
        walk(c, out)
    return out


def element_id(element):
    return element.get("element-6066-11e4-a52e-4f735466cecf") or element["ELEMENT"]


def main(a):
    cmd = a[0] if a else "help"
    if cmd in ("help", "--help", "-h"):
        print(__doc__)
        return
    counts = {"status": (0, 0), "shot": (0, 1), "tree": (0, 1), "tap": (2, 2),
              "tapt": (1, 2), "swipe": (4, 5), "type": (1, 1), "clipboard": (2, 2),
              "clipboard-check": (2, 2), "home": (0, 0), "launch": (1, 1),
              "url": (1, 1), "apps": (0, 1)}
    if cmd not in counts:
        raise RuntimeError(f"未知命令：{cmd}；使用 --help 查看用法")
    low, high = counts[cmd]
    if not low <= len(a) - 1 <= high:
        raise RuntimeError(f"{cmd} 参数数量不正确；使用 --help 查看用法")
    if cmd == "status":
        print(json.dumps(req("GET", "/status", timeout=5), ensure_ascii=False))
    elif cmd == "shot":
        import base64
        path = a[1] if len(a) > 1 else "/tmp/ios.png"
        Path(path).write_bytes(base64.b64decode(req("GET", "/screenshot")))
        w = req("GET", "/session/%s/window/size" % sid())["width"]
        subprocess.run(["sips", "--resampleWidth", str(int(w)), path], capture_output=True, check=True)
        print(f"OK {path}（已缩放到点坐标，宽 {int(w)}）")
    elif cmd == "tree":
        kw = a[1] if len(a) > 1 else None
        for t, l, x, y in walk(req("GET", "/source?format=json", timeout=120), []):
            if kw is None or kw in l:
                print(f"{t}\t{l[:60]}\t{x},{y}")
    elif cmd == "tap":
        req("POST", "/session/%s/wda/tap" % sid(), {"x": float(a[1]), "y": float(a[2])}); print("OK")
    elif cmd == "tapt":
        text, idx = a[1], int(a[2]) if len(a) > 2 else 0
        if idx < 0:
            raise RuntimeError("控件序号必须为非负整数")
        s = sid()
        q = text.replace("\\", "\\\\").replace("'", "\\'")
        for pred in (f"label == '{q}' OR name == '{q}'", f"label CONTAINS '{q}' OR name CONTAINS '{q}'"):
            els = req("POST", f"/session/{s}/elements", {"using": "predicate string", "value": pred})
            els = [e for e in els if req("GET", f"/session/{s}/element/{element_id(e)}/displayed")]
            if len(els) > idx:
                req("POST", f"/session/{s}/element/{element_id(els[idx])}/click"); print("OK"); return
        raise RuntimeError(f"找不到可见控件：{text}")
    elif cmd == "swipe":
        x1, y1, x2, y2 = map(float, a[1:5])
        req("POST", "/session/%s/wda/dragfromtoforduration" % sid(),
            {"fromX": x1, "fromY": y1, "toX": x2, "toY": y2, "duration": float(a[5]) if len(a) > 5 else 0.05})
        print("OK")
    elif cmd == "type":
        req("POST", "/session/%s/wda/keys" % sid(), {"value": list(a[1])}); print("OK")
    elif cmd in ("clipboard", "clipboard-check"):
        import base64
        if len(a) != 3:
            raise RuntimeError('用法：clipboard UTF-8文件 切回的App包名')
        if not RUNNER_BUNDLE_ID:
            raise RuntimeError("请配置 WDA_RUNNER_BUNDLE_ID（已安装的 .xctrunner 包名）")
        content = Path(a[1]).read_text(encoding='utf-8')
        s = sid()
        req('POST', f'/session/{s}/wda/apps/activate',
            {'bundleId': RUNNER_BUNDLE_ID})
        try:
            if cmd == 'clipboard':
                req('POST', f'/session/{s}/wda/setPasteboard',
                    {'content': base64.b64encode(content.encode()).decode(), 'contentType': 'plaintext'})
            actual = req('POST', f'/session/{s}/wda/getPasteboard', {'contentType': 'plaintext'})
            decoded = base64.b64decode(actual).decode()
            if cmd == 'clipboard-check' and not decoded and content:
                raise RuntimeError('未读取到其他App复制的剪贴板内容，请在编辑界面和发布页核对全文')
            if decoded != content:
                raise RuntimeError('手机剪贴板全文核对失败')
        finally:
            req('POST', f'/session/{s}/wda/apps/activate', {'bundleId': a[2]})
        print(f'OK 剪贴板全文已核对：{len(content)} 字符')
    elif cmd == "home":
        req("POST", "/wda/homescreen"); print("OK")
    elif cmd == "launch":
        req("POST", "/session/%s/wda/apps/launch" % sid(), {"bundleId": a[1]}); print("OK")
    elif cmd == "url":
        req('POST', f'/session/{sid()}/url', {'url': a[1]}); print('OK')
    elif cmd == "apps":
        if not UDID:
            raise RuntimeError("请在 .env 或环境变量中配置 IOS_UDID")
        out = subprocess.run(["xcrun", "devicectl", "device", "info", "apps", "--device", UDID,
                              "--include-all-apps"], capture_output=True, text=True, check=True).stdout
        for line in out.splitlines()[3:]:
            if len(a) < 2 or a[1].lower() in line.lower():
                print(line.rstrip())
    else:
        print(__doc__)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as e:
        print("ERR", e); sys.exit(1)
