from app.llm_client import llm_client
from app.supabase_client import supabase_client

class RouterLogic:
    def process_message(self, user_id: str, message: str) -> str:
        # Step 1: Llama decides the intent
        intent_prompt = """
        你是 Festo 工業自動化設備的客服系統總機。
        請判斷使用者的意圖，只能回答以下四種之一：
        - INQUIRY (詢問庫存、規格、FAQ)
        - ORDER (採購下單)
        - REPAIR (機台報修、技術排障)
        - OTHER (閒聊或其他)
        """
        
        intent_response = llm_client.generate_response(
            model_type="llama",
            system_prompt=intent_prompt,
            user_message=message,
            model_name="meta-llama/Llama-3.1-8B-Instruct"
        ).strip().upper()
        
        # We simulate intent matching since LLM might output extra text
        if "ORDER" in intent_response:
            return self._handle_order(user_id, message)
        elif "REPAIR" in intent_response:
            return self._handle_repair(user_id, message)
        else:
            return self._handle_inquiry(user_id, message)

    def _handle_inquiry(self, user_id: str, message: str) -> str:
        # Step 2: Use Llama for simple fast response (simulating RAG/FAQ)
        sys_prompt = "你是 Festo 的客服，請以專業禮貌的語氣回答問題。"
        return llm_client.generate_response(
            model_type="llama",
            system_prompt=sys_prompt,
            user_message=message,
            model_name="meta-llama/Llama-3.1-8B-Instruct"
        )

    def _handle_order(self, user_id: str, message: str) -> str:
        # Step 2: Use Gemma to extract JSON
        sys_prompt = """
        請從使用者的訊息中萃取出採購資訊，並以 JSON 格式回傳。
        包含：'model' (型號), 'quantity' (數量)。
        如果資訊不足，請回答 MISSING_INFO。
        """
        extraction = llm_client.generate_response(
            model_type="gemma",
            system_prompt=sys_prompt,
            user_message=message,
            model_name="cyankiwi/gemma-4-26B-A4B-it-AWQ-8bit"
        )
        
        if "MISSING_INFO" in extraction:
            return "為了幫您建立採購單，請提供完整的產品型號與數量。"
            
        # Call Supabase
        result = supabase_client.create_sales_order(client_id=user_id, items_json=extraction)
        return f"已為您處理訂單。\n{result}"

    def _handle_repair(self, user_id: str, message: str) -> str:
        # Step 2: Use Qwen for complex troubleshooting
        sys_prompt = "你是 Festo 資深技術工程師 (FAE)。請協助客戶排解設備異常問題。如果不確定，請請客戶提供錯誤代碼。"
        return llm_client.generate_response(
            model_type="qwen",
            system_prompt=sys_prompt,
            user_message=message,
            model_name="Qwen/Qwen3.6-35B-A3B-FP8"
        )

router_logic = RouterLogic()
