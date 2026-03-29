import sys
import os
import subprocess
import threading
import json
import re
import time
import webbrowser

# --- ライブラリ読み込み ---
try:
    import tkinter as tk
    import customtkinter as ctk
    GUI_AVAILABLE = True
except:
    GUI_AVAILABLE = False

# --- 設定 ---
PLAYIT_SECRET = os.getenv("PLAYIT_SECRET", "").strip()
CONFIG_FILE = "servers_list.json"
# あなたのマイクラIDをここに書いておけば、GitHub側で自動的に許可されます
MY_ID = "System_Kenshin" 

class MinecraftRealmsPro:
    def __init__(self, headless=False):
        self.server_process = None
        self.current_running_world = None
        self.headless = headless
        self.world_name_val = "KUROiworld"
        
        self.worlds = self.load_world_list()
        self.auto_detect_existing_folders()

        if not headless and GUI_AVAILABLE:
            self.setup_gui()
        else:
            print(">>> [INFO] Headless Mode: 24時間稼働開始")

    def log(self, msg, tag="INFO"):
        print(f"[{tag}] {msg}", flush=True)
        if not self.headless and hasattr(self, "console_box"):
            def _gui_log():
                self.console_box.configure(state="normal")
                self.console_box.insert("end", f"[{tag}] {msg}\n")
                self.console_box.see("end")
                self.console_box.configure(state="disabled")
            self.root.after(0, _gui_log)

    def send_command(self, cmd):
        """改行コード問題を完全に排除してコマンド送信"""
        if self.server_process and self.server_process.stdin:
            try:
                # \r を消し、純粋な \n だけを付けてバイト列で送る
                clean_cmd = (cmd.strip().replace('\r', '') + "\n").encode('utf-8')
                self.server_process.stdin.write(clean_cmd.decode('utf-8'))
                self.server_process.stdin.flush()
            except: pass

    def start_server(self):
        if self.server_process: return
        world = self.world_name_val # Headless時は固定
        
        # サーバー設定（ホワイトリストをオンにする）
        props = {
            "level-name": world, "white-list": "true", "online-mode": "true",
            "spawn-protection": "0", "difficulty": "normal", "max-players": "10"
        }
        with open("server.properties", "w") as f:
            for k, v in props.items(): f.write(f"{k}={v}\n")
        with open("eula.txt", "w") as f: f.write("eula=true")

        java_cmd = "java" # GitHub側はこれでJava26が動く

        def run():
            try:
                self.log(f"マイクラサーバー起動開始: {world}")
                self.server_process = subprocess.Popen(
                    [java_cmd, "-Xmx7G", "-Xms7G", "-jar", "server.jar", "nogui"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace', bufsize=1
                )
                self.current_running_world = world
                for line in self.server_process.stdout:
                    clean_line = line.strip()
                    self.log(clean_line, "SERVER")
                    
                    # 起動完了後の処理
                    if "Done" in clean_line:
                        time.sleep(5)
                        # 【重要】自分を自動的に招待＆管理者にする
                        self.send_command(f"whitelist add {MY_ID}")
                        self.send_command(f"op {MY_ID}")
                        self.send_command("gamerule keepInventory false")
                        self.log(f">>> {MY_ID} を自動招待し、管理者に任命しました。", "SYSTEM")

            except Exception as e: self.log(f"エラー: {e}", "ERROR")
            self.server_process = None

        threading.Thread(target=run, daemon=True).start()

    def setup_gui(self):
        # (GUIのコードは今まで通りですが、GitHubで上書きするのでシンプルにします)
        self.root = ctk.CTk()
        self.root.title("MC Manager Pro")
        self.console_box = ctk.CTkTextbox(self.root, width=800, height=500, fg_color="black", text_color="#00FF00")
        self.console_box.pack(padx=20, pady=20)
        ctk.CTkButton(self.root, text="サーバー開始", command=self.start_server).pack(pady=10)

    def load_world_list(self): return ["KUROiworld"]
    def auto_detect_existing_folders(self): pass
    def save_world_list(self): pass

if __name__ == "__main__":
    is_headless = "--headless" in sys.argv or not GUI_AVAILABLE
    manager = MinecraftRealmsPro(headless=is_headless)
    if is_headless:
        manager.start_server()
        while True: time.sleep(10)
    else:
        manager.root.mainloop()
