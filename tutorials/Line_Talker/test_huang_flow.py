import sys
sys.path.append("/workspace/tutorials/Line_Talker")
from app.router_logic import router_logic

test_user = "U2ced6c962379c726f1286b84f3f88bea"

# 確保會話是乾淨的
router_logic.order_sessions.clear_session(test_user)

print("=== 測試 1: 黃柏翰追加下單「下單 白色盒*4」===")
resp1 = router_logic.process_message(test_user, "下單 白色盒*4")
print("Response 1:\n", resp1)

print("\n=== 測試 2: 黃柏翰修改公司「更改公司名稱為測試企業」===")
resp2 = router_logic.process_message(test_user, "更改公司名稱為測試企業")
print("Response 2:\n", resp2)

print("\n=== 測試 3: 黃柏翰發送「確認訂單」===")
resp3 = router_logic.process_message(test_user, "確認訂單")
print("Response 3:\n", resp3)
