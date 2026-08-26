import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class FestoSupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        self.is_mock = False
        if not self.url or not self.key or "your-project-id" in self.url:
            print("WARNING: Supabase credentials missing or invalid. Using Mock mode.")
            self.is_mock = True
            self.client = None
        else:
            self.client: Client = create_client(self.url, self.key)

    def check_inventory(self, sku_id: str) -> str:
        """查詢庫存"""
        if self.is_mock:
            return f"Mock庫存查詢: 產品 {sku_id} 目前庫存充足 (100 件)"
        
        try:
            # Assumes 'products' table exists with sku_id and stock columns
            response = self.client.table('products').select('*').eq('sku_id', sku_id).execute()
            data = response.data
            if data:
                stock = data[0].get('stock', 0)
                return f"產品 {sku_id} 目前庫存: {stock} 件"
            return f"找不到產品 {sku_id} 的庫存資料。"
        except Exception as e:
            return f"庫存查詢發生錯誤: {e}"

    def create_sales_order(self, client_id: str, items_json: str) -> str:
        """建立訂單"""
        if self.is_mock:
            return f"Mock訂單建立成功: 客戶 {client_id} 已購買 {items_json}"
            
        try:
            # Assumes 'orders' table exists
            response = self.client.table('orders').insert({
                "client_id": client_id,
                "items": items_json,
                "status": "Pending"
            }).execute()
            return f"訂單建立成功 (Order ID: {response.data[0].get('id')})"
        except Exception as e:
            return f"建立訂單發生錯誤: {e}"

supabase_client = FestoSupabaseClient()
