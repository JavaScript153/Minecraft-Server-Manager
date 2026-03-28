import sys
import os
import subprocess
import threading
import json
import re
import time
import shutil
import webbrowser

# --- GUIライブラリの読み込み (VPS/GitHub環境では無視される) ---
try:
    import tkinter as tk
    import customtkinter as ctk
    from tkinter import messagebox
    GUI_AVAILABLE = True
except:
    GUI_AVAILABLE = False

# --- Discordライブラリの読み込み ---
try:
    import discord
    from discord import app_commands
    DISCORD_AVAILABLE = True
except:
    DISCORD_AVAILABLE = False

# --- セキュリティ設定 (GitHub Secrets対応) ---
# 環境変数から取得。なければ空文字（ローカル用）
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
PLAYIT_SECRET = os.getenv("PLAYIT_SECRET", "")

# ==========================================
# 1. Discord Bot クラス
# ==========================================
if DISCORD_AVAILABLE:
    class MyDiscordBot(discord.Client):
        def __init__(self, manager):
            intents = discord.Intents.default()
            intents.message_content = True
            super().__init__(intents=intents)
            self.manager = manager
            self.tree = app_commands.CommandTree(self)

        async def setup_hook(self):
            @self.tree.command(name="start", description="マイクラサーバーを起動します")
            async def start(interaction: discord.Interaction):
                if self.manager.server_process:
                    await interaction.response.send_message("🟢 サーバーは既に稼働中です")
                else:
                    threading.Thread(target=self.manager.start_server).start()
                    await interaction.response.send_message("🚀 サーバーの起動を開始しました")

            @self.tree.command(name="stop", description="マイクラサーバーを停止します")
            async def stop(interaction: discord.Interaction):
                if self.manager.server_process:
                    self.manager.send_command("stop")
                    await interaction.response.send_message("🛑 停止コマンドを送信しました")
                else:
                    await interaction.response.send_message("❌ サーバーは動いていません")

            @self.tree.command(name="status", description="状態を確認します")
            async def status(interaction: discord.Interaction):
                st = "稼働中 🟢" if self.manager.server_process else "停止中 🔴"
                await interaction.response.send_message(f"📊 状態: {st}")
            await self.tree.sync()

