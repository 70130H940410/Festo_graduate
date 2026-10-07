import sys
from app.router_logic import router_logic

def main():
    user_id = "manual_tester_01"
    print("=" * 60)
    print("🤖 Festo LINE 機器人 本地終端互動測試工具")
    print("指令說明：")
    print(" - 輸入任何對話開始測試 (例如：'你們賣什麼', '我要買2個黑色保險絲盒', '真人客服')")
    print(" - 輸入 '/resume' 可退出真人模式並切回 AI")
    print(" - 輸入 '/cancel' 或 '取消' 可取消進行中的訂單")
    print(" - 輸入 'exit' 或 'quit' 退出測試")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n👤 測試者: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("👋 測試結束！")
                break

            response = router_logic.process_message(user_id, user_input)
            if not response:
                print("🤖 Festo Bot: [真人客服模式中，AI 保持安靜無回覆。可輸入 /resume 切回 AI]")
            else:
                print(f"🤖 Festo Bot:\n{response}")
        except KeyboardInterrupt:
            print("\n👋 測試結束！")
            break
        except Exception as e:
            print(f"❌ 發生異常: {e}")

if __name__ == "__main__":
    main()
