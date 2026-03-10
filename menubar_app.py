#!/usr/bin/env python3
"""
OpenClaw 🦞 macOS Menu Bar App
──────────────────────────────
A lightweight status-bar companion that lets you:
  • Check gateway status at a glance (green/red dot)
  • Start / Stop / Restart the gateway daemon
  • Open Dashboard, TUI, or Telegram bot
  • View channel status (Telegram etc.)
  • Quick-access to config files

Requires: rumps, pyobjc  (pip3 install rumps)
Usage:    python3 menubar_app.py
Package:  py2app → OpenClaw Menu Bar.app
"""

import rumps
import subprocess
import json
import os
import webbrowser
import threading
import urllib.request

# ─── Helpers ────────────────────────────────────────────────────────────

def _env():
    """Return env dict with PATH including Homebrew."""
    e = os.environ.copy()
    e["PATH"] = "/usr/local/bin:/opt/homebrew/bin:" + e.get("PATH", "")
    e["LANG"] = "en_US.UTF-8"
    return e

def _run(args, timeout=10):
    """Run a CLI command and return (ok, stdout+stderr)."""
    try:
        r = subprocess.run(
            args, capture_output=True, text=True,
            timeout=timeout, env=_env()
        )
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out
    except FileNotFoundError:
        return False, "openclaw 未安裝"
    except subprocess.TimeoutExpired:
        return False, "指令逾時"
    except Exception as e:
        return False, str(e)

