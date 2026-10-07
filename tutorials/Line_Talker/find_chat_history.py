import sys
import os
sys.path.append("/workspace/tutorials/Line_Talker")
from app.supabase_client import supabase_client

# 檢查 Supabase 是否有對話相關 table
sb = supabase_client.client
candidate_tables = [
    "chat_history", "messages", "conversations", "line_messages", 
    "line_chat", "chat_logs", "user_logs", "dialogs", "line_users",
    "customer_messages", "audit_logs"
]

print("=== Checking Supabase tables ===")
for t in candidate_tables:
    try:
        r = sb.table(t).select("*").limit(3).execute()
        print(f"Table '{t}' EXISTS! Count: {len(r.data)}")
        if r.data:
            print(" Sample:", r.data[0])
    except Exception as e:
        # 表不存在通常會報錯
        pass

# 檢查本機日誌檔案
print("\n=== Checking local log files in Line_Talker & Festo ===")
for base in ["/workspace/tutorials/Line_Talker", "/workspace/tutorials/Festo"]:
    for root, dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".log") or "chat" in f or "history" in f or "dialog" in f:
                p = os.path.join(root, f)
                print(f"Log/data file: {p} (size: {os.path.getsize(p)} bytes)")

