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

---

## 為什麼需要這個工具？

[OpenClaw](https://openclaw.ai/) 是一個強大的個人 AI 助手，跑在你自己的裝置上。但它的安裝流程需要：

- 確認 Node.js ≥ 22
- 執行 `npm install -g openclaw`
- 手動跑 `openclaw setup` 互動式 CLI
- 設定 Gateway 模式、Token、背景服務
- 連結 Telegram Bot（需跟 BotFather 互動取得 Token）
- 設定 AI 模型和 API Key

對不熟悉終端機的使用者來說，這些步驟可能會卡關。

**這個工具把整個流程包裝成一個 macOS App**，全中文介面，9 個步驟的精靈引導，點點按按就完成。

---

## 功能截圖

安裝精靈包含 **9 個頁面**：

| 步驟 | 頁面 | 說明 |
|------|------|------|
| 1 | 🦞 歡迎 | 流程總覽 |
| 2 | 🔍 環境檢查 | 自動偵測 macOS / Node.js / npm / curl |
| 3 | ⚙️ 安裝選項 | 選頻道（Stable / Beta / Dev） |
| 4 | 📦 安裝進度 | 即時日誌、可取消 |
| 5 | ⚙️ Gateway 設定 | 閘道模式 / 安全 Token / 背景服務 |
| 6 | 💬 Telegram | Step-by-step 建立 Bot 並貼上 Token |
| 7 | 🧠 模型選擇 | Claude / GPT / Gemini + API Key |
| 8 | 🦞 聊天測試 | 直接跟龍蝦對話，自動推薦 Skills |
| 9 | 🎉 完成 | 一鍵開啟 Telegram / Dashboard / ClawHub |

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

# 直接執行
/opt/homebrew/bin/python3.13 installer_gui.py
```

### 方法三：自己打包 .app + .dmg

```bash
# 建立虛擬環境
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install py2app

# 打包
./build_app.sh

# 建 DMG
./create_dmg.sh
```

---

## 專案結構

```
.
├── installer_gui.py    # 主程式 — Tkinter 9 頁安裝精靈
├── setup.py            # py2app 打包設定
├── build_app.sh        # 一鍵建置 .app
├── create_dmg.sh       # 打包成 .dmg
└── resources/          # 圖示資源
```

---

## 技術細節

- **GUI 框架**：Python 3.13 + Tkinter (Tk 9.0)
- **打包**：py2app → .app bundle → hdiutil/create-dmg → .dmg
- **安裝方式**：呼叫 `npm install -g openclaw` 或官方 install script
- **設定方式**：直接寫入 `~/.openclaw/openclaw.json` 和 `~/.openclaw/.env`
- **聊天功能**：透過 `openclaw agent --message` CLI 與 Gateway 互動

---

## 支援的 AI 模型

| 模型 | 提供者 | 說明 |
|------|--------|------|
| Claude Sonnet 4 | Anthropic | 最佳平衡（預設） |
| Claude Opus 4 | Anthropic | 最強推理能力 |
| GPT-4.1 | OpenAI | OpenAI 旗艦 |
| o3 | OpenAI | 強推理模型 |
| Gemini 2.5 Pro | Google | Google 最新模型 |

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
