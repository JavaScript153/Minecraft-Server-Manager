import sys, os, subprocess, threading, time, re

# あなたのマイクラID（管理者用）
MY_ID = "System_Kenshin"

class MinecraftManager:
    def __init__(self):
        self.server_process = None
        # 自分のPCかGitHub Actionsかを判定
        self.is_github = os.getenv("GITHUB_ACTIONS") == "true"
        self.world_name = "KUROiworld"

    def log(self, msg):
        print(f"[LOG] {msg}", flush=True)

    def send_command(self, cmd):
        if self.server_process and self.server_process.stdin:
            try:
                # 余計な文字を排除して送信
                clean_cmd = cmd.strip().replace('\r', '') + "\n"
                self.server_process.stdin.write(clean_cmd)
                self.server_process.stdin.flush()
            except: pass

    def start(self):
        # 1. サーバー設定を「GitHub Actions専用」に強制書き換え
        # server-ipを空にすることで、内部ネットワークの制限を回避します
        props = {
            "level-name": self.world_name,
            "white-list": "true",
            "online-mode": "true",
            "server-ip": "", 
            "server-port": "25565",
            "spawn-protection": "0",
            "pause-when-empty-automated": "false"
        }
        with open("server.properties", "w") as f:
            for k, v in props.items(): f.write(f"{k}={v}\n")
        with open("eula.txt", "w") as f: f.write("eula=true")

        # 2. Javaの起動 (メモリを4GBに絞ってplayit用の余力を残す)
        java_cmd = "java"
        # 自分のPC(Windows)ならパスを探す
        if os.name == 'nt' and os.path.exists(r"C:\Program Files\Java\jdk-26\bin\java.exe"):
            java_cmd = r"C:\Program Files\Java\jdk-26\bin\java.exe"

        def run_server():
            try:
                self.log("マイクラサーバーを起動しています...")
                self.server_process = subprocess.Popen(
                    [java_cmd, "-Xmx4G", "-Xms4G", "-jar", "server.jar", "nogui"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace', bufsize=1
                )

                for line in self.server_process.stdout:
                    clean_line = line.strip()
                    print(f"[SERVER] {clean_line}", flush=True)
                    
                    # 起動完了時に自分を招待
                    if "Done" in clean_line:
                        time.sleep(5)
                        self.send_command(f"whitelist add {MY_ID}")
                        self.send_command(f"op {MY_ID}")
                        self.log(f"*** {MY_ID} を管理者として招待しました ***")

            except Exception as e:
                self.log(f"エラーが発生しました: {e}")

        threading.Thread(target=run_server, daemon=True).start()

if __name__ == "__main__":
    manager = MinecraftManager()
    manager.start()
    # GitHub Actionsが終了しないように無限ループ
    while True:
        time.sleep(10)
