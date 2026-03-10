#!/opt/homebrew/bin/python3.13
"""
OpenClaw macOS Graphical Installer
===================================
Full wizard: Install → Telegram → Model → Chat Test → Skills → Done
"""

import os
import platform
import secrets
import shutil
import subprocess
import sys
import threading
import webbrowser
import json
import re
import hashlib
import base64
import socket
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont, scrolledtext

# ─── Fix PATH for .app bundle ────────────────────────────────────────────────
# When launched as .app, PATH is minimal (/usr/bin:/bin).
# Add common macOS paths so shutil.which() and subprocess can find node/npm/brew.
_EXTRA_PATHS = [
    "/opt/homebrew/bin",
    "/opt/homebrew/sbin",
    "/usr/local/bin",
    "/usr/local/sbin",
    os.path.expanduser("~/.nvm/versions/node/*/bin"),  # nvm
    os.path.expanduser("~/n/bin"),                       # n
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
]
_current = os.environ.get("PATH", "")
_to_add = [p for p in _EXTRA_PATHS if p not in _current and "*" not in p]
# Also resolve nvm glob
import glob as _glob
for _pattern in [os.path.expanduser("~/.nvm/versions/node/*/bin")]:
    for _found in sorted(_glob.glob(_pattern), reverse=True):  # newest first
        if _found not in _current:
            _to_add.insert(0, _found)
os.environ["PATH"] = ":".join(_to_add) + ":" + _current

# ─── Constants ────────────────────────────────────────────────────────────────
APP_NAME = "OpenClaw Installer"
OPENCLAW_WEBSITE = "https://openclaw.ai/"
INSTALL_SCRIPT_URL = "https://openclaw.ai/install.sh"
REQUIRED_NODE_MAJOR = 22
WINDOW_WIDTH = 750
WINDOW_HEIGHT = 600

# Colors – lobster theme
C_BG = "#1a1a2e"
C_BG2 = "#16213e"
C_ACCENT = "#e94560"
C_ACCENT2 = "#ff6b81"
C_TEXT = "#eaeaea"
C_DIM = "#a0a0b0"
C_OK = "#2ecc71"
C_WARN = "#f39c12"
C_ERR = "#e74c3c"
C_INPUT = "#0f3460"
C_BTN = "#e94560"
C_BTN_FG = "#ffffff"

# ─── Provider metadata & dynamic model detection ────────────────────────────
PROVIDER_META = {
    "anthropic": {"env_key": "ANTHROPIC_API_KEY",
                  "url": "https://console.anthropic.com/settings/keys", "label": "Anthropic"},
    "openai":    {"env_key": "OPENAI_API_KEY",
                  "url": "https://platform.openai.com/api-keys",       "label": "OpenAI"},
    "google":    {"env_key": "GOOGLE_API_KEY",
                  "url": "https://aistudio.google.com/apikey",         "label": "Google"},
}

# ─── OpenAI OAuth PKCE ────────────────────────────────────────────────────
OPENAI_AUTH_URL = "https://auth.openai.com/authorize"
OPENAI_TOKEN_URL = "https://auth.openai.com/oauth/token"
OPENAI_CLIENT_ID = "pdlLIX2Y72MIl2rhLhTE9VV9bN905kBh"  # ChatGPT public PKCE client
OPENAI_SCOPE = "openid profile email offline_access"
OPENAI_AUDIENCE = "https://api.openai.com/v1"

# Regex patterns to match model families on OpenRouter; latest by timestamp wins
MODEL_FAMILIES = [
    {"re": r"^anthropic/claude-.*sonnet",   "desc": "最佳平衡（推薦）"},
    {"re": r"^anthropic/claude-.*opus",     "desc": "最強推理能力"},
    {"re": r"^openai/gpt-",                 "desc": "OpenAI 旗艦模型"},
    {"re": r"^openai/o\d",                  "desc": "強推理模型"},
    {"re": r"^google/gemini-.*pro",          "desc": "Google 最新模型"},
]

# Hardcoded fallback (used when network unavailable)
MODELS_FALLBACK = [
    {"id": "anthropic/claude-sonnet-4.6", "name": "Claude Sonnet 4.6", "provider": "Anthropic",
     "desc": "最佳平衡（推薦）", "env_key": "ANTHROPIC_API_KEY", "url": "https://console.anthropic.com/settings/keys"},
    {"id": "anthropic/claude-opus-4.6", "name": "Claude Opus 4.6", "provider": "Anthropic",
     "desc": "最強推理能力", "env_key": "ANTHROPIC_API_KEY", "url": "https://console.anthropic.com/settings/keys"},
    {"id": "openai/gpt-5.4", "name": "GPT-5.4", "provider": "OpenAI",
     "desc": "OpenAI 旗艦模型", "env_key": "OPENAI_API_KEY", "url": "https://platform.openai.com/api-keys"},
    {"id": "openai/o3-deep-research", "name": "o3 Deep Research", "provider": "OpenAI",
     "desc": "強推理模型", "env_key": "OPENAI_API_KEY", "url": "https://platform.openai.com/api-keys"},
    {"id": "google/gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro", "provider": "Google",
     "desc": "Google 最新模型", "env_key": "GOOGLE_API_KEY", "url": "https://aistudio.google.com/apikey"},
]


