import os, subprocess, threading, time, sys, re

# 管理者ID
MY_ID = "System_Kenshin"

class MinecraftRunner:
    def __init__(self):
        self.proc = None

    def send(self, cmd):
        if self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write(cmd.strip() + "\n")
                self.proc.stdin.flush()
            except: pass

    def start(self):
        # 1. 接続をplayitと確実に握手させる設定
        props = {
            "level-name": "KUROiworld",
            "white-list": "true",
            "online-mode": "true",
            "server-port": "25565",
            "server-ip": "127.0.0.1", # playitと同じ内部IPに固定
            "spawn-protection": "0",
            "pause-when-empty-automated": "false" # 自動停止をオフ
        }
        with open("server.properties", "w") as f:
            for k, v in props.items(): f.write(f"{k}={v}\n")
        with open("eula.txt", "w") as f: f.write("eula=true")

        # 2. サーバー起動
        def run():
            try:
                # メモリを4Gに抑えて安定させる
                self.proc = subprocess.Popen(
                    ["java", "-Xmx4G", "-Xms4G", "-jar", "server.jar", "nogui"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                    stdin=subprocess.PIPE, text=True, bufsize=1
                )
                for line in self.proc.stdout:
                    msg = line.strip()
                    print(f"[SERVER] {msg}", flush=True)
                    if "Done" in msg:
                        time.sleep(5)
                        self.send(f"whitelist add {MY_ID}")
                        self.send(f"op {MY_ID}")
                        print(">>> サーバーが正常に準備できました")
            except Exception as e: print(f"Error: {e}")

        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    runner = MinecraftRunner()
    runner.start()
    while True: time.sleep(10)