def _run_bg(args):
    """Run command in background, no wait."""
    try:
        subprocess.Popen(args, env=_env(),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def _get_bot_username():
    """Try to read bot token from config and resolve username via Telegram API."""
    try:
        cfg_path = os.path.expanduser("~/.openclaw/openclaw.json")
        if not os.path.exists(cfg_path):
            return None
        with open(cfg_path) as f:
            cfg = json.load(f)
        token = cfg.get("channels", {}).get("telegram", {}).get("botToken", "")
        if not token or ":" not in token:
            return None
        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url, headers={"User-Agent": "OpenClaw-MenuBar"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                return data["result"].get("username")
    except Exception:
        pass
    return None


# ─── Menu Bar App ───────────────────────────────────────────────────────

class OpenClawMenuBar(rumps.App):
    def __init__(self):
        super().__init__(
            name="OpenClaw",
            title="🦞",
            quit_button=None,  # We'll add our own
        )

        # ── Build menu ──
        self.status_item = rumps.MenuItem("⏳ 檢查中…", callback=None)
        self.status_item.set_callback(None)

        self.menu = [
            self.status_item,
            None,  # separator
            rumps.MenuItem("▶️ 啟動 Gateway", callback=self.start_gateway),
            rumps.MenuItem("⏹ 停止 Gateway", callback=self.stop_gateway),
            rumps.MenuItem("🔄 重新啟動", callback=self.restart_gateway),
            None,
            rumps.MenuItem("🌐 控制面板 (Dashboard)", callback=self.open_dashboard),
            rumps.MenuItem("💻 終端互動 (TUI)", callback=self.open_tui),
            rumps.MenuItem("📱 開啟 Telegram Bot", callback=self.open_telegram),
            None,
            rumps.MenuItem("📡 頻道狀態", callback=self.show_channels),
            rumps.MenuItem("🔧 安裝常駐服務", callback=self.install_daemon),
            rumps.MenuItem("📂 開啟設定檔", callback=self.open_config),
            rumps.MenuItem("📂 開啟 .env", callback=self.open_env),
            None,
            rumps.MenuItem("🦞 ClawHub Skills", callback=self.open_clawhub),
            rumps.MenuItem("📖 關於 OpenClaw", callback=self.show_about),
            None,
            rumps.MenuItem("結束 OpenClaw Menu Bar", callback=self.quit_app),
        ]

        # Start periodic status check
        self._check_timer = rumps.Timer(self._update_status, 15)
        self._check_timer.start()
        # Also check immediately
        threading.Thread(target=self._update_status_now, daemon=True).start()

    # ─── Status polling ────────────────────────────────────────────────

    def _update_status(self, _=None):
        threading.Thread(target=self._update_status_now, daemon=True).start()

    def _update_status_now(self):
        ok, out = _run(["openclaw", "daemon", "status"])
        if ok and "running" in out.lower():
            title = "🦞"
            status_text = "🟢 Gateway 運行中"
        elif ok:
            title = "🦞💤"
            status_text = "🟡 Gateway 已停止"
        else:
            title = "🦞❌"
            status_text = "🔴 Gateway 離線"

        rumps.Timer(lambda _: None, 0).stop()  # force main thread
        self.title = title
        self.status_item.title = status_text

    # ─── Gateway controls ──────────────────────────────────────────────

    @rumps.clicked("▶️ 啟動 Gateway")
    def start_gateway(self, _=None):
        ok, out = _run(["openclaw", "daemon", "start"], timeout=15)
        if ok:
            rumps.notification("OpenClaw", "Gateway 已啟動", "🟢 服務已開始運行", sound=False)
        else:
            rumps.notification("OpenClaw", "啟動失敗", out[:200], sound=True)
        self._update_status()

    @rumps.clicked("⏹ 停止 Gateway")
    def stop_gateway(self, _=None):
        ok, out = _run(["openclaw", "daemon", "stop"], timeout=15)
        if ok:
            rumps.notification("OpenClaw", "Gateway 已停止", "🔴 服務已關閉", sound=False)
        else:
            rumps.notification("OpenClaw", "停止失敗", out[:200], sound=True)
        self._update_status()

    @rumps.clicked("🔄 重新啟動")
    def restart_gateway(self, _=None):
        rumps.notification("OpenClaw", "正在重新啟動…", "⏳", sound=False)
        _run(["openclaw", "daemon", "stop"], timeout=10)
        ok, out = _run(["openclaw", "daemon", "start"], timeout=15)
        if ok:
            rumps.notification("OpenClaw", "已重新啟動", "🟢 Gateway 運行中", sound=False)
        else:
            rumps.notification("OpenClaw", "重新啟動失敗", out[:200], sound=True)
        self._update_status()

    # ─── Open tools ────────────────────────────────────────────────────

    @rumps.clicked("🌐 控制面板 (Dashboard)")
    def open_dashboard(self, _=None):
        _run_bg(["openclaw", "dashboard"])

    @rumps.clicked("💻 終端互動 (TUI)")
    def open_tui(self, _=None):
        subprocess.Popen([
            "osascript", "-e",
            'tell application "Terminal" to do script "openclaw tui"'
        ])

    @rumps.clicked("📱 開啟 Telegram Bot")
    def open_telegram(self, _=None):
        def do():
            username = _get_bot_username()
            if username:
                webbrowser.open(f"https://t.me/{username}")
            else:
                webbrowser.open("https://t.me/")
        threading.Thread(target=do, daemon=True).start()

    # ─── Info & config ─────────────────────────────────────────────────

    @rumps.clicked("📡 頻道狀態")
    def show_channels(self, _=None):
        ok, out = _run(["openclaw", "channels", "status"])
        rumps.alert(
            title="📡 頻道狀態",
            message=out if out else "(無資訊)",
            ok="好"
        )

    @rumps.clicked("🔧 安裝常駐服務")
    def install_daemon(self, _=None):
        ok, out = _run(["openclaw", "daemon", "install"], timeout=30)
        if ok:
            rumps.notification("OpenClaw", "常駐服務已安裝", "✅ Gateway 將在開機時自動啟動", sound=False)
        else:
            rumps.alert(title="安裝失敗", message=out[:300], ok="好")
        self._update_status()

    @rumps.clicked("📂 開啟設定檔")
    def open_config(self, _=None):
        cfg = os.path.expanduser("~/.openclaw/openclaw.json")
        if os.path.exists(cfg):
            subprocess.Popen(["open", cfg])
        else:
            rumps.alert(title="找不到設定檔", message=cfg, ok="好")

    @rumps.clicked("📂 開啟 .env")
    def open_env(self, _=None):
        env_file = os.path.expanduser("~/.openclaw/.env")
        if os.path.exists(env_file):
            subprocess.Popen(["open", env_file])
        else:
            rumps.alert(title="找不到 .env", message=env_file, ok="好")

    @rumps.clicked("🦞 ClawHub Skills")
    def open_clawhub(self, _=None):
        webbrowser.open("https://clawhub.ai/")

    @rumps.clicked("📖 關於 OpenClaw")
    def show_about(self, _=None):
        ok, out = _run(["openclaw", "--version"])
        ver = out.strip() if ok else "未知版本"
        rumps.alert(
            title="🦞 OpenClaw",
            message=f"版本：{ver}\n\n"
                    f"OpenClaw 是一個 AI 助理平台，\n"
                    f"透過 Telegram、終端、網頁等管道為您服務。\n\n"
                    f"clawhub.ai",
            ok="好"
        )

    @rumps.clicked("結束 OpenClaw Menu Bar")
    def quit_app(self, _=None):
        rumps.quit_application()


# ─── Entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    OpenClawMenuBar().run()
