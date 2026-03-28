import tkinter as tk
import customtkinter as ctk
import subprocess
import threading
import os
import shutil
import json
import re
import time
import webbrowser
from tkinter import messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MinecraftRealmsPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Minecraft 自作Realms Pro - 修正完了版")
        self.geometry("1350x900")

        # --- データ初期化 ---
        self.server_process = None
        self.tunnel_process = None
        self.current_running_world = None
        self.config_file = "servers_list.json"
        
        self.worlds = self.load_world_list()
        self.auto_detect_existing_folders()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- レイアウト ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # 1. サーバー一覧 (左)
        self.sidebar = ctk.CTkFrame(self, width=250)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ctk.CTkLabel(self.sidebar, text="サーバー一覧", font=("MS Gothic", 20, "bold")).pack(pady=20)
        self.world_list_frame = ctk.CTkScrollableFrame(self.sidebar, label_text="作成済みワールド")
        self.world_list_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        # 2. 設定タブ (中)
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=0, column=1, padx=5, pady=10, sticky="nsew")
        self.tabview = ctk.CTkTabview(self.settings_frame)
        self.tabview.pack(expand=True, fill="both", padx=10, pady=10)
        self.tab_game = self.tabview.add("全般")
        self.tab_world = self.tabview.add("ワールド生成")
        self.tab_rules = self.tabview.add("ゲームルール")
        self.tab_players = self.tabview.add("メンバー管理")
        
        # UI構築
        self.setup_game_tab()
        self.setup_world_tab()
        self.setup_rules_tab()
        self.setup_players_tab()

        # 3. コンソール (右)
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=2, padx=5, pady=10, sticky="nsew")
        self.addr_frame = ctk.CTkFrame(self.right_frame, fg_color="#1a1a1a", border_width=2, border_color="#2D7D46")
        self.addr_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(self.addr_frame, text="公開アドレス確認 (playit.gg)", font=("MS Gothic", 12)).pack(pady=(5,0))
        self.addr_display = ctk.CTkLabel(self.addr_frame, text="停止中", text_color="#777", font=("Consolas", 18, "bold"))
        self.addr_display.pack(pady=5)
        ctk.CTkButton(self.addr_frame, text="playit.gg 管理画面を開く", font=("MS Gothic", 11), height=24, fg_color="#2D7D46", command=self.open_playit_web).pack(pady=5)
        
        self.console_box = ctk.CTkTextbox(self.right_frame, state="disabled", fg_color="black", text_color="#00FF00", font=("Consolas", 12))
        self.console_box.pack(expand=True, fill="both", padx=10, pady=5)
        self.cmd_entry = ctk.CTkEntry(self.right_frame, placeholder_text="コマンドを入力...")
        self.cmd_entry.pack(fill="x", padx=10, pady=5)
        self.cmd_entry.bind("<Return>", lambda e: self.send_command())

        # 4. 下部：コントロール
        self.bottom_frame = ctk.CTkFrame(self, height=80)
        self.bottom_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        self.start_btn = ctk.CTkButton(self.bottom_frame, text="サーバーを開始", fg_color="#2D7D46", command=self.start_server, height=45)
        self.start_btn.pack(side="left", padx=20, pady=10, expand=True, fill="x")
        self.stop_btn = ctk.CTkButton(self.bottom_frame, text="停止", fg_color="#A32E2E", command=self.safe_stop_server, height=45)
        self.stop_btn.pack(side="left", padx=20, pady=10, expand=True, fill="x")

        self.refresh_world_list_ui()

    # --- 部品作成用の命令 (ここが抜けていました！) ---
    def add_label(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text, font=("MS Gothic", 12, "bold"))
        lbl.pack(anchor="w", pady=(10, 0))
        return lbl

    def add_entry(self, parent, default, ph=""):
        e = ctk.CTkEntry(parent, placeholder_text=ph)
        e.insert(0, default)
        e.pack(pady=5, fill="x")
        return e

    def add_switch(self, parent, text, default):
        s = ctk.CTkSwitch(parent, text=text)
        if default: s.select()
        s.pack(pady=8, anchor="w")
        return s

    # --- ログ出力 ---
    def log(self, msg, tag="INFO"):
        def _log():
            self.console_box.configure(state="normal")
            self.console_box.insert("end", f"[{tag}] {msg}\n")
            self.console_box.see("end")
            self.console_box.configure(state="disabled")
        self.after(0, _log)

    def open_playit_web(self):
        webbrowser.open("https://playit.gg/account/tunnels")

    # --- ワールド管理 ---
    def load_world_list(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f: return json.load(f)
            except: return []
        return []

    def save_world_list(self):
        with open(self.config_file, "w") as f: json.dump(self.worlds, f)

    def auto_detect_existing_folders(self):
        exclude = ["libraries", "logs", "versions", "__pycache__"]
        for item in os.listdir('.'):
            if os.path.isdir(item) and item not in exclude and item not in self.worlds:
                if os.path.exists(os.path.join(item, "level.dat")): self.worlds.append(item)
        self.save_world_list()

    def refresh_world_list_ui(self):
        for widget in self.world_list_frame.winfo_children(): widget.pack_forget(); widget.destroy()
        for world in self.worlds:
            frame = ctk.CTkFrame(self.world_list_frame); frame.pack(fill="x", pady=2, padx=5)
            sc = "#55FF55" if world == self.current_running_world else "#FF5555"
            ctk.CTkLabel(frame, text="●", text_color=sc).pack(side="left", padx=5)
            ctk.CTkButton(frame, text=world, fg_color="transparent", anchor="w", command=lambda w=world: self.select_world(w)).pack(side="left", expand=True, fill="x")
            ctk.CTkButton(frame, text="消去", width=40, fg_color="#555", hover_color="red", command=lambda w=world: self.delete_world_action(w)).pack(side="right", padx=5)

    def select_world(self, name):
        self.world_name.delete(0, "end"); self.world_name.insert(0, name)
        self.log(f"ワールド '{name}' を選択しました。")

    def delete_world_action(self, name):
        if self.current_running_world == name: return
        if messagebox.askyesno("削除", f"'{name}' を完全に削除しますか？\n(シード値などを変えたい場合は一度削除してください)"):
            if os.path.exists(name): shutil.rmtree(name)
            if name in self.worlds: self.worlds.remove(name)
            self.save_world_list(); self.refresh_world_list_ui()

    # --- 各タブの構築 ---
    def setup_game_tab(self):
        self.add_label(self.tab_game, "ワールド名 (新しい名前を入れると新規作成)")
        self.world_name = self.add_entry(self.tab_game, "KUROiworld")
        self.add_label(self.tab_game, "ゲームモード")
        self.gamemode = ctk.CTkOptionMenu(self.tab_game, values=["survival", "creative", "adventure", "spectator"])
        self.gamemode.set("survival"); self.gamemode.pack(pady=5, fill="x")
        self.add_label(self.tab_game, "難易度")
        self.difficulty = ctk.CTkOptionMenu(self.tab_game, values=["peaceful", "easy", "normal", "hard"])
        self.difficulty.set("normal"); self.difficulty.pack(pady=5, fill="x")
        self.add_label(self.tab_game, "説明 (MOTD)")
        self.motd = self.add_entry(self.tab_game, "Welcome to my Python Realm!")

    def setup_world_tab(self):
        ctk.CTkLabel(self.tab_world, text="※シード値や地形は「新規作成時」のみ有効です", text_color="orange").pack(pady=5)
        self.add_label(self.tab_world, "シード値 (空欄でランダム)")
        self.seed = self.add_entry(self.tab_world, "")
        self.add_label(self.tab_world, "ワールドタイプ")
        self.world_type = ctk.CTkOptionMenu(self.tab_world, values=["default", "flat", "large_biomes", "amplified"])
        self.world_type.set("default"); self.world_type.pack(pady=5, fill="x")
        self.structures = self.add_switch(self.tab_world, "構造物を生成 (村など)", True)
        self.hardcore = self.add_switch(self.tab_world, "ハードコアモード", False)

    def setup_rules_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_rules, height=400); scroll.pack(expand=True, fill="both")
        self.keep_inv = self.add_switch(scroll, "アイテムを保持 (keepInventory)", True)
        self.mob_grief = self.add_switch(scroll, "モブによる破壊 (mobGriefing)", True)
        self.day_cycle = self.add_switch(scroll, "時間経過 (doDaylightCycle)", True)
        self.weather_cycle = self.add_switch(scroll, "天候変化 (doWeatherCycle)", True)
        self.pvp = self.add_switch(scroll, "プレイヤー間攻撃 (PvP)", True)

    def setup_players_tab(self):
        ctk.CTkLabel(self.tab_players, text="【招待】プレイヤーを招待", font=("MS Gothic", 14, "bold")).pack(pady=5)
        self.invite_entry = ctk.CTkEntry(self.tab_players, placeholder_text="マイクラID"); self.invite_entry.pack(pady=2, fill="x")
        ctk.CTkButton(self.tab_players, text="招待リストに追加", command=self.add_whitelist).pack(pady=5, fill="x")
        self.whitelist_scroll = ctk.CTkScrollableFrame(self.tab_players, height=180, label_text="招待済みリスト"); self.whitelist_scroll.pack(fill="x", pady=5)
        ctk.CTkLabel(self.tab_players, text="【権限】管理者を設定", font=("MS Gothic", 14, "bold")).pack(pady=(20, 5))
        self.admin_entry = ctk.CTkEntry(self.tab_players, placeholder_text="マイクラID"); self.admin_entry.pack(pady=2, fill="x")
        ctk.CTkButton(self.tab_players, text="管理者に任命", command=self.add_op).pack(pady=5, fill="x")
        self.ops_scroll = ctk.CTkScrollableFrame(self.tab_players, height=180, label_text="管理者リスト"); self.ops_scroll.pack(fill="x", pady=5)

    def refresh_member_lists(self):
        for w in self.whitelist_scroll.winfo_children(): w.destroy()
        if os.path.exists("whitelist.json"):
            try:
                with open("whitelist.json", "r") as f:
                    for p in json.load(f): ctk.CTkLabel(self.whitelist_scroll, text=f"👤 {p['name']}", anchor="w").pack(fill="x", padx=10)
            except: pass
        for w in self.ops_scroll.winfo_children(): w.destroy()
        if os.path.exists("ops.json"):
            try:
                with open("ops.json", "r") as f:
                    for p in json.load(f): ctk.CTkLabel(self.ops_scroll, text=f"⭐ {p['name']}", text_color="orange", anchor="w").pack(fill="x", padx=10)
            except: pass

    def add_whitelist(self):
        name = self.invite_entry.get(); 
        if name: self.send_command(f"whitelist add {name}"); self.invite_entry.delete(0, "end"); self.after(2000, self.refresh_member_lists)

    def add_op(self):
        name = self.admin_entry.get(); 
        if name: self.send_command(f"op {name}"); self.admin_entry.delete(0, "end"); self.after(2000, self.refresh_member_lists)

    def on_closing(self): self.force_stop(); self.destroy()

    def force_stop(self):
        if self.server_process: self.server_process.terminate()
        if self.tunnel_process: self.tunnel_process.terminate()

    def safe_stop_server(self):
        if self.server_process: self.send_command("stop"); self.log("停止コマンド送信。")

    # --- サーバー起動 ---
    def start_server(self):
        if self.server_process: return
        name = self.world_name.get()
        if not name: return
        if name not in self.worlds: self.worlds.append(name); self.save_world_list(); self.refresh_world_list_ui()

        # server.properties に設定を書き込む
        props = {
            "level-name": name,
            "level-seed": self.seed.get(),
            "level-type": self.world_type.get(),
            "generate-structures": str(self.structures.get()).lower(),
            "hardcore": str(self.hardcore.get()).lower(),
            "gamemode": self.gamemode.get(),
            "difficulty": self.difficulty.get(),
            "white-list": "true",
            "spawn-protection": "0",
            "online-mode": "true",
            "motd": self.motd.get()
        }
        with open("server.properties", "w") as f:
            for k, v in props.items(): f.write(f"{k}={v}\n")
        with open("eula.txt", "w") as f: f.write("eula=true")

        java_cmd = r"C:\Program Files\Java\jdk-26\bin\java.exe"
        if not os.path.exists(java_cmd): java_cmd = "java"

        self.current_running_world = name
        self.refresh_world_list_ui()

        def run_s():
            try:
                self.server_process = subprocess.Popen(
                    [java_cmd, "-Xmx2G", "-jar", "server.jar", "nogui"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, 
                    text=True, encoding='utf-8', errors='replace', bufsize=1
                )
                for line in self.server_process.stdout:
                    self.log(line.strip(), "SERVER")
                    if "Done" in line:
                        time.sleep(5)
                        # ゲームルール送信 (確実に true/false を送る)
                        self.send_command(f"gamerule keepInventory {'true' if self.keep_inv.get() else 'false'}")
                        self.send_command(f"gamerule mobGriefing {'true' if self.mob_grief.get() else 'false'}")
                        if self.admin_entry.get(): self.send_command(f"op {self.admin_entry.get()}")
                        self.after(1000, self.refresh_member_lists)
            except Exception as e: self.log(f"エラー: {e}", "ERROR")
            self.server_process = None; self.current_running_world = None
            self.after(0, lambda: self.addr_display.configure(text="停止中", text_color="#777"))
            self.after(0, self.refresh_world_list_ui)

        def run_t():
            files = [f for f in os.listdir('.') if 'playit' in f and f.endswith('.exe')]
            if files:
                try: self.tunnel_process = subprocess.Popen([files[0]])
                except: pass

        threading.Thread(target=run_s, daemon=True).start()
        threading.Thread(target=run_t, daemon=True).start()

    def send_command(self, cmd=None):
        c = cmd if cmd else self.cmd_entry.get()
        if self.server_process and c:
            try:
                # 余計な空白を排除
                self.server_process.stdin.write(c.strip() + "\n")
                self.server_process.stdin.flush()
                self.cmd_entry.delete(0, "end")
            except: pass

if __name__ == "__main__":
    app = MinecraftRealmsPro()
    app.mainloop()