class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.configure(bg=C_BG)

        # Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (WINDOW_WIDTH // 2)
        y = (self.winfo_screenheight() // 2) - (WINDOW_HEIGHT // 2)
        self.geometry(f"+{x}+{y}")

        # State
        self.install_channel = tk.StringVar(value="latest")
        self.install_daemon = tk.BooleanVar(value=True)
        self.run_onboard = tk.BooleanVar(value=True)
        self.models = list(MODELS_FALLBACK)
        self.models_fetched = False
        self.selected_model = tk.StringVar(value=MODELS_FALLBACK[0]["id"])
        self.api_key_var = tk.StringVar()
        self.telegram_token_var = tk.StringVar()
        self.gateway_mode = tk.StringVar(value="local")
        self.gateway_token = tk.StringVar()
        self.gen_token = tk.BooleanVar(value=True)
        self.install_process = None
        self.install_cancelled = False
        self.chat_history = []

        # Fonts
        self.f_title = tkfont.Font(family="Helvetica Neue", size=22, weight="bold")
        self.f_sub = tkfont.Font(family="Helvetica Neue", size=14)
        self.f_body = tkfont.Font(family="Helvetica Neue", size=12)
        self.f_small = tkfont.Font(family="Helvetica Neue", size=10)
        self.f_mono = tkfont.Font(family="Menlo", size=11)
        self.f_chat = tkfont.Font(family="Helvetica Neue", size=13)

        self._setup_styles()

        self.pages = []
        self.current_page = 0
        self.container = tk.Frame(self, bg=C_BG)
        self.container.pack(fill="both", expand=True)

        # Build all 9 pages
        self._build_p0_welcome()      # 0: Welcome
        self._build_p1_check()        # 1: Environment Check
        self._build_p2_options()      # 2: Install Options
        self._build_p3_install()      # 3: Install Progress
        self._build_p4_gateway()      # 4: Gateway Setup  ← NEW
        self._build_p5_telegram()     # 5: Telegram
        self._build_p6_model()        # 6: Model Selection
        self._build_p7_chat()         # 7: Chat Test
        self._build_p8_done()         # 8: Done

        self._show_page(0)

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        # ── Normal (dark bg) ──
        s.configure("TCheckbutton", background=C_BG, foreground=C_TEXT,
                    font=("Helvetica Neue", 12), indicatorsize=20,
                    indicatormargin=6, indicatorrelief="flat")
        s.map("TCheckbutton",
              background=[("active", C_BG), ("!active", C_BG)],
              indicatorcolor=[("selected", C_ACCENT), ("!selected", C_BG2)],
              indicatorrelief=[("selected", "flat"), ("!selected", "sunken")])

        s.configure("TRadiobutton", background=C_BG, foreground=C_TEXT,
                    font=("Helvetica Neue", 12), indicatorsize=20,
                    indicatormargin=6)
        s.map("TRadiobutton",
              background=[("active", C_BG), ("!active", C_BG)],
              indicatorcolor=[("selected", C_ACCENT), ("!selected", C_BG2)])

        # ── Dark variants for C_INPUT panels ──
        s.configure("Dark.TCheckbutton", background=C_INPUT, foreground=C_TEXT,
                    font=("Helvetica Neue", 12), indicatorsize=20,
                    indicatormargin=6, indicatorrelief="flat")
        s.map("Dark.TCheckbutton",
              background=[("active", C_INPUT), ("!active", C_INPUT)],
              indicatorcolor=[("selected", C_ACCENT), ("!selected", "#1a1a2e")],
              indicatorrelief=[("selected", "flat"), ("!selected", "sunken")])

        s.configure("Dark.TRadiobutton", background=C_INPUT, foreground=C_TEXT,
                    font=("Helvetica Neue", 12), indicatorsize=20,
                    indicatormargin=6)
        s.map("Dark.TRadiobutton",
              background=[("active", C_INPUT), ("!active", C_INPUT)],
              indicatorcolor=[("selected", C_ACCENT), ("!selected", "#1a1a2e")])

        s.configure("Horizontal.TProgressbar", troughcolor=C_BG2, background=C_ACCENT, thickness=8)

    # ═══ Helpers ══════════════════════════════════════════════════════════

    def _bind_paste(self, entry):
        """Bind Cmd+V paste on macOS for tk.Entry widgets."""
        def _paste(e):
            try:
                txt = self.clipboard_get()
                if entry.select_present():
                    entry.delete("sel.first", "sel.last")
                entry.insert("insert", txt)
            except tk.TclError:
                pass
            return "break"
        entry.bind("<Command-v>", _paste)
        entry.bind("<Command-V>", _paste)
        # Also bind Cmd+A select-all
        def _select_all(e):
            entry.select_range(0, "end")
            entry.icursor("end")
            return "break"
        entry.bind("<Command-a>", _select_all)
        entry.bind("<Command-A>", _select_all)

    def _make_page(self):
        f = tk.Frame(self.container, bg=C_BG)
        self.pages.append(f)
        return f

    def _show_page(self, i):
        for p in self.pages:
            p.pack_forget()
        self.current_page = i
        self.pages[i].pack(fill="both", expand=True)

    def _nav(self, page, back=True, next_text="下一步 →", next_cmd=None, back_cmd=None):
        nav = tk.Frame(page, bg=C_BG2, height=60)
        nav.pack(side="bottom", fill="x")
        nav.pack_propagate(False)
        if back:
            tk.Button(nav, text="← 上一步", font=self.f_body, bg=C_BG, fg=C_DIM,
                      activebackground=C_BG2, activeforeground=C_TEXT, bd=0, padx=20, pady=10,
                      cursor="hand2", command=back_cmd or (lambda: self._show_page(self.current_page - 1))
                      ).pack(side="left", padx=20)
        if next_text:
            btn = tk.Button(nav, text=next_text, font=self.f_body, bg=C_BTN, fg=C_BTN_FG,
                      activebackground=C_ACCENT2, activeforeground=C_BTN_FG, bd=0, padx=30, pady=10,
                      cursor="hand2", command=next_cmd or (lambda: self._show_page(self.current_page + 1)))
            btn.pack(side="right", padx=20)
            return btn
        return None

    def _section(self, parent, title):
        tk.Label(parent, text=title, font=self.f_sub, bg=C_BG, fg=C_TEXT).pack(anchor="w", pady=(15, 8))
        f = tk.Frame(parent, bg=C_INPUT, padx=15, pady=12)
        f.pack(fill="x")
        return f

    # ═══ Page 0: Welcome ═════════════════════════════════════════════════

    def _build_p0_welcome(self):
        p = self._make_page()
        tk.Frame(p, bg=C_BG, height=40).pack()
        tk.Label(p, text="🦞", font=("Apple Color Emoji", 60), bg=C_BG).pack(pady=(0, 8))
        tk.Label(p, text="歡迎使用 OpenClaw 安裝工具", font=self.f_title, bg=C_BG, fg=C_TEXT).pack(pady=(0, 8))
        tk.Label(p, text="您的個人 AI 助手，跑在自己的裝置上。\n本工具將引導您完成完整的安裝與設定流程。",
                 font=self.f_sub, bg=C_BG, fg=C_DIM, justify="center").pack(pady=(0, 20))

        box = tk.Frame(p, bg=C_INPUT, padx=20, pady=15)
        box.pack(padx=50, fill="x")
        steps = [
            ("1️⃣", "檢查環境 & 安裝 OpenClaw"),
            ("2️⃣", "設定 Gateway 閘道（模式 / Token / 啟動）"),
            ("3️⃣", "連結 Telegram 聊天機器人"),
            ("4️⃣", "選擇 AI 大模型（Claude / GPT / Gemini）"),
            ("5️⃣", "與 🦞 對話測試 & 自動推薦 Skills"),
            ("6️⃣", "完成！開始使用"),
        ]
        for icon, text in steps:
            r = tk.Frame(box, bg=C_INPUT)
            r.pack(anchor="w", pady=4)
            tk.Label(r, text=icon, font=self.f_body, bg=C_INPUT).pack(side="left")
            tk.Label(r, text=f"  {text}", font=self.f_body, bg=C_INPUT, fg=C_TEXT).pack(side="left")

        link = tk.Label(p, text="了解更多 → openclaw.ai", font=self.f_small, bg=C_BG, fg=C_ACCENT, cursor="hand2")
        link.pack(pady=(15, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open(OPENCLAW_WEBSITE))
        self._nav(p, back=False, next_text="開始 →", next_cmd=self._go_check)

    # ═══ Page 1: Environment Check ═══════════════════════════════════════

    def _build_p1_check(self):
        p = self._make_page()
        tk.Label(p, text="🔍 環境檢查", font=self.f_title, bg=C_BG, fg=C_TEXT).pack(pady=(25, 15))

        self.chk_frame = tk.Frame(p, bg=C_BG)
        self.chk_frame.pack(padx=40, fill="x")
        self.chk = {}
        for key, label in [("os","macOS 版本"),("arch","系統架構"),("node","Node.js ≥ 22"),
                            ("npm","npm"),("curl","curl"),("brew","Homebrew（選用）")]:
            r = tk.Frame(self.chk_frame, bg=C_BG)
            r.pack(anchor="w", pady=5, fill="x")
            s = tk.Label(r, text="⏳", font=self.f_body, bg=C_BG, fg=C_WARN, width=3)
            s.pack(side="left")
            tk.Label(r, text=label, font=self.f_body, bg=C_BG, fg=C_TEXT).pack(side="left", padx=(5,0))
            d = tk.Label(r, text="", font=self.f_small, bg=C_BG, fg=C_DIM)
            d.pack(side="right")
            self.chk[key] = (s, d)

        # Node install frame (hidden, shows progress)
        self.node_box = tk.Frame(p, bg=C_INPUT, padx=20, pady=15)
        self.node_status_label = tk.Label(self.node_box, text="⏳ 正在自動安裝 Node.js 22+...",
                                           font=self.f_sub, bg=C_INPUT, fg=C_WARN)
        self.node_status_label.pack(anchor="w")
        self.node_detail_label = tk.Label(self.node_box, text="偵測安裝方式中...",
                                           font=self.f_small, bg=C_INPUT, fg=C_DIM)
        self.node_detail_label.pack(anchor="w", pady=(4,0))
        self.node_progress = ttk.Progressbar(self.node_box, mode="indeterminate",
                                              style="Horizontal.TProgressbar", length=500)
        self.node_progress.pack(fill="x", pady=(8,0))

        self._nav(p, back=True, next_text="下一步 →", next_cmd=lambda: self._show_page(2))

    def _go_check(self):
        self._show_page(1)
        self.after(300, lambda: threading.Thread(target=self._do_checks, daemon=True).start())
        # Start fetching latest models in background (will be ready by page 6)
        if not self.models_fetched:
            threading.Thread(target=self._fetch_latest_models, daemon=True).start()

    def _sc(self, key, st, detail=""):
        icons = {"ok":("✅",C_OK),"warn":("⚠️",C_WARN),"fail":("❌",C_ERR)}
        ic,co = icons.get(st,("❓",C_DIM))
        s,d = self.chk[key]
        s.config(text=ic, fg=co); d.config(text=detail)

    def _do_checks(self):
        mv = platform.mac_ver()[0]
        self.after(0, lambda: self._sc("os","ok" if mv else "fail", f"macOS {mv}" if mv else "非macOS"))
        self.after(0, lambda: self._sc("arch","ok", platform.machine()))
        self.after(0, lambda: self._sc("curl","ok" if shutil.which("curl") else "fail",
                                        "已安裝" if shutil.which("curl") else "未找到"))
        self.after(0, lambda: self._sc("brew","ok" if shutil.which("brew") else "warn",
                                        "已安裝" if shutil.which("brew") else "未安裝"))
        nok, nv = self._ck_node()
        if nok:
            self.after(0, lambda v=nv: self._sc("node","ok",f"v{v}"))
            # npm comes with node
            npm = shutil.which("npm")
            if npm:
                try:
                    r = subprocess.run(["npm","--version"], capture_output=True, text=True, timeout=10)
                    self.after(0, lambda v=r.stdout.strip(): self._sc("npm","ok",f"v{v}"))
                except: self.after(0, lambda: self._sc("npm","warn","版本未知"))
            else:
                self.after(0, lambda: self._sc("npm","fail","未找到"))
        else:
            det = f"v{nv}（需≥22）" if nv else "未安裝"
            self.after(0, lambda d=det: self._sc("node","fail",d))
            self.after(0, lambda: self._sc("npm","fail","需先安裝 Node.js"))
            # Auto-install Node.js
            self.after(0, lambda: self.node_box.pack(padx=40, fill="x", pady=(10,0)))
            self.after(0, lambda: self.node_progress.start(15))
            self._auto_install_node()

    def _ck_node(self):
        n = shutil.which("node")
        if not n: return False, None
        try:
            r = subprocess.run(["node","--version"], capture_output=True, text=True, timeout=10)
            v = r.stdout.strip().lstrip("v")
            return int(v.split(".")[0]) >= REQUIRED_NODE_MAJOR, v
        except: return False, None

    def _auto_install_node(self):
        """Automatically install Node.js 22 via Homebrew (install Homebrew first if needed)."""
        def _update(msg):
            self.after(0, lambda: self.node_detail_label.config(text=msg))

        def _run(cmd, **kw):
            kw.setdefault("capture_output", True)
            kw.setdefault("text", True)
            kw.setdefault("timeout", 600)
            return subprocess.run(cmd, **kw)

        def do():
            try:
                has_brew = shutil.which("brew") is not None
                # ── Step 1: Install Homebrew if missing ──
                if not has_brew:
                    _update("正在安裝 Homebrew（首次需數分鐘）…")
                    p = subprocess.Popen(
                        ["/bin/bash", "-c",
                         'NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                    )
                    for line in p.stdout:
                        short = line.strip()[-60:] if line.strip() else ""
                        if short:
                            _update(f"Homebrew: {short}")
                    p.wait()
                    if p.returncode != 0:
                        raise RuntimeError("Homebrew 安裝失敗")
                    # Ensure brew is on PATH
                    for bp in ["/opt/homebrew/bin", "/usr/local/bin"]:
                        if os.path.isfile(os.path.join(bp, "brew")):
                            os.environ["PATH"] = bp + ":" + os.environ.get("PATH", "")
                            break
                    _update("✅ Homebrew 安裝完成")

                # ── Step 2: Install Node.js 22 ──
                _update("正在透過 Homebrew 安裝 Node.js 22…")
                p2 = subprocess.Popen(
                    ["brew", "install", "node@22"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                for line in p2.stdout:
                    short = line.strip()[-60:] if line.strip() else ""
                    if short:
                        _update(f"Node: {short}")
                p2.wait()
                if p2.returncode != 0:
                    raise RuntimeError("Node.js 安裝失敗")

                # Link node@22 so it's on PATH
                subprocess.run(["brew", "link", "--overwrite", "node@22"],
                                capture_output=True, text=True, timeout=60)

                # Refresh PATH with node location
                node_prefix = subprocess.run(
                    ["brew", "--prefix", "node@22"],
                    capture_output=True, text=True, timeout=30
                ).stdout.strip()
                if node_prefix:
                    bin_dir = os.path.join(node_prefix, "bin")
                    if bin_dir not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = bin_dir + ":" + os.environ["PATH"]

                _update("✅ Node.js 22 安裝完成！正在重新檢查…")
                self.after(500, lambda: [
                    self.node_progress.stop(),
                    self.node_box.pack_forget(),
                    self._do_checks()
                ])
                return

            except Exception as e:
                self.after(0, lambda: self.node_progress.stop())
                _update(f"❌ 自動安裝失敗：{e}")
                self.after(0, lambda: messagebox.showerror(
                    "自動安裝失敗",
                    f"無法自動安裝 Node.js：\n{e}\n\n"
                    "請手動安裝：https://nodejs.org/en/download/\n"
                    "安裝後重新開啟本安裝程式。"
                ))

        threading.Thread(target=do, daemon=True).start()

    # ═══ Page 2: Options ═════════════════════════════════════════════════

    def _build_p2_options(self):
        p = self._make_page()
        tk.Label(p, text="⚙️ 安裝選項", font=self.f_title, bg=C_BG, fg=C_TEXT).pack(pady=(25,15))
        opts = tk.Frame(p, bg=C_BG)
        opts.pack(padx=40, fill="both", expand=True)

        ch = self._section(opts, "安裝頻道")
        for v,d in [("latest","Stable 穩定版（推薦）"),("beta","Beta 測試版"),("dev","Dev 開發版")]:
            ttk.Radiobutton(ch, text=d, variable=self.install_channel, value=v).pack(anchor="w",pady=2)

        sv = self._section(opts, "服務設定")
        ttk.Checkbutton(sv, text="安裝 Gateway 背景服務（launchd）", variable=self.install_daemon).pack(anchor="w",pady=2)
        ttk.Checkbutton(sv, text="安裝後執行 onboarding 精靈", variable=self.run_onboard).pack(anchor="w",pady=2)

        self._nav(p, next_text="開始安裝 →", next_cmd=self._start_install)

    # ═══ Page 3: Install Progress ════════════════════════════════════════

    def _build_p3_install(self):
        p = self._make_page()
        tk.Label(p, text="📦 正在安裝 OpenClaw...", font=self.f_title, bg=C_BG, fg=C_TEXT).pack(pady=(25,8))
        self.inst_status = tk.Label(p, text="準備中...", font=self.f_sub, bg=C_BG, fg=C_DIM)
        self.inst_status.pack(pady=(0,12))
        self.pbar = ttk.Progressbar(p, mode="indeterminate", style="Horizontal.TProgressbar", length=550)
        self.pbar.pack(pady=(0,12))

        lf = tk.Frame(p, bg=C_BG2, padx=2, pady=2)
        lf.pack(padx=30, fill="both", expand=True)
        self.log = tk.Text(lf, bg=C_BG2, fg=C_TEXT, font=self.f_mono, wrap="word", bd=0, padx=10, pady=10,
                           insertbackground=C_TEXT, selectbackground=C_ACCENT)
        sb = tk.Scrollbar(lf, command=self.log.yview)
        self.log.config(yscrollcommand=sb.set, state="disabled")
        sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

        nav = tk.Frame(p, bg=C_BG2, height=60); nav.pack(side="bottom", fill="x"); nav.pack_propagate(False)
        self.btn_cancel = tk.Button(nav, text="取消", font=self.f_body, bg=C_ERR, fg=C_BTN_FG,
                                     bd=0, padx=20, pady=10, cursor="hand2", command=self._cancel)
        self.btn_cancel.pack(side="right", padx=20)

    def _log_write(self, t):
        def do():
            self.log.config(state="normal"); self.log.insert("end",t); self.log.see("end"); self.log.config(state="disabled")
        self.after(0, do)

    def _start_install(self):
        self._show_page(3); self.pbar.start(15); self.install_cancelled = False
        threading.Thread(target=self._do_install, daemon=True).start()

    def _cancel(self):
        self.install_cancelled = True
        if self.install_process:
            try: self.install_process.terminate()
            except: pass
        self._log_write("\n⚠️ 已取消\n"); self.pbar.stop()
        self.after(0, lambda: self.inst_status.config(text="已取消", fg=C_ERR))
        self.after(0, lambda: self.btn_cancel.config(text="← 返回", command=lambda: self._show_page(2)))

    def _run_cmd(self, cmd, label):
        self.after(0, lambda: self.inst_status.config(text=label))
        self._log_write(f"\n{'─'*45}\n▶ {label}\n$ {cmd}\n\n")
        try:
            env = os.environ.copy()
            env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:" + env.get("PATH","")
            env["PYTHONIOENCODING"] = "utf-8"
            env["LANG"] = "en_US.UTF-8"
            self.install_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                     env=env, encoding="utf-8", errors="replace", bufsize=1)
            for line in self.install_process.stdout:
                if self.install_cancelled: return False
                self._log_write(line)
            self.install_process.wait()
            if self.install_process.returncode != 0:
                self._log_write(f"\n❌ 回傳碼：{self.install_process.returncode}\n"); return False
            self._log_write(f"\n✅ {label} 完成\n"); return True
        except Exception as e:
            self._log_write(f"\n❌ {e}\n"); return False

    def _do_install(self):
        ch = self.install_channel.get()
        tag = f"@{ch}" if ch != "latest" else "@latest"
        self._log_write(f"🦞 OpenClaw Installer\n   Channel: {ch}\n")

        # Clean stale npm modules to prevent ENOTEMPTY error
        stale_dir = "/opt/homebrew/lib/node_modules/openclaw"
        if os.path.isdir(stale_dir):
            self._log_write("🧹 清理舊模組目錄...\n")
            try:
                shutil.rmtree(stale_dir, ignore_errors=True)
            except Exception:
                pass
        # Also clean leftover .openclaw-* temp dirs
        nm_dir = "/opt/homebrew/lib/node_modules"
        if os.path.isdir(nm_dir):
            for d in os.listdir(nm_dir):
                if d.startswith(".openclaw-"):
                    try:
                        shutil.rmtree(os.path.join(nm_dir, d), ignore_errors=True)
                    except Exception:
                        pass

        ok = self._run_cmd(f"npm install -g openclaw{tag}", f"安裝 OpenClaw ({ch})")
        if not ok and not self.install_cancelled:
            self._log_write("\n⚠️ npm 失敗，嘗試官方腳本...\n")
            ok = self._run_cmd(f"curl -fsSL {INSTALL_SCRIPT_URL} | bash", "官方安裝腳本")

        if self.install_cancelled: return
        if not ok:
            self.after(0, lambda: self.inst_status.config(text="安裝失敗", fg=C_ERR))
            self.after(0, lambda: self.pbar.stop())
            self.after(0, lambda: self.btn_cancel.config(text="← 返回", command=lambda: self._show_page(2)))
            return

        self.after(0, lambda: self.pbar.stop())
        self.after(0, lambda: self._show_page(4))

    # ═══ Page 4: Gateway Setup (NEW) ═══════════════════════════════════

    def _build_p4_gateway(self):
        p = self._make_page()

        # Nav bar FIRST (pack bottom) so it's always visible
        nav = tk.Frame(p, bg=C_BG2, height=60)
        nav.pack(side="bottom", fill="x")
        nav.pack_propagate(False)
        tk.Button(nav, text="← 上一步", font=self.f_body, bg=C_BG, fg=C_DIM,
                  activebackground=C_BG2, activeforeground=C_TEXT, bd=0, padx=20, pady=10,
                  cursor="hand2", command=lambda: self._show_page(self.current_page - 1)
                  ).pack(side="left", padx=20)
        tk.Button(nav, text="套用設定 →", font=self.f_body, bg=C_BTN, fg=C_BTN_FG,
                  activebackground=C_ACCENT2, activeforeground=C_BTN_FG, bd=0, padx=30, pady=10,
                  cursor="hand2", command=self._apply_gateway
                  ).pack(side="right", padx=20)

        # Status label (above nav)
        self.gw_status = tk.Label(p, text="", font=self.f_small, bg=C_BG, fg=C_DIM)
        self.gw_status.pack(side="bottom", fill="x", padx=35, pady=(0,5))

        # Title
        tk.Label(p, text="\u2699\ufe0f Gateway 閘道設定", font=self.f_title, bg=C_BG, fg=C_TEXT).pack(pady=(18,5))
        tk.Label(p, text="Gateway 是 🦞 的控制中心，所有訊息經由它轉發",
                 font=self.f_sub, bg=C_BG, fg=C_DIM).pack(pady=(0,10))

        # Scrollable content area
        canvas = tk.Canvas(p, bg=C_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(p, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=C_BG)
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw", width=WINDOW_WIDTH - 60)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(30, 0))
        scrollbar.pack(side="right", fill="y")
        # Mouse wheel scroll
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # ── Section 1: Gateway Mode ──
        s1 = tk.Frame(content, bg=C_INPUT, padx=15, pady=10)
        s1.pack(fill="x", pady=(0,8), padx=5)
        tk.Label(s1, text="1. 閘道模式", font=self.f_sub, bg=C_INPUT, fg=C_ACCENT).pack(anchor="w")
        tk.Label(s1, text="選擇 Gateway 的運行方式：", font=self.f_body, bg=C_INPUT, fg=C_DIM).pack(anchor="w", pady=(2,5))

        for val, label, desc in [
            ("local", "本機模式（推薦）", "Gateway 跑在你的 Mac 上，資料不離開裝置"),
            ("remote", "遠端模式", "連線到遠端 Gateway 伺服器"),
        ]:
            rf = tk.Frame(s1, bg=C_INPUT)
            rf.pack(anchor="w", pady=1)
            ttk.Radiobutton(rf, text=label, variable=self.gateway_mode, value=val,
                            style="Dark.TRadiobutton").pack(side="left")
            tk.Label(rf, text=f"  — {desc}", font=self.f_small, bg=C_INPUT, fg=C_DIM).pack(side="left")

        # ── Section 2: Gateway Token ──
        s2 = tk.Frame(content, bg=C_INPUT, padx=15, pady=10)
        s2.pack(fill="x", pady=(0,8), padx=5)
        tk.Label(s2, text="2. 安全認證 Token", font=self.f_sub, bg=C_INPUT, fg=C_ACCENT).pack(anchor="w")
        tk.Label(s2, text="Token 用於保護你的 Gateway，防止未經授權的存取。",
                 font=self.f_body, bg=C_INPUT, fg=C_DIM).pack(anchor="w", pady=(2,5))

        ttk.Checkbutton(s2, text="自動產生安全 Token（推薦）", variable=self.gen_token,
                        command=self._toggle_token_entry, style="Dark.TCheckbutton").pack(anchor="w", pady=2)

        self.token_frame = tk.Frame(s2, bg=C_INPUT)
        self.token_frame.pack(fill="x", pady=(5,0))
        tk.Label(self.token_frame, text="Token：", font=self.f_body, bg=C_INPUT, fg=C_DIM).pack(side="left")
        self.gw_token_entry = tk.Entry(self.token_frame, textvariable=self.gateway_token,
                                        font=self.f_mono, bg=C_BG2, fg=C_TEXT,
                                        insertbackground=C_TEXT, bd=0, width=40, state="disabled")
        self.gw_token_entry.pack(side="left", padx=(5,0), ipady=4)

        # ── Section 3: Daemon / launchd ──
        s3 = tk.Frame(content, bg=C_INPUT, padx=15, pady=10)
        s3.pack(fill="x", pady=(0,8), padx=5)
        tk.Label(s3, text="3. 背景服務", font=self.f_sub, bg=C_INPUT, fg=C_ACCENT).pack(anchor="w")
        tk.Label(s3, text="將 Gateway 註冊為 macOS 背景服務，開機時自動啟動。",
                 font=self.f_body, bg=C_INPUT, fg=C_DIM).pack(anchor="w", pady=(2,3))
        ttk.Checkbutton(s3, text="安裝背服務（launchd daemon）", variable=self.install_daemon,
                        style="Dark.TCheckbutton").pack(anchor="w")

    def _toggle_token_entry(self):
        if self.gen_token.get():
            self.gw_token_entry.config(state="disabled")
        else:
            self.gw_token_entry.config(state="normal")

    def _apply_gateway(self):
        self.gw_status.config(text="正在套用 Gateway 設定...", fg=C_WARN)
        threading.Thread(target=self._do_gateway_setup, daemon=True).start()

    def _do_gateway_setup(self):
        env = os.environ.copy()
        env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:" + env.get("PATH", "")
        results = []

        # 1. Set gateway mode
        mode = self.gateway_mode.get()
        try:
            r = subprocess.run(["openclaw", "config", "set", "gateway.mode", mode],
                               capture_output=True, text=True, timeout=15, env=env)
            results.append(f"\u2705 閘道模式 → {mode}")
        except Exception as e:
            results.append(f"\u274c 閘道模式設定失敗：{e}")
            # Fallback: write directly to config
            try:
                config_path = os.path.expanduser("~/.openclaw/openclaw.json")
                config = {}
                if os.path.exists(config_path):
                    with open(config_path) as f: config = json.load(f)
                if "gateway" not in config: config["gateway"] = {}
                config["gateway"]["mode"] = mode
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, "w") as f: json.dump(config, f, indent=2)
                results[-1] = f"\u2705 閘道模式 → {mode}（直接寫入設定檔）"
            except: pass

        # 2. Generate / set token
        if self.gen_token.get():
            try:
                token = secrets.token_urlsafe(32)
                self.gateway_token.set(token)
                r = subprocess.run(["openclaw", "config", "set", "gateway.auth.token", token],
                                   capture_output=True, text=True, timeout=15, env=env)
                results.append(f"\u2705 安全 Token 已產生並設定")
            except Exception as e:
                results.append(f"\u274c Token 設定失敗：{e}")
                try:
                    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
                    config = {}
                    if os.path.exists(config_path):
                        with open(config_path) as f: config = json.load(f)
                    if "gateway" not in config: config["gateway"] = {}
                    if "auth" not in config["gateway"]: config["gateway"]["auth"] = {}
                    config["gateway"]["auth"]["token"] = token
                    with open(config_path, "w") as f: json.dump(config, f, indent=2)
                    results[-1] = f"\u2705 安全 Token 已產生（直接寫入設定檔）"
                except: pass
        else:
            token = self.gateway_token.get().strip()
            if token:
                try:
                    subprocess.run(["openclaw", "config", "set", "gateway.auth.token", token],
                                   capture_output=True, text=True, timeout=15, env=env)
                    results.append(f"\u2705 自訂 Token 已設定")
                except Exception as e:
                    results.append(f"\u274c Token 設定失敗：{e}")

        # 3. Install daemon
        if self.install_daemon.get():
            try:
                r = subprocess.run(["openclaw", "onboard", "--install-daemon"],
                                   capture_output=True, text=True, timeout=30, env=env)
                results.append(f"\u2705 背景服務已安裝")
            except Exception as e:
                results.append(f"\u26a0\ufe0f 背景服務安裝失敗：{e}")

        # 4. Start gateway
        try:
            subprocess.Popen(["openclaw", "gateway"], env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            results.append(f"\u2705 Gateway 已啟動")
        except:
            results.append(f"\u26a0\ufe0f Gateway 啟動失敗，可稍後手動執行")

        summary = "\n".join(results)
        self.after(0, lambda: self.gw_status.config(text=summary, fg=C_OK))
        self.after(1500, lambda: self._show_page(5))

    # ═══ Page 5: Telegram Setup ══════════════════════════════════════════

    def _build_p5_telegram(self):
        p = self._make_page()

        # Pack nav FIRST (bottom) so it's always visible
        self._nav(p, next_text="下一步 →", next_cmd=self._save_telegram)

        tk.Label(p, text="💬 連結 Telegram", font=self.f_title, bg=C_BG, fg=C_TEXT).pack(pady=(20,8))

        # Content area (no canvas/scrollbar — fits in window)
        inner = tk.Frame(p, bg=C_BG)
        inner.pack(padx=30, fill="both", expand=True)

        # Step 1
        s1 = tk.Frame(inner, bg=C_INPUT, padx=15, pady=10)
        s1.pack(fill="x", pady=5)
        tk.Label(s1, text="Step 1：建立 Telegram Bot", font=self.f_sub, bg=C_INPUT, fg=C_ACCENT).pack(anchor="w")
        tk.Label(s1, text="① 在 Telegram 搜尋 @BotFather 並開啟對話\n"
                 "② 發送 /newbot\n"
                 "③ 輸入機器人名稱，例如：My OpenClaw\n"
                 "④ 輸入機器人帳號（需以 bot 結尾），例如：my_openclaw_bot\n"
                 "⑤ BotFather 會回覆一組 Bot Token，格式像：\n"
                 "   123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
                 font=self.f_small, bg=C_INPUT, fg=C_TEXT, justify="left", wraplength=600).pack(anchor="w", pady=(4,0))
        tk.Button(s1, text="📱 開啟 BotFather", font=self.f_small, bg=C_BTN, fg=C_BTN_FG,
                  bd=0, padx=12, pady=4, cursor="hand2",
                  command=lambda: webbrowser.open("https://t.me/BotFather")).pack(anchor="w", pady=(6,0))

        # Step 2
        s2 = tk.Frame(inner, bg=C_INPUT, padx=15, pady=10)
        s2.pack(fill="x", pady=5)
        tk.Label(s2, text="Step 2：貼上 Bot Token", font=self.f_sub, bg=C_INPUT, fg=C_ACCENT).pack(anchor="w")
        tk.Label(s2, text="把 BotFather 給你的 Token 貼到下方：",
                 font=self.f_small, bg=C_INPUT, fg=C_TEXT).pack(anchor="w", pady=(4,0))
        tf = tk.Frame(s2, bg=C_INPUT)
        tf.pack(fill="x", pady=(6,0))
        tk.Label(tf, text="Bot Token：", font=self.f_body, bg=C_INPUT, fg=C_DIM).pack(side="left")
        self.tg_entry = tk.Entry(tf, textvariable=self.telegram_token_var, font=self.f_mono,
                                  bg=C_BG2, fg=C_TEXT, insertbackground=C_TEXT, bd=0, width=45)
        self.tg_entry.pack(side="left", padx=(5,0), ipady=5)
        self._bind_paste(self.tg_entry)

        # Step 3
        s3 = tk.Frame(inner, bg=C_INPUT, padx=15, pady=10)
        s3.pack(fill="x", pady=5)
        tk.Label(s3, text="Step 3：設定完成後", font=self.f_sub, bg=C_INPUT, fg=C_ACCENT).pack(anchor="w")
        tk.Label(s3, text="• 在 Telegram 搜尋你剛建立的 bot 帳號\n"
                 "• 點「Start」開始對話\n"
                 "• OpenClaw 會自動回覆你！",
                 font=self.f_small, bg=C_INPUT, fg=C_TEXT, justify="left").pack(anchor="w", pady=(4,0))

    def _save_telegram(self):
        token = self.telegram_token_var.get().strip()
        if token:
            # Save token to openclaw config
            def do():
                try:
                    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
                    config = {}
                    if os.path.exists(config_path):
                        with open(config_path) as f:
                            config = json.load(f)
                    if "channels" not in config:
                        config["channels"] = {}
                    config["channels"]["telegram"] = {"botToken": token}

                    os.makedirs(os.path.dirname(config_path), exist_ok=True)
                    with open(config_path, "w") as f:
                        json.dump(config, f, indent=2)
                except Exception as e:
                    self.after(0, lambda: messagebox.showwarning("提醒", f"Token 儲存失敗：{e}\n可稍後手動設定。"))
            threading.Thread(target=do, daemon=True).start()
        self._show_page(6)

    # ═══ Page 6: Model Selection ═════════════════════════════════════════

    def _build_p6_model(self):
        p = self._make_page()

        # Pack nav FIRST (bottom) so it's always visible
        self._nav(p, next_text="下一步 →", next_cmd=self._save_model)

        # ─── Auth section (pack bottom, above nav) ───
        auth_section = tk.Frame(p, bg=C_BG)
        auth_section.pack(side="bottom", padx=30, fill="x", pady=(8,0))

        # Manual API Key input
        key_frame = tk.Frame(auth_section, bg=C_INPUT, padx=15, pady=10)
        key_frame.pack(fill="x")
        tk.Label(key_frame, text="🔑 方式一：手動輸入 API Key", font=self.f_body, bg=C_INPUT, fg=C_TEXT).pack(anchor="w")

        kf = tk.Frame(key_frame, bg=C_INPUT)
        kf.pack(fill="x", pady=(6,0))
        self.api_entry = tk.Entry(kf, textvariable=self.api_key_var, font=self.f_mono, show="•",
                                   bg=C_BG2, fg=C_TEXT, insertbackground=C_TEXT, bd=0, width=45)
        self.api_entry.pack(side="left", ipady=6)
        self._bind_paste(self.api_entry)
        tk.Button(kf, text="取得 Key", font=self.f_small, bg=C_ACCENT, fg=C_BTN_FG, bd=0,
                  padx=12, pady=4, cursor="hand2", command=self._open_api_url).pack(side="left", padx=(10,0))

        tk.Label(key_frame, text="💡 API Key 會安全儲存在 ~/.openclaw/ 本機目錄中",
                 font=self.f_small, bg=C_INPUT, fg=C_DIM).pack(anchor="w", pady=(4,0))

        # Divider
        div_frame = tk.Frame(auth_section, bg=C_BG)
        div_frame.pack(fill="x", pady=(6,6))
        tk.Frame(div_frame, bg=C_DIM, height=1).pack(side="left", fill="x", expand=True)
        tk.Label(div_frame, text=" 或 ", font=self.f_small, bg=C_BG, fg=C_DIM).pack(side="left", padx=8)
        tk.Frame(div_frame, bg=C_DIM, height=1).pack(side="left", fill="x", expand=True)

        # OAuth login for OpenAI
        oauth_frame = tk.Frame(auth_section, bg=C_INPUT, padx=15, pady=10)
        oauth_frame.pack(fill="x")

        tk.Label(oauth_frame, text="🔐 方式二：OAuth 登入（僅 OpenAI）",
                 font=self.f_body, bg=C_INPUT, fg=C_TEXT).pack(anchor="w")

        oauth_btn_row = tk.Frame(oauth_frame, bg=C_INPUT)
        oauth_btn_row.pack(fill="x", pady=(4,0))
        self.oauth_btn = tk.Button(oauth_btn_row, text="🚀 使用 OpenAI 帳號登入", font=self.f_body,
                                    bg="#10a37f", fg="#ffffff", bd=0, padx=20, pady=6,
                                    cursor="hand2", command=self._oauth_login_openai)
        self.oauth_btn.pack(side="left")
        self.oauth_status = tk.Label(oauth_btn_row, text="", font=self.f_small, bg=C_INPUT, fg=C_DIM)
        self.oauth_status.pack(side="left", padx=(12,0))

        # ─── Top: Title ───
        tk.Label(p, text="🧠 選擇 AI 大模型", font=self.f_title, bg=C_BG, fg=C_TEXT).pack(pady=(18,6))
        tk.Label(p, text="選擇一個大語言模型作為 🦞 的大腦", font=self.f_sub, bg=C_BG, fg=C_DIM).pack(pady=(0,3))

        # Status label for fetch progress
        self.model_status_label = tk.Label(p, text="", font=self.f_small, bg=C_BG, fg=C_DIM)
        self.model_status_label.pack(pady=(0,6))

        # ─── Middle: Scrollable model list (fills remaining space) ───
        self.models_frame = tk.Frame(p, bg=C_BG)
        self.models_frame.pack(padx=30, fill="both", expand=True)

        # Populate with fallback models initially
        self._populate_model_list(self.models)

    def _populate_model_list(self, models):
        """Clear and rebuild the model radio-button list."""
        for w in self.models_frame.winfo_children():
            w.destroy()
        for m in models:
            mf = tk.Frame(self.models_frame, bg=C_INPUT, padx=12, pady=10)
            mf.pack(fill="x", pady=4)
            left = tk.Frame(mf, bg=C_INPUT)
            left.pack(side="left", fill="x", expand=True)
            rb = ttk.Radiobutton(left, text=f"{m['name']}  ({m['provider']})",
                                  variable=self.selected_model, value=m["id"])
            rb.pack(anchor="w")
            tk.Label(left, text=m["desc"], font=self.f_small, bg=C_INPUT, fg=C_DIM).pack(anchor="w", padx=(25,0))

    def _oauth_login_openai(self):
        """OAuth 2.0 PKCE login for OpenAI — opens browser, receives token via local callback."""
        self.oauth_btn.config(state="disabled", text="⏳ 等待登入中…")
        self.oauth_status.config(text="瀏覽器已開啟，請完成登入…", fg=C_WARN)

        def do():
            auth_code = [None]
            error_msg = [None]

            # ── 1. Generate PKCE verifier & challenge ──
            code_verifier = secrets.token_urlsafe(64)[:128]
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).rstrip(b"=").decode()
            state = secrets.token_urlsafe(32)

            # ── 2. Find free port & start local callback server ──
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]
            redirect_uri = f"http://127.0.0.1:{port}/callback"

            class _Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                    if "code" in qs:
                        auth_code[0] = qs["code"][0]
                        body = ("<html><body style='font-family:system-ui;text-align:center;padding:60px;"
                                "background:#1a1a2e;color:#eaeaea'>"
                                "<h1>✅ 登入成功！</h1><p>請返回 OpenClaw 安裝程式。</p>"
                                "</body></html>")
                    else:
                        error_msg[0] = qs.get("error_description", qs.get("error", ["未知錯誤"]))[0]
                        body = ("<html><body style='font-family:system-ui;text-align:center;padding:60px;"
                                "background:#1a1a2e;color:#e74c3c'>"
                                f"<h1>❌ 登入失敗</h1><p>{error_msg[0]}</p>"
                                "</body></html>")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(body.encode())

                def log_message(self, *a): pass

            server = HTTPServer(("127.0.0.1", port), _Handler)
            server.timeout = 180  # 3 min timeout

            # ── 3. Open browser to OpenAI auth ──
            params = urllib.parse.urlencode({
                "client_id": OPENAI_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": OPENAI_SCOPE,
                "audience": OPENAI_AUDIENCE,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": state,
            })
            webbrowser.open(f"{OPENAI_AUTH_URL}?{params}")

            # ── 4. Wait for callback ──
            server.handle_request()
            server.server_close()

            if not auth_code[0]:
                err = error_msg[0] or "登入逾時或已取消"
                self.after(0, lambda: self.oauth_status.config(text=f"❌ {err}", fg=C_ERR))
                self.after(0, lambda: self.oauth_btn.config(
                    state="normal", text="🚀 使用 OpenAI 帳號登入"))
                return

            # ── 5. Exchange code for access token ──
            self.after(0, lambda: self.oauth_status.config(text="🔄 正在取得 Token…", fg=C_WARN))
            try:
                token_data = urllib.parse.urlencode({
                    "grant_type": "authorization_code",
                    "client_id": OPENAI_CLIENT_ID,
                    "code": auth_code[0],
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                }).encode()
                req = urllib.request.Request(
                    OPENAI_TOKEN_URL,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode())

                access_token = result.get("access_token", "")
                if access_token:
                    self.after(0, lambda: self.api_key_var.set(access_token))
                    self.after(0, lambda: self.oauth_status.config(
                        text="✅ 登入成功！Token 已自動填入", fg=C_OK))
                else:
                    raise ValueError("回應中沒有 access_token")

            except Exception as e:
                self.after(0, lambda: self.oauth_status.config(
                    text=f"❌ Token 交換失敗：{e}", fg=C_ERR))

            self.after(0, lambda: self.oauth_btn.config(
                state="normal", text="🚀 使用 OpenAI 帳號登入"))

        threading.Thread(target=do, daemon=True).start()

    def _fetch_latest_models(self):
        """Fetch latest models from OpenRouter API and update the model list."""
        self.after(0, lambda: self.model_status_label.config(
            text="🔄 正在線上取得最新模型列表…", fg=C_WARN))
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/models",
                headers={"User-Agent": "OpenClaw-Installer/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            all_models = data.get("data", [])
            result = []

            for fam in MODEL_FAMILIES:
                pat = re.compile(fam["re"])
                matches = []
                for m in all_models:
                    mid = m.get("id", "")
                    # Skip :free / :beta tag variants only
                    if ":" in mid.split("/")[-1]:
                        continue
                    if pat.search(mid):
                        matches.append(m)

                if not matches:
                    continue

                # Pick the most recently created model in this family
                matches.sort(key=lambda x: x.get("created", 0), reverse=True)
                best = matches[0]
                provider_key = best["id"].split("/")[0]
                meta = PROVIDER_META.get(provider_key)
                if not meta:
                    continue

                result.append({
                    "id": best["id"],
                    "name": best.get("name", best["id"].split("/")[-1]),
                    "provider": meta["label"],
                    "desc": fam["desc"],
                    "env_key": meta["env_key"],
                    "url": meta["url"],
                })

            if result:
                self.models = result
                self.selected_model.set(result[0]["id"])
                self.models_fetched = True
                self.after(0, lambda: self._populate_model_list(result))
                self.after(0, lambda: self.model_status_label.config(
                    text=f"✅ 已取得最新模型（{len(result)} 個）", fg=C_OK))
            else:
                raise ValueError("無符合模型")

        except Exception:
            self.models_fetched = True  # don't retry
            self.after(0, lambda: self.model_status_label.config(
                text="⚠️ 線上取得失敗，使用內建模型列表", fg=C_WARN))

    def _open_api_url(self):
        mid = self.selected_model.get()
        for m in self.models:
            if m["id"] == mid:
                webbrowser.open(m["url"]); return

    def _save_model(self):
        mid = self.selected_model.get()
        key = self.api_key_var.get().strip()

        def do():
            try:
                config_path = os.path.expanduser("~/.openclaw/openclaw.json")
                config = {}
                if os.path.exists(config_path):
                    with open(config_path) as f:
                        config = json.load(f)
                if "agent" not in config:
                    config["agent"] = {}
                config["agent"]["model"] = mid

                # Save API key to env-compatible format
                if key:
                    for m in self.models:
                        if m["id"] == mid:
                            env_path = os.path.expanduser("~/.openclaw/.env")
                            lines = []
                            if os.path.exists(env_path):
                                with open(env_path) as f:
                                    lines = [l for l in f.readlines() if not l.startswith(m["env_key"])]
                            lines.append(f"{m['env_key']}={key}\n")
                            with open(env_path, "w") as f:
                                f.writelines(lines)
                            break

                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)
            except Exception as e:
                self.after(0, lambda: messagebox.showwarning("提醒", f"設定儲存失敗：{e}"))
        threading.Thread(target=do, daemon=True).start()
        self._show_page(7)

    # ═══ Page 7: Chat Test & Skill Discovery ═════════════════════════════

    def _build_p7_chat(self):
        p = self._make_page()

        # Pack nav FIRST (bottom) so it's always visible
        self._nav(p, next_text="完成設定 →", next_cmd=self._finish_setup)

        tk.Label(p, text="🦞 跟龍蝦聊聊", font=self.f_title, bg=C_BG, fg=C_TEXT).pack(pady=(20,5))
        tk.Label(p, text="告訴 🦞 你想拿它來做什麼，它會推薦合適的 Skills",
                 font=self.f_sub, bg=C_BG, fg=C_DIM).pack(pady=(0,10))

        # Input bar (pack BEFORE chat so it stays above nav)
        input_frame = tk.Frame(p, bg=C_BG2, padx=10, pady=10)
        input_frame.pack(side="bottom", fill="x", padx=20, pady=(5,0))

        self.chat_input = tk.Entry(input_frame, font=self.f_chat, bg=C_INPUT, fg=C_TEXT,
                                    insertbackground=C_TEXT, bd=0)
        self.chat_input.pack(side="left", fill="x", expand=True, ipady=8, padx=(0,10))
        self.chat_input.bind("<Return>", lambda e: self._send_chat())
        self._bind_paste(self.chat_input)

        tk.Button(input_frame, text="發送", font=self.f_body, bg=C_BTN, fg=C_BTN_FG,
                  bd=0, padx=20, pady=6, cursor="hand2", command=self._send_chat).pack(side="right")

        # Chat display (fills remaining space between title and input)
        chat_frame = tk.Frame(p, bg=C_BG2, padx=2, pady=2)
        chat_frame.pack(padx=20, fill="both", expand=True)

        self.chat_display = tk.Text(chat_frame, bg=C_BG2, fg=C_TEXT, font=self.f_chat,
                                     wrap="word", bd=0, padx=12, pady=10, spacing3=5,
                                     insertbackground=C_TEXT, selectbackground=C_ACCENT)
        csb = tk.Scrollbar(chat_frame, command=self.chat_display.yview)
        self.chat_display.config(yscrollcommand=csb.set, state="disabled")
        csb.pack(side="right", fill="y")
        self.chat_display.pack(side="left", fill="both", expand=True)

        # Configure text tags
        self.chat_display.tag_configure("bot", foreground=C_ACCENT)
        self.chat_display.tag_configure("user", foreground=C_OK)
        self.chat_display.tag_configure("system", foreground=C_DIM, font=self.f_small)

    def _chat_append(self, role, text):
        def do():
            self.chat_display.config(state="normal")
            if role == "bot":
                self.chat_display.insert("end", "🦞 ", "bot")
                self.chat_display.insert("end", text + "\n\n", "bot")
            elif role == "user":
                self.chat_display.insert("end", "你：", "user")
                self.chat_display.insert("end", text + "\n\n")
            else:
                self.chat_display.insert("end", text + "\n\n", "system")
            self.chat_display.see("end")
            self.chat_display.config(state="disabled")
        self.after(0, do)

    def _send_chat(self):
        msg = self.chat_input.get().strip()
        if not msg:
            return
        self.chat_input.delete(0, "end")
        self._chat_append("user", msg)
        self.chat_history.append({"role": "user", "content": msg})

        # Send to openclaw agent in background
        threading.Thread(target=self._do_chat, args=(msg,), daemon=True).start()

    def _do_chat(self, msg):
        try:
            env = os.environ.copy()
            env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:" + env.get("PATH", "")

            # Load env file if exists
            env_path = os.path.expanduser("~/.openclaw/.env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            env[k] = v

            # Use openclaw agent command
            result = subprocess.run(
                ["openclaw", "agent", "--message", msg, "--no-stream"],
                capture_output=True, text=True, timeout=60, env=env
            )

            response = result.stdout.strip()
            if not response:
                response = result.stderr.strip() if result.stderr else "（沒有收到回覆，請確認 Gateway 是否運行中）"

            self._chat_append("bot", response)
            self.chat_history.append({"role": "assistant", "content": response})

            # After 2 exchanges, suggest searching for skills
            if len(self.chat_history) >= 4 and not hasattr(self, '_skills_suggested'):
                self._skills_suggested = True
                self._chat_append("system",
                    "💡 提示：基於你的對話，🦞 可以自動搜尋適合的 Skills。\n"
                    "   輸入「推薦 skills」讓它幫你找！")

        except FileNotFoundError:
            self._chat_append("bot", "⚠️ 找不到 openclaw 指令。請確認安裝是否成功。\n"
                                      "你可以跳過此步驟，稍後透過 Telegram 與 🦞 互動。")
        except subprocess.TimeoutExpired:
            self._chat_append("bot", "⏱️ 回覆超時。Gateway 可能尚未啟動。\n"
                                      "試試先執行：openclaw gateway --port 18789")
        except Exception as e:
            self._chat_append("bot", f"⚠️ 錯誤：{e}\n你可以跳過此步驟。")

    def _finish_setup(self):
        self._show_page(8)

    # ═══ Page 8: Done ════════════════════════════════════════════════════

    def _build_p8_done(self):
        p = self._make_page()
        tk.Frame(p, bg=C_BG, height=35).pack()
        tk.Label(p, text="🎉", font=("Apple Color Emoji", 55), bg=C_BG).pack(pady=(0,8))
        tk.Label(p, text="全部完成！", font=self.f_title, bg=C_BG, fg=C_OK).pack(pady=(0,8))
        tk.Label(p, text="OpenClaw 已安裝並設定完畢。\n您的 🦞 已準備好為您服務！",
                 font=self.f_sub, bg=C_BG, fg=C_DIM, justify="center").pack(pady=(0,18))

        box = tk.Frame(p, bg=C_INPUT, padx=20, pady=15)
        box.pack(padx=40, fill="x")
        tk.Label(box, text="現在可以：", font=self.f_sub, bg=C_INPUT, fg=C_TEXT).pack(anchor="w", pady=(0,8))
        for ic, tx in [
            ("📱", "開啟 Telegram，跟你的 🦞 Bot 說話"),
            ("🌐", "openclaw dashboard — 網頁控制面板"),
            ("🖥️", "啟動 macOS Menu Bar App 常駐"),
            ("🧠", "探索 clawhub.ai 安裝更多 Skills"),
            ("📡", "openclaw gateway status — 檢查服務狀態"),
        ]:
            r = tk.Frame(box, bg=C_INPUT); r.pack(anchor="w", pady=3)
            tk.Label(r, text=ic, font=self.f_body, bg=C_INPUT).pack(side="left")
            tk.Label(r, text=f"  {tx}", font=self.f_body, bg=C_INPUT, fg=C_TEXT).pack(side="left")

        bf = tk.Frame(p, bg=C_BG)
        bf.pack(pady=18)

        tk.Button(bf, text="📱 開啟 Telegram Bot", font=self.f_body, bg=C_BTN, fg=C_BTN_FG,
                  bd=0, padx=18, pady=10, cursor="hand2",
                  command=self._open_telegram_bot).pack(side="left", padx=8)
        tk.Button(bf, text="🌐 控制面板", font=self.f_body, bg=C_INPUT, fg=C_TEXT,
                  bd=0, padx=18, pady=10, cursor="hand2",
                  command=lambda: subprocess.Popen(["openclaw","dashboard"],
                      env={**os.environ, "PATH": "/usr/local/bin:/opt/homebrew/bin:" + os.environ.get("PATH","")}
                  )).pack(side="left", padx=8)
        tk.Button(bf, text="🦞 ClawHub Skills", font=self.f_body, bg=C_INPUT, fg=C_TEXT,
                  bd=0, padx=18, pady=10, cursor="hand2",
                  command=lambda: webbrowser.open("https://clawhub.ai/")).pack(side="left", padx=8)

        tk.Button(p, text="關閉安裝工具", font=self.f_body, bg=C_BG2, fg=C_DIM,
                  bd=0, padx=20, pady=8, cursor="hand2", command=self.quit).pack(pady=(5,0))

    def _open_telegram_bot(self):
        token = self.telegram_token_var.get().strip()
        if token and ":" in token:
            # Extract bot username is not easily possible from token alone
            # Just open Telegram
            webbrowser.open("https://t.me/")
        else:
            webbrowser.open("https://t.me/")


if __name__ == "__main__":
    InstallerApp().mainloop()
