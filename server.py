import sys
import os
import subprocess
import threading
import re
import time

# --- GUIライブラリ ---
try:
    import tkinter as tk
    import customtkinter as ctk
    GUI_AVAILABLE = True
except:
    GUI_AVAILABLE = False

# --- 設定（あなたのマイクラIDを入れてください） ---
MY_ID = "System_Kenshin" # あなたのマイクラIDが違う場合はここを書き換えてください

class MinecraftRealmsPro:
    def __init__(self, headless=False):
        self.server_process = None
        self.headless = headless
        self.world_name = "KUROiworld"

        if not headless and GUI_AVAILABLE:
            self.setup_gui()
        else:
            print(">>> [INFO] Headless Mode: 24時間稼働を開始します...")

    def log(self, msg):
        print(msg, flush=True)
        if not self.headless and hasattr(self, "console_box"):
            self.console_box.insert("end", f"{msg}\n")
            self.console_box.see("end")

    def send_command(self, cmd):
        if self.server_process and self.server_process.stdin:
            try:
                # 余計な改行コードを除去して送信
                self.server_process.stdin.write(cmd.strip() + "\n")
                self.server_process.stdin.flush()
            except: pass

    def start_server(self):
        if self.server_process: return
        
        # サーバー設定（常にホワイトリストを有効化）
        props = {
            "level-name": self.world_name, "white-list": "true", 
            "online-mode": "true", "spawn-protection": "0"
        }
        with open("server.properties", "w") as f:
            for k, v in props.items(): f.write(f"{k}={v}\n")
        with open("eula.txt", "w") as f: f.write("eula=true")

        def run():
            try:
                self.log(f">>> マイクラサーバーを起動します... ({self.world_name})")
                self.server_process = subprocess.Popen(
                    ["java", "-Xmx7G", "-Xms7G", "-jar", "server.jar", "nogui"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace', bufsize=1
                )
                
                for line in self.server_process.stdout:
                    clean_line = line.strip()
                    self.log(f"[SERVER] {clean_line}")
                    
                    # あなたが入った時に自動で管理者にする
                    if "joined the game" in clean_line:
                        match = re.search(r'(\w+) joined the game', clean_line)
                        if match:
                            time.sleep(2)
                            self.send_command(f"op {match.group(1)}")

                    # 起動完了時に自分を招待＆管理者にする
                    if "Done" in clean_line:
                        time.sleep(5)
                        self.send_command(f"whitelist add {MY_ID}")
                        self.send_command(f"op {MY_ID}")
                        self.log(f">>> {MY_ID} を自動で招待リストに追加しました。")

            except Exception as e: self.log(f">>> エラー: {e}")
            self.server_process = None

        threading.Thread(target=run, daemon=True).start()

    def setup_gui(self):
        self.root = ctk.CTk()
        self.root.title("Minecraft Manager")
        self.console_box = ctk.CTkTextbox(self.root, width=800, height=500, fg_color="black", text_color="#00FF00")
        self.console_box.pack(padx=20, pady=20)
        ctk.CTkButton(self.root, text="開始", command=self.start_server).pack()

if __name__ == "__main__":
    is_headless = "--headless" in sys.argv or not GUI_AVAILABLE
    manager = MinecraftRealmsPro(headless=is_headless)
    if is_headless:
        manager.start_server()
        try:
            while True: time.sleep(10)
        except KeyboardInterrupt: pass
    else:
        manager.root.mainloop()
