import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        # Default mock endpoints if env vars are missing
        self.llama_url = os.getenv("LLAMA_ENDPOINT", "http://192.168.50.168:22530/v1")
        self.gemma_url = os.getenv("GEMMA_ENDPOINT", "http://192.168.50.168:26615/v1")
        self.qwen_url = os.getenv("QWEN_ENDPOINT", "http://192.168.50.168:21909/v1")
        
        # We assume local models don't need real API keys, but the client requires the parameter.
        self.dummy_key = "EMPTY"

    def get_client(self, model_type: str) -> OpenAI:
        """Helper to get the right client based on model type."""
        if model_type == "llama":
            return OpenAI(base_url=self.llama_url, api_key=self.dummy_key)
        elif model_type == "gemma":
            return OpenAI(base_url=self.gemma_url, api_key=self.dummy_key)
        elif model_type == "qwen":
            return OpenAI(base_url=self.qwen_url, api_key=self.dummy_key)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def generate_response(self, model_type: str, system_prompt: str, user_message: str, model_name: str = "default", history: list = None) -> str:
        """Synchronously calls the LLM."""
        print(f"   🧠 [LLM 呼叫] 呼叫模型: {model_type.upper()} ({model_name})")
        print(f"      - User Msg: {user_message}")
        try:
            client = self.get_client(model_type)
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": user_message})

            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            result = response.choices[0].message.content
            print(f"      - 回應: {result.strip()}")
            return result
        except Exception as e:
            print(f"      ❌ [錯誤] 呼叫 {model_type} 失敗: {e}")
            return f"[系統提示] 呼叫 {model_type} 失敗，請確認模型是否啟動或使用 Mock。"

llm_client = LLMClient()
