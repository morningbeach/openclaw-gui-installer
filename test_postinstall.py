#!/opt/homebrew/bin/python3.13
"""
OpenClaw Post-Install Tester
==============================
跳過安裝步驟，直接從 Gateway 頁面開始測試。
Pages: Gateway(4) → Telegram(5) → Model(6) → Chat(7) → Done(8)

用法: python3.13 test_postinstall.py [page]
  page: 4=Gateway  5=Telegram  6=Model  7=Chat  8=Done
  預設從 page 4 開始
"""
import sys
import os

# Add script dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import installer module (without running mainloop)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "installer_gui",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "installer_gui.py")
)
mod = importlib.util.module_from_spec(spec)

# Prevent the if __name__ == "__main__" block from running
mod.__name__ = "installer_gui"
spec.loader.exec_module(mod)

# Determine start page
start_page = 4
if len(sys.argv) > 1:
    try:
        start_page = int(sys.argv[1])
        if start_page < 4:
            start_page = 4
        elif start_page > 8:
            start_page = 8
    except ValueError:
        pass

print(f"🧪 OpenClaw Post-Install Tester")
print(f"   Starting at page {start_page}")
print(f"   Pages: 4=Gateway  5=Telegram  6=Model  7=Chat  8=Done")
print()

# Create app and jump to the desired page
app = mod.InstallerApp()
app.title(f"🧪 OpenClaw Tester (page {start_page})")
app._show_page(start_page)
app.mainloop()
