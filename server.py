import os, subprocess, threading, time, sys

# 管理者ID（自分のマイクラ名に書き換えてください）
MY_ID = "System_Kenshin"

class MinecraftRunner:
    def __init__(self):
        self.proc = None

    def send(self, cmd):
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(cmd.strip() + "\n")
            self.proc.stdin.flush()

    def start(self):
        # 1. server.properties を強制設定
        # server-ipを空欄に、ポートを25565に固定
        props = {
            "level-name": "KUROiworld",
            "white-list": "true",
            "online-mode": "true",
            "server-port": "25565",
            "server-ip": "0.0.0.0",
            "spawn-protection": "0",
            "pause-when-empty-automated": "false"
        }
        with open("server.properties", "w") as f:
            for k, v in props.items(): f.write(f"{k}={v}\n")
        with open("eula.txt", "w") as f: f.write("eula=true")

        # 2. サーバー起動（Java 26対応）
        cmd = ["java", "-Xmx6G", "-Xms6G", "-jar", "server.jar", "nogui"]
        print(f">>> 起動コマンド: {' '.join(cmd)}")

        def run():
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                stdin=subprocess.PIPE, text=True, bufsize=1
            )
            for line in self.proc.stdout:
                msg = line.strip()
                print(f"[SERVER] {msg}", flush=True)
                
                if "Done" in msg:
                    time.sleep(5)
                    self.send(f"whitelist add {MY_ID}")
                    self.send(f"op {MY_ID}")
                    print(f">>> {MY_ID} を招待し、管理者にしました。")

        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    runner = MinecraftRunner()
    runner.start()
    # 6時間動き続けるためのループ
    while True:
        time.sleep(10)
