import os
import re

logs = [
    "/workspace/tutorials/Festo/Festo_Cloud_Update/Line_Talker/server.log",
    "/root/.gemini/antigravity-ide/brain/b6f589f2-a754-46d6-96b1-daf02541d734/.system_generated/tasks/task-638.log",
]

for log in logs:
    if os.path.exists(log):
        print(f"=== Reading {log} ===")
        with open(log, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            for line in lines[-100:]:  # 最近 100 行
                if any(k in line for k in ["📩", "收到", "用戶", "訊息", "Route", "黃柏翰", "訂單", "Order", "State", "Session"]):
                    print(line.strip())
