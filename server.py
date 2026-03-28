import sys
import os
import subprocess
import threading
import json
import re
import time
import webbrowser

# --- GUIライブラリの読み込み (環境に合わせて柔軟に対応) ---
try:
    import tkinter as tk
    import customtkinter as ctk
    from tkinter import messagebox
    GUI_AVAILABLE = True
except:
    GUI_AVAILABLE = False

# --- 設定の読み込み ---
PLAYIT_SECRET = os.getenv("PLAYIT_SECRET", "").strip()
CONFIG_FILE = "servers_list.json"

class MinecraftRealmsPro:
    def __init__(self, headless=False):
        self.server_process = None
        self.current_running_world = None
        self.headless = headless
        
        # データの初期化
        self.worlds = self.load_world_list()
        self.auto_detect_existing_folders()

        if not headless and GUI_AVAILABLE:
            self.setup_gui()
            self.refresh_world_list_ui()
            self.after(2000, self.refresh_member_lists)
        else:
            print(">>> [INFO] Headless Mode: 画面なしでサーバーを起動します...")

    # --- 便利メソッド ---
    def add_label(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text, font=("MS Gothic", 12, "bold"))
        lbl.pack(anchor="w", pady=(10, 0))
        return lbl

    def add_entry(self, parent, default):
        e = ctk.CTkEntry(parent); e.insert(0, default); e.pack(pady=5, fill="x"); return e

    def add_switch(self, parent, text, default):
        s = ctk.CTkSwitch(parent, text=text); (s.select() if default else s.deselect()); s.pack(pady=8, anchor="w"); return s

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
        world = self.world_name_entry.get() if not self.headless else "KUROiworld"
        
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
                self.log(f"マイクラサーバーを起動中: {world}")
                self.server_process = subprocess.Popen(
                    [java_cmd, "-Xmx7G", "-Xms7G", "-jar", "server.jar", "nogui"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace', bufsize=1
                )
                self.current_running_world = world
                for line in self.server_process.stdout:
                    clean_line = line.strip()
                    self.log(clean_line, "SERVER")
                    
                    if "joined the game" in clean_line:
                        match = re.search(r'(\w+) joined the game', clean_line)
                        if match:
                            time.sleep(2)
                            self.send_command(f"op {match.group(1)}")
                    
                    if "Done" in clean_line:
                        time.sleep(3)
                        self.send_command("gamerule keepInventory true")
                        if not self.headless: self.after(0, self.refresh_member_lists)

            except Exception as e: self.log(f"起動エラー: {e}", "ERROR")
            self.server_process = None
            self.current_running_world = None

        threading.Thread(target=run, daemon=True).start()

    # --- GUI構築 (PC用) ---
    def setup_gui(self):
        self.root = ctk.CTk()
        self.root.title("Minecraft Server Manager Pro (No Bot)")
        self.root.geometry("1100x800")
        self.root.grid_columnconfigure(0, weight=1); self.root.grid_columnconfigure(1, weight=2); self.root.grid_columnconfigure(2, weight=2)
        self.root.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self.root); sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.world_list_frame = ctk.CTkScrollableFrame(sidebar, label_text="ワールドリスト"); self.world_list_frame.pack(expand=True, fill="both", padx=5, pady=5)

        settings = ctk.CTkFrame(self.root); settings.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.tabview = ctk.CTkTabview(settings); self.tabview.pack(expand=True, fill="both")
        self.tab_game = self.tabview.add("設定"); self.tab_players = self.tabview.add("メンバー")
        
        self.world_name_entry = self.add_entry(self.tab_game, "KUROiworld")
        ctk.CTkButton(self.tab_game, text="サーバー開始", fg_color="green", command=self.start_server).pack(pady=10, fill="x")
        ctk.CTkButton(self.tab_game, text="playit.gg 管理画面", command=lambda: webbrowser.open("https://playit.gg/login")).pack(pady=5, fill="x")

        self.invite_entry = ctk.CTkEntry(self.tab_players, placeholder_text="招待ID"); self.invite_entry.pack(fill="x", pady=5)
        ctk.CTkButton(self.tab_players, text="招待追加", command=lambda: self.send_command(f"whitelist add {self.invite_entry.get()}")).pack(fill="x")
        self.whitelist_scroll = ctk.CTkScrollableFrame(self.tab_players, height=300, label_text="招待済み"); self.whitelist_scroll.pack(fill="x", pady=5)

        right = ctk.CTkFrame(self.root); right.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        self.console_box = ctk.CTkTextbox(right, fg_color="black", text_color="#00FF00", font=("Consolas", 12))
        self.console_box.pack(expand=True, fill="both", padx=5, pady=5)

    def load_world_list(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f: return json.load(f)
            except: return ["KUROiworld"]
        return ["KUROiworld"]

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

    def refresh_member_lists(self):
        for w in self.whitelist_scroll.winfo_children(): w.destroy()
        if os.path.exists("whitelist.json"):
            try:
                with open("whitelist.json", "r") as f:
                    for p in json.load(f): ctk.CTkLabel(self.whitelist_scroll, text=p['name'], anchor="w").pack(fill="x", padx=10)
            except: pass

    def on_closing(self):
        if self.server_process: self.server_process.terminate()
        if hasattr(self, "root"): self.root.destroy()

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