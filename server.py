import sys
import os
import subprocess
import threading
import json
import re
import time
import webbrowser

# --- GUIライブラリの読み込みチェック ---
try:
    import tkinter as tk
    import customtkinter as ctk
    from tkinter import messagebox
    GUI_AVAILABLE = True
except:
    GUI_AVAILABLE = False

# --- 設定読み込み ---
PLAYIT_SECRET = os.getenv("PLAYIT_SECRET", "").strip()
CONFIG_FILE = "servers_list.json"

class MinecraftRealmsPro:
    def __init__(self, headless=False):
        self.server_process = None
        self.current_running_world = None
        self.headless = headless
        self.world_name_val = "KUROiworld" # デフォルトのワールド名
        
        # データの読み込み
        self.worlds = self.load_world_list()
        self.auto_detect_existing_folders()

        if not headless and GUI_AVAILABLE:
            self.setup_gui()
            self.refresh_world_list_ui()
        else:
            print(">>> [INFO] Headless Mode: サーバー自動起動を開始します...")

    # --- GUI用便利メソッド ---
    def add_label(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text, font=("MS Gothic", 12, "bold"))
        lbl.pack(anchor="w", pady=(10, 0))
        return lbl

    def add_entry(self, parent, default):
        e = ctk.CTkEntry(parent); e.insert(0, default); e.pack(pady=5, fill="x"); return e

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
        if self.server_process:
            try:
                self.server_process.stdin.write(cmd.strip() + "\n")
                self.server_process.stdin.flush()
            except: pass

    # --- サーバー起動ロジック ---
    def start_server(self):
        if self.server_process: return
        # GUIなら入力された名前、Headlessならデフォルト名
        world = self.world_name_entry.get() if not self.headless else self.world_name_val
        
        # 設定ファイル作成 (常に最新の設定を反映)
        props = {
            "level-name": world, 
            "white-list": "true", 
            "online-mode": "true", 
            "spawn-protection": "0",
            "difficulty": "normal"
        }
        with open("server.properties", "w") as f:
            for k, v in props.items(): f.write(f"{k}={v}\n")
        with open("eula.txt", "w") as f: f.write("eula=true")

        # Java 26 を最優先で検索
        java_cmd = "java"
        paths = [r"C:\Program Files\Java\jdk-26\bin\java.exe"]
        for p in paths:
            if os.path.exists(p): java_cmd = p; break

        def run():
            try:
                self.log(f"マイクラサーバー起動準備中... (ワールド: {world})")
                self.server_process = subprocess.Popen(
                    [java_cmd, "-Xmx7G", "-Xms7G", "-jar", "server.jar", "nogui"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace', bufsize=1
                )
                self.current_running_world = world
                for line in self.server_process.stdout:
                    clean_line = line.strip()
                    self.log(clean_line, "SERVER")
                    
                    # 参加者を自動で管理者(OP)にする
                    if "joined the game" in clean_line:
                        match = re.search(r'(\w+) joined the game', clean_line)
                        if match:
                            time.sleep(2)
                            self.send_command(f"op {match.group(1)}")
                    
                    # 起動完了後の自動設定
                    if "Done" in clean_line:
                        time.sleep(5)
                        self.send_command("gamerule keepInventory true")

            except Exception as e: self.log(f"エラー: {e}", "ERROR")
            self.server_process = None
            self.current_running_world = None

        threading.Thread(target=run, daemon=True).start()

    # --- GUI構築 (PC用) ---
    def setup_gui(self):
        self.root = ctk.CTk()
        self.root.title("Minecraft Server Manager Pro")
        self.root.geometry("1100x800")
        self.root.grid_columnconfigure(0, weight=1); self.root.grid_columnconfigure(1, weight=2)
        self.root.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self.root); left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.world_list_frame = ctk.CTkScrollableFrame(left, label_text="ワールドリスト"); self.world_list_frame.pack(expand=True, fill="both", pady=5)

        self.add_label(left, "ワールド設定")
        self.world_name_entry = self.add_entry(left, self.world_name_val)
        
        ctk.CTkButton(left, text="サーバー開始", fg_color="green", command=self.start_server).pack(pady=10, fill="x")
        ctk.CTkButton(left, text="playit.gg 管理画面", command=lambda: webbrowser.open("https://playit.gg/login")).pack(fill="x")

        self.console_box = ctk.CTkTextbox(self.root, fg_color="black", text_color="#00FF00", font=("Consolas", 12))
        self.console_box.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

    # --- データ管理系 ---
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
                if os.path.exists(os.path.join(item, "level.dat")) and item not in self.worlds:
                    self.worlds.append(item)
        self.save_world_list()

    def refresh_world_list_ui(self):
        for widget in self.world_list_frame.winfo_children(): widget.destroy()
        for world in self.worlds:
            frame = ctk.CTkFrame(self.world_list_frame); frame.pack(fill="x", pady=2)
            ctk.CTkLabel(frame, text="●", text_color="#55FF55").pack(side="left", padx=5)
            ctk.CTkButton(frame, text=world, fg_color="transparent", anchor="w", 
                         command=lambda w=world: self.select_world(w)).pack(side="left", expand=True, fill="x")

    def select_world(self, name):
        if hasattr(self, "world_name_entry"):
            self.world_name_entry.delete(0, "end"); self.world_name_entry.insert(0, name)

# ==========================================
# 3. 実行メイン
# ==========================================
if __name__ == "__main__":
    # --headless 引数があるか、GUIが使えない環境ならHeadless
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
