# 🦞 OpenClaw macOS 圖形化安裝工具

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/python-3.13-green?style=flat-square" />
  <img src="https://img.shields.io/badge/license-MIT-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/OpenClaw-v2026.3-e94560?style=flat-square" />
</p>

> **一鍵完成 OpenClaw 的安裝、設定、連結 Telegram、選模型、到上手使用。**
>
> 不需要打開終端機，不需要記任何指令。
>
> 還附帶 **macOS Menu Bar App** 🦞 常駐狀態列管理 Gateway。

---

## 為什麼需要這個工具？

[OpenClaw](https://openclaw.ai/) 是一個強大的個人 AI 助手，跑在你自己的裝置上。但它的安裝流程需要：

- 確認 Node.js ≥ 22
- 執行 `npm install -g openclaw`
- 手動跑 `openclaw setup` 互動式 CLI
- 設定 Gateway 模式、Token、背景服務
- 連結 Telegram Bot（需跟 BotFather 互動取得 Token）
- 設定 AI 模型和 API Key
- 處理 DM 配對認證

對不熟悉終端機的使用者來說，這些步驟可能會卡關。

**這個工具把整個流程包裝成一個 macOS App**，全中文介面，9 個步驟的精靈引導，點點按按就完成。

---

## 功能截圖

### 安裝精靈（9 頁）

| 步驟 | 頁面 | 說明 |
|------|------|------|
| 1 | 🦞 歡迎 | 流程總覽 |
| 2 | 🔍 環境檢查 | 自動偵測 macOS / Node.js / npm / curl，缺少 Node.js 會自動安裝 |
| 3 | ⚙️ 安裝選項 | 選頻道（Stable / Beta / Dev） |
| 4 | 📦 安裝進度 | 即時日誌、可取消 |
| 5 | ⚙️ Gateway 設定 | 閘道模式 / 安全 Token / 背景服務 |
| 6 | 💬 Telegram | 建立 Bot → 貼 Token → DM 配對認證（或開放模式） |
| 7 | 🧠 模型選擇 | 動態抓取最新模型 + API Key 快速連結 |
| 8 | 🦞 聊天測試 | 直接跟龍蝦對話（繁體中文），自動推薦 Skills |
| 9 | 🎉 完成 | Daemon 安裝、Menu Bar 啟動、Telegram / Dashboard / TUI |

### Menu Bar App（常駐狀態列）

🦞 圖示常駐在螢幕右上角，提供：

- 🟢/🔴 Gateway 狀態即時顯示（每 15 秒自動刷新）
- ▶️ 啟動 / ⏹ 停止 / 🔄 重新啟動 Gateway
- 🌐 開啟控制面板（Dashboard）
- 💻 開啟終端互動介面（TUI）
- 📱 開啟 Telegram Bot（自動偵測 bot 帳號）
- 📡 檢視頻道狀態
- 🔧 安裝常駐服務（launchd daemon）
- 📂 快速開啟設定檔 / .env

---

## 安裝方式

### 方法一：下載 DMG（推薦）

1. 到 [Releases](../../releases) 下載最新的 `OpenClaw-Installer.dmg`
2. 雙擊 DMG，拖曳 App 到 Applications
3. 打開 **OpenClaw Installer**，跟著精靈走

### 方法二：從原始碼執行

```bash
# 需要 Python 3.13 + Tkinter（Homebrew）
brew install python@3.13 python-tk@3.13

# Clone
git clone https://github.com/morningbeach/openclaw-gui-installer.git
cd openclaw-gui-installer

# 執行安裝精靈
/opt/homebrew/bin/python3.13 installer_gui.py

# 執行 Menu Bar App（需額外安裝 rumps）
pip3 install rumps
/opt/homebrew/bin/python3.13 menubar_app.py
```

### 方法三：自己打包 .app + .dmg

```bash
# 建立虛擬環境
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install py2app rumps

# 打包安裝精靈
./build_app.sh

# 打包 Menu Bar App
./build_menubar.sh

# 建 DMG
./create_dmg.sh
```

### 測試工具（跳過安裝流程）

```bash
# 直接跳到指定頁面測試（4=Gateway, 5=Telegram, 6=Model, 7=Chat, 8=Done）
/opt/homebrew/bin/python3.13 test_postinstall.py 5
```

---

## 專案結構

```
.
├── installer_gui.py      # 主程式 — Tkinter 9 頁安裝精靈
├── menubar_app.py        # macOS Menu Bar 常駐 App（rumps）
├── test_postinstall.py   # 測試工具 — 跳頁直測
├── setup.py              # py2app 打包設定（安裝精靈）
├── setup_menubar.py      # py2app 打包設定（Menu Bar）
├── build_app.sh          # 一鍵建置安裝精靈 .app
├── build_menubar.sh      # 一鍵建置 Menu Bar .app
├── create_dmg.sh         # 打包成 .dmg
└── resources/            # 圖示資源
```

---

## 技術細節

- **GUI 框架**：Python 3.13 + Tkinter (Tk 9.0)
- **Menu Bar**：[rumps](https://github.com/jaredks/rumps) + pyobjc
- **打包**：py2app → .app bundle → hdiutil/create-dmg → .dmg
- **安裝方式**：呼叫 `npm install -g openclaw` 或官方 install script
- **設定方式**：直接寫入 `~/.openclaw/openclaw.json` 和 `~/.openclaw/.env`
- **聊天功能**：透過 `openclaw agent --agent main --message` CLI 與 Gateway 互動
- **模型偵測**：從 OpenRouter API 動態抓取最新模型，自動轉換 ID 格式（dots → dashes）
- **Telegram 配對**：支援 DM pairing 機制 + 開放模式，透過 Telegram Bot API 自動解析 bot 帳號
- **Daemon 管理**：透過 `openclaw daemon install/start/stop/status` 管理 macOS LaunchAgent

---

## 支援的 AI 模型

安裝精靈會自動從 OpenRouter 抓取最新模型列表，以下為 fallback 預設：

| 模型 | 提供者 | 說明 |
|------|--------|------|
| Claude Sonnet 4.6 | Anthropic | 最佳平衡（預設） |
| Claude Opus 4.6 | Anthropic | 最強推理能力 |
| GPT-5.4 | OpenAI | OpenAI 旗艦 |
| o3 Deep Research | OpenAI | 強推理模型 |
| Gemini 3.1 Pro | Google | Google 最新模型 |

> 💡 模型 ID 使用 OpenClaw 格式（dash 分隔）：`anthropic/claude-sonnet-4-6`

---

## 系統需求

- macOS 12.0 (Monterey) 或以上
- Node.js ≥ 22（安裝精靈會自動偵測，缺少時引導安裝）
- 網路連線（安裝 OpenClaw 和 AI API 需要）

---

## License

MIT — 自由使用、修改、分發。

本工具為社群專案，與 OpenClaw 官方無直接關聯。

---

## 致謝

- [OpenClaw](https://openclaw.ai/) by [@steipete](https://github.com/steipete)
- OpenClaw 中文社群的所有夥伴 🦞
