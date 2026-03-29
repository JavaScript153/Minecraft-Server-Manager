import sys, os, subprocess, threading, re, time

# --- 設定 ---
MY_ID = "System_Kenshin" 

class MinecraftRealmsPro:
    def __init__(self, headless=False):
        self.server_process = None
        self.headless = headless
        self.world_name = "KUROiworld"
        if not headless: print("GUI起動中...")

    def log(self, msg): print(msg, flush=True)

    def send_command(self, cmd):
        if self.server_process and self.server_process.stdin:
            try:
                self.server_process.stdin.write(cmd.strip() + "\n")
                self.server_process.stdin.flush()
            except: pass

    def start_server(self):
        if self.server_process: return
        
        # 【重要】接続先を127.0.0.1に、メモリを4GBに抑えて安定させます
        props = {
            "level-name": self.world_name, "white-list": "true", 
            "online-mode": "true", "spawn-protection": "0",
            "server-ip": "127.0.0.1", "server-port": "25565"
        }
        with open("server.properties", "w") as f:
            for k, v in props.items(): f.write(f"{k}={v}\n")
        with open("eula.txt", "w") as f: f.write("eula=true")

        def run():
            try:
                self.log(f">>> サーバー起動開始...")
                # メモリを4Gに下げて安定性を高めます
                self.server_process = subprocess.Popen(
                    ["java", "-Xmx4G", "-Xms4G", "-jar", "server.jar", "nogui"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                    text=True, encoding='utf-8', errors='replace', bufsize=1
                )
                
                for line in self.server_process.stdout:
                    clean_line = line.strip()
                    self.log(f"[SERVER] {clean_line}")
                    if "Done" in clean_line:
                        time.sleep(5)
                        self.send_command(f"whitelist add {MY_ID}")
                        self.send_command(f"op {MY_ID}")
            except Exception as e: self.log(f">>> エラー: {e}")
            self.server_process = None

        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    is_headless = "--headless" in sys.argv or not os.name == 'nt'
    manager = MinecraftRealmsPro(headless=is_headless)
    manager.start_server()
    while True: time.sleep(10)