# ==========================================
# 2. メイン管理クラス (GUI & サーバー制御)
# ==========================================
class MinecraftRealmsPro:
    def __init__(self, headless=False):
        self.server_process = None
        self.current_running_world = None
        self.config_file = "servers_list.json"
        self.headless = headless
        
        # データの読み込み
        self.worlds = self.load_world_list()
        self.auto_detect_existing_folders()

        if not headless and GUI_AVAILABLE:
            self.setup_gui()
        else:
            print(">>> Headless Mode: GUIなしで実行中...")

    def load_world_list(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f: return json.load(f)
            except: return []
        return ["KUROiworld"]

    def save_world_list(self):
        with open(self.config_file, "w") as f: json.dump(self.worlds, f)

    def auto_detect_existing_folders(self):
        exclude = ["libraries", "logs", "versions", "__pycache__"]
        for item in os.listdir('.'):
            if os.path.isdir(item) and item not in exclude:
                if os.path.exists(os.path.join(item, "level.dat")):
                    if item not in self.worlds: self.worlds.append(item)
        self.save_world_list()

    def log(self, msg, tag="INFO"):
        print(f"[{tag}] {msg}")
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

    # --- サーバー起動の核心 ---
    def start_server(self):
        if self.server_process: return
        
        # ワールド名の決定 (GUIなら入力値、Headlessならリストの最初)
        world = self.world_name_entry.get() if not self.headless else self.worlds[0]
        self.log(f"サーバー開始準備: {world}")

        # server.properties の作成
        props = {
            "level-name": world, "white-list": "true", "online-mode": "true",
            "spawn-protection": "0", "max-players": "10", "motd": "24/7 Managed Server"
        }
        with open("server.properties", "w") as f:
            for k, v in props.items(): f.write(f"{k}={v}\n")
        with open("eula.txt", "w") as f: f.write("eula=true")

        # Javaのパス検索
        java_cmd = "java"
        paths = [r"C:\Program Files\Java\jdk-26\bin\java.exe", "/usr/bin/java"]
        for p in paths:
            if os.path.exists(p): java_cmd = p; break

        def run():
            try:
                self.server_process = subprocess.Popen(
                    [java_cmd, "-Xmx6G", "-Xms6G", "-jar", "server.jar", "nogui"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace', bufsize=1
                )
                self.current_running_world = world
                for line in self.server_process.stdout:
                    clean_line = line.strip()
                    self.log(clean_line, "SERVER")
                    
                    # 全員自動管理者(OP)化
                    if "joined the game" in clean_line:
                        player = re.search(r'(\w+) joined the game', clean_line)
                        if player:
                            time.sleep(2)
                            self.send_command(f"op {player.group(1)}")
                    
                    # 起動完了後の自動設定
                    if "Done" in clean_line:
                        time.sleep(3)
                        # GUIがあればその設定、なければデフォルトtrue
                        ki = "true" if self.headless or self.keep_inv_sw.get() else "false"
                        self.send_command(f"gamerule keepInventory {ki}")

            except Exception as e: self.log(f"致命的なエラー: {e}", "ERROR")
            self.server_process = None
            self.current_running_world = None
            self.log("サーバーが停止しました。")

        threading.Thread(target=run, daemon=True).start()

    # --- GUI構築 (Windows専用) ---
    def setup_gui(self):
        self.root = ctk.CTk()
        self.root.title("Minecraft Realms Manager Pro")
        self.root.geometry("1100x800")
        
        self.root.grid_columnconfigure(0, weight=1); self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # 左側：設定
        left = ctk.CTkFrame(self.root); left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(left, text="ワールド設定", font=("MS Gothic", 20)).pack(pady=10)
        self.world_name_entry = ctk.CTkEntry(left, placeholder_text="ワールド名")
        self.world_name_entry.insert(0, self.worlds[0]); self.world_name_entry.pack(fill="x", padx=10, pady=5)
        
        self.keep_inv_sw = ctk.CTkSwitch(left, text="アイテム保持 (keepInventory)"); self.keep_inv_sw.select(); self.keep_inv_sw.pack(pady=5)
        
        ctk.CTkButton(left, text="サーバーを開始", fg_color="green", command=self.start_server).pack(pady=20, fill="x", padx=10)
        ctk.CTkButton(left, text="playit.gg ログイン", command=lambda: webbrowser.open("https://playit.gg/login")).pack(pady=5)

        # 右側：ログ
        right = ctk.CTkFrame(self.root); right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.console_box = ctk.CTkTextbox(right, fg_color="black", text_color="#00FF00", font=("Consolas", 12))
        self.console_box.pack(expand=True, fill="both", padx=5, pady=5)

        # Discord Bot 起動ボタン (GUI用)
        self.token_entry = ctk.CTkEntry(left, placeholder_text="Discord Token (空ならSecretsを使用)", show="*")
        self.token_entry.pack(pady=5, fill="x", padx=10)
        ctk.CTkButton(left, text="Discord Bot 起動", command=self.manual_bot_start).pack(pady=5)

    def manual_bot_start(self):
        token = self.token_entry.get() or DISCORD_TOKEN
        if token and DISCORD_AVAILABLE:
            threading.Thread(target=lambda: MyDiscordBot(self).run(token), daemon=True).start()
            self.log("Discord Botを起動しました。")

# ==========================================
# 3. 実行メイン
# ==========================================
if __name__ == "__main__":
    # --headless 引数があるか、GUIが使えない環境ならHeadlessモード
    is_headless = "--headless" in sys.argv or not GUI_AVAILABLE
    
    manager = MinecraftRealmsPro(headless=is_headless)
    
    if is_headless:
        # GitHub Actions用：自動でサーバーとボットを開始
        if DISCORD_AVAILABLE and DISCORD_TOKEN:
            threading.Thread(target=lambda: MyDiscordBot(manager).run(DISCORD_TOKEN), daemon=True).start()
        
        # サーバー本体を開始
        manager.start_server()
        
        # 6時間制限（Actions）のために待機。Ctrl+Cでも止まる
        try:
            while True: time.sleep(10)
        except KeyboardInterrupt:
            print("Stopping server...")
            manager.send_command("stop")
            time.sleep(10)
    else:
        manager.root.mainloop()