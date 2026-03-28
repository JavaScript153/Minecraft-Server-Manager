import sys
import os
import subprocess
import threading
import json
import re
import time
import webbrowser

# --- GUIライブラリの読み込み ---
try:
    import tkinter as tk
    import customtkinter as ctk
    GUI_AVAILABLE = True
except:
    GUI_AVAILABLE = False

# --- 設定 ---
PLAYIT_SECRET = os.getenv("PLAYIT_SECRET", "").strip()
CONFIG_FILE = "servers_list.json"

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
            self.refresh_world_list_ui()
        else:
            print(">>> [INFO] Headless Mode: 24時間稼働を開始します...")

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
        """改行コード問題を解決し、確実にコマンドを届ける"""
        if self.server_process and self.server_process.stdin:
            try:
                # 前後の空白を消し、Windowsの改行(\r)を消して、Linuxの改行(\n)のみにする
                clean_cmd = cmd.strip().replace('\r', '') + "\n"
                self.server_process.stdin.write(clean_cmd)
                self.server_process.stdin.flush()
                self.log(f"コマンド送信成功: {cmd.strip()}", "SYSTEM")
            except Exception as e:
                self.log(f"コマンド送信エラー: {e}", "ERROR")

    def start_server(self):
        if self.server_process: return
        world = self.world_name_entry.get() if not self.headless else self.world_name_val
        
        # 設定ファイル作成
        props = {"level-name": world, "white-list": "true", "online-mode": "true", "spawn-protection": "0"}
        with open("server.properties", "w") as f:
            for k, v in props.items(): f.write(f"{k}={v}\n")
        with open("eula.txt", "w") as f: f.write("eula=true")

        # Javaパス検索
        java_cmd = "java"
        paths = [r"C:\Program Files\Java\jdk-26\bin\java.exe", "/usr/bin/java"]
        for p in paths:
            if os.path.exists(p): java_cmd = p; break

        def run():
            try:
                self.log(f"マイクラサーバー起動開始... ({world})")
                self.server_process = subprocess.Popen(
                    [java_cmd, "-Xmx7G", "-Xms7G", "-jar", "server.jar", "nogui"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace', bufsize=1
                )
                self.current_running_world = world
                
                for line in self.server_process.stdout:
                    clean_line = line.strip()
                    self.log(clean_line, "SERVER")
                    
                    # 参加時に管理者(OP)化
                    if "joined the game" in clean_line:
                        match = re.search(r'(\w+) joined the game', clean_line)
                        if match:
                            time.sleep(2)
                            self.send_command(f"op {match.group(1)}")
                    
                    # 起動完了後に設定を適用
                    if "Done" in clean_line:
                        def apply_initial_settings():
                            time.sleep(10) # サーバーが落ち着くまで待機
                            # ★ここで keepInventory を false (オフ) に設定します
                            self.send_command("gamerule keepInventory false")
                            self.send_command("gamerule mobGriefing true")
                            self.log(">>> 初期設定(アイテム保持:OFF)を適用しました。", "SYSTEM")
                        threading.Thread(target=apply_initial_settings, daemon=True).start()

            except Exception as e: self.log(f"エラー: {e}", "ERROR")
            self.server_process = None
            self.current_running_world = None

        threading.Thread(target=run, daemon=True).start()

    def setup_gui(self):
        self.root = ctk.CTk()
        self.root.title("Minecraft Manager Pro")
        self.root.geometry("1100x800")
        self.root.grid_columnconfigure(0, weight=1); self.root.grid_columnconfigure(1, weight=2)
        left = ctk.CTkFrame(self.root); left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.world_list_frame = ctk.CTkScrollableFrame(left, label_text="ワールド"); self.world_list_frame.pack(expand=True, fill="both")
        self.world_name_entry = ctk.CTkEntry(left); self.world_name_entry.insert(0, self.world_name_val); self.world_name_entry.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(left, text="サーバー開始", fg_color="green", command=self.start_server).pack(pady=10, fill="x")
        self.console_box = ctk.CTkTextbox(self.root, fg_color="black", text_color="#00FF00", font=("Consolas", 12))
        self.console_box.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

    def load_world_list(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f: return json.load(f)
            except: return [self.world_name_val]
        return [self.world_name_val]

    def save_world_list(self):
        with open(CONFIG_FILE, "w") as f: json.dump(self.worlds, f)

    def auto_detect_existing_folders(self):
        exclude = ["libraries", "logs", "versions", "__pycache__"]
        for item in os.listdir('.'):
            if os.path.isdir(item) and item not in exclude:
                if os.path.exists(os.path.join(item, "level.dat")):
                    if item not in self.worlds: self.worlds.append(item)
        self.save_world_list()

    def refresh_world_list_ui(self):
        for widget in self.world_list_frame.winfo_children(): widget.destroy()
        for world in self.worlds:
            frame = ctk.CTkFrame(self.world_list_frame); frame.pack(fill="x", pady=2)
            ctk.CTkLabel(frame, text="●", text_color="#55FF55").pack(side="left", padx=5)
            ctk.CTkButton(frame, text=world, fg_color="transparent", anchor="w", command=lambda w=world: self.select_world(w)).pack(side="left", expand=True, fill="x")

    def select_world(self, name):
        if hasattr(self, "world_name_entry"):
            self.world_name_entry.delete(0, "end"); self.world_name_entry.insert(0, name)

if __name__ == "__main__":
    is_headless = "--headless" in sys.argv or not GUI_AVAILABLE
    manager = MinecraftRealmsPro(headless=is_headless)
    if is_headless:
        manager.start_server()
        try:
            while True: time.sleep(10)
        except KeyboardInterrupt:
            manager.send_command("stop")
            time.sleep(5)
    else:
        manager.root.mainloop()
