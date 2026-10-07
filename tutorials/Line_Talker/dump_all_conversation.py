import glob
import os

task_logs = glob.glob("/root/.gemini/antigravity-ide/brain/b6f589f2-a754-46d6-96b1-daf02541d734/.system_generated/tasks/*.log")

print(f"Found {len(task_logs)} task logs.")

for tl in sorted(task_logs):
    with open(tl, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        if "88bea" in content or "黃柏翰" in content:
            print(f"\n==================== Log: {os.path.basename(tl)} ====================")
            for line in content.splitlines():
                if any(k in line for k in ["收到新訊息", "User Msg", "回應:", "處理流程", "訂單摘要", "訂單建立成功", "訂單編號", "更改", "查詢"]):
                    print(line[:150])
