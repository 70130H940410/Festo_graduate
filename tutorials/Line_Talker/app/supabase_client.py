import os
import json
import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class FestoSupabaseClient:
    """
    Line_Talker 專用的 Supabase 客戶端。
    直接讀取 Festo MES 雲端資料庫（Supabase）的真實庫存資料，
    並將 LINE 訂單寫入雲端 orders 表。

    庫存來源：
      - tbl_buffer_pos: ASRS 倉儲 32 個位置的即時狀態
        - f_no 欄位：0=空位, 25=銀色盤子, 210=黑色, 410=藍色, 610=白色
      - products: 產品主檔（名稱、價格、庫存數字）

    訂單寫入：
      - line_orders: LINE Bot 產生的訂單（含適用者資訊）
    """

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
            print(f"✅ [Supabase] Connected to {self.url}")

    # ─── PNo 顏色代碼對應 ────────────────────────────────────
    # Festo MES tblBufferPos 中 PNo (f_no) 的對應關係
    FNO_TO_COLOR = {
        210: "Black",
        410: "Blue",
        610: "White",
    }

    COLOR_TO_PRODUCT_NAME = {
        "Black": "Basic Fuse Box - Black",
        "Blue":  "Basic Fuse Box - Blue",
        "White": "Basic Fuse Box - White",
    }

    # ─── Mock 產品資料（無 Supabase 連線時使用）───────────────
    MOCK_PRODUCTS = [
        {"id": 1, "name": "Basic Fuse Box - Black", "description": "黑色上蓋標準保險絲盒", "base_price": 100, "stock": 71},
        {"id": 2, "name": "Basic Fuse Box - Blue",  "description": "藍色上蓋標準保險絲盒", "base_price": 100, "stock": 69},
        {"id": 3, "name": "Basic Fuse Box - White", "description": "白色上蓋標準保險絲盒", "base_price": 100, "stock": 76},
    ]

    MOCK_BUFFER = [
        {"buf_pos": i, "f_no": [210, 410, 610, 0, 25][i % 5], "o_no": 0,
         "quantity": 1 if [210, 410, 610, 0, 25][i % 5] in (210, 410, 610) else 0}
        for i in range(32)
    ]

    # ═══════════════════════════════════════════════════════════
    # 倉儲即時狀態（tbl_buffer_pos）
    # ═══════════════════════════════════════════════════════════

    def get_buffer_positions(self) -> list[dict]:
        """
        從 Supabase 讀取 ASRS 倉儲 32 個位置的即時狀態。
        回傳: [{"buf_pos": int, "f_no": int, "o_no": int, "quantity": int, ...}, ...]
        """
        if self.is_mock:
            return self.MOCK_BUFFER

        try:
            resp = self.client.table("tbl_buffer_pos").select(
                "buf_pos,f_no,o_no,u_pos,type,zone,quantity,quantity_max,time_stamp,pallet_id"
            ).order("buf_pos").execute()
            return resp.data if resp.data else []
        except Exception as e:
            print(f"❌ [Supabase] 讀取 tbl_buffer_pos 失敗: {e}")
            return []

    def get_warehouse_inventory(self) -> dict:
        """
        從 tbl_buffer_pos 計算各顏色產品的倉儲即時庫存。

        邏輯：掃描 32 個位置，根據 f_no 判斷有哪些產品在倉庫中。
          - f_no=210 → 黑色 (Black)
          - f_no=410 → 藍色 (Blue)
          - f_no=610 → 白色 (White)
          - f_no=0   → 空位
          - f_no=25  → 銀色盤子（不算產品庫存）

        回傳:
            {
                "Basic Fuse Box - Black": {"count": 8, "positions": [1, 5, 9, ...]},
                "Basic Fuse Box - Blue":  {"count": 6, "positions": [2, 6, ...]},
                "Basic Fuse Box - White": {"count": 10, "positions": [3, 7, ...]},
                "empty": {"count": 5, "positions": [4, 8, ...]},
                "total_occupied": 24,
                "total_capacity": 32,
            }
        """
        positions = self.get_buffer_positions()

        inventory = {}
        for color, product_name in self.COLOR_TO_PRODUCT_NAME.items():
            inventory[product_name] = {"count": 0, "positions": []}

        empty_count = 0
        empty_positions = []

        for pos in positions:
            f_no = int(pos.get("f_no", 0))
            buf_pos = int(pos.get("buf_pos", 0))

            if f_no in self.FNO_TO_COLOR:
                color = self.FNO_TO_COLOR[f_no]
                product_name = self.COLOR_TO_PRODUCT_NAME[color]
                inventory[product_name]["count"] += 1
                inventory[product_name]["positions"].append(buf_pos)
            elif f_no == 0:
                empty_count += 1
                empty_positions.append(buf_pos)
            # f_no=25 (銀色盤子) 不計入產品庫存

        total_occupied = sum(v["count"] for v in inventory.values())

        inventory["empty"] = {"count": empty_count, "positions": empty_positions}
        inventory["total_occupied"] = total_occupied
        inventory["total_capacity"] = 32

        return inventory

    # ═══════════════════════════════════════════════════════════
    # 產品查詢（products 表）
    # ═══════════════════════════════════════════════════════════

    def get_all_products(self) -> list:
        """取得所有產品清單（含庫存數字）"""
        if self.is_mock:
            return self.MOCK_PRODUCTS

        try:
            response = self.client.table('products').select('*').execute()
            return response.data if response.data else self.MOCK_PRODUCTS
        except Exception as e:
            print(f"❌ [Supabase] 取得產品清單失敗: {e}，使用倉儲即時庫存")
            # fallback：從 tbl_buffer_pos 計算庫存
            return self._products_from_warehouse()

    def _products_from_warehouse(self) -> list:
        """
        若 products 表不可用，從 tbl_buffer_pos 即時計算產品庫存。
        """
        warehouse = self.get_warehouse_inventory()
        products = []
        product_defaults = {
            "Basic Fuse Box - Black": {"id": 1, "description": "黑色上蓋標準保險絲盒", "base_price": 100},
            "Basic Fuse Box - Blue":  {"id": 2, "description": "藍色上蓋標準保險絲盒", "base_price": 100},
            "Basic Fuse Box - White": {"id": 3, "description": "白色上蓋標準保險絲盒", "base_price": 100},
        }
        for name, defaults in product_defaults.items():
            wh_data = warehouse.get(name, {})
            products.append({
                "id": defaults["id"],
                "name": name,
                "description": defaults["description"],
                "base_price": defaults["base_price"],
                "stock": wh_data.get("count", 0),
            })
        return products

    def get_product_by_name(self, product_name: str) -> dict | None:
        """
        以產品名稱查詢產品資訊（精確比對）。
        回傳 dict 包含 id, name, base_price, stock 等，或 None。
        """
        if self.is_mock:
            for p in self.MOCK_PRODUCTS:
                if p["name"].lower() == product_name.lower():
                    return p.copy()
            return None

        try:
            response = (
                self.client.table('products')
                .select('*')
                .eq('name', product_name)
                .execute()
            )
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"⚠️ [Supabase] products 表查詢失敗，嘗試從倉儲計算: {e}")

        # fallback：從 warehouse 計算
        warehouse = self.get_warehouse_inventory()
        if product_name in warehouse:
            wh = warehouse[product_name]
            defaults = {
                "Basic Fuse Box - Black": {"id": 1, "description": "黑色上蓋標準保險絲盒", "base_price": 100},
                "Basic Fuse Box - Blue":  {"id": 2, "description": "藍色上蓋標準保險絲盒", "base_price": 100},
                "Basic Fuse Box - White": {"id": 3, "description": "白色上蓋標準保險絲盒", "base_price": 100},
            }
            if product_name in defaults:
                d = defaults[product_name]
                return {
                    "id": d["id"],
                    "name": product_name,
                    "description": d["description"],
                    "base_price": d["base_price"],
                    "stock": wh["count"],
                }
        return None

    # ═══════════════════════════════════════════════════════════
    # 庫存查詢
    # ═══════════════════════════════════════════════════════════

    def check_inventory(self, sku_id: str) -> str:
        """查詢單一產品庫存（保留舊介面，向後相容）"""
        if self.is_mock:
            return f"Mock庫存查詢: 產品 {sku_id} 目前庫存充足 (100 件)"

        try:
            response = self.client.table('products').select('*').eq('sku_id', sku_id).execute()
            data = response.data
            if data:
                stock = data[0].get('stock', 0)
                return f"產品 {sku_id} 目前庫存: {stock} 件"
            return f"找不到產品 {sku_id} 的庫存資料。"
        except Exception as e:
            return f"庫存查詢發生錯誤: {e}"

    def check_inventory_batch(self, items: list[dict]) -> list[dict]:
        """
        批量庫存查詢。優先使用 tbl_buffer_pos 即時倉儲資料。

        參數 items: [{"product_name": str, "quantity": int}, ...]
        回傳: [{"product_name": str, "quantity": int, "stock": int,
                "unit_price": int, "in_stock": bool, "product_id": int | None,
                "warehouse_positions": list[int]}, ...]
        """
        # 取得倉儲即時庫存
        warehouse = self.get_warehouse_inventory()
        print(f"📊 [倉儲即時狀態] 佔用 {warehouse['total_occupied']}/{warehouse['total_capacity']} 位置")
        for pname in self.COLOR_TO_PRODUCT_NAME.values():
            wh = warehouse.get(pname, {})
            print(f"   {pname}: {wh.get('count', 0)} 件 (位置: {wh.get('positions', [])})")

        results = []
        for item in items:
            name = item["product_name"]
            qty = item["quantity"]

            # 從工廠 ASRS 倉儲取得即時庫存 (SSOT)
            wh_data = warehouse.get(name, {})
            wh_stock = wh_data.get("count", 0)
            wh_positions = wh_data.get("positions", [])

            # 取得產品基本資訊（單價、未入倉儲庫存、ID 等）
            product = self.get_product_by_name(name)

            if product:
                # 庫存以 ASRS 倉儲即時資料為唯一可信來源 (SSOT)
                # products.stock 可能是過時的靜態數字，不參與計算
                total_available = wh_stock
                results.append({
                    "product_name": name,
                    "quantity": qty,
                    "warehouse_stock": wh_stock,           # ASRS 倉儲實體庫存
                    "unwarehoused_stock": 0,
                    "product_stock": 0,
                    "stock": total_available,              # 總庫存 (顯示給客戶，供下單校驗)
                    "total_stock": total_available,
                    "unit_price": product.get("base_price", 100),
                    "in_stock": total_available >= qty,
                    "product_id": product.get("id"),
                    "warehouse_positions": wh_positions,
                })
            else:
                results.append({
                    "product_name": name,
                    "quantity": qty,
                    "warehouse_stock": 0,
                    "unwarehoused_stock": 0,
                    "product_stock": 0,
                    "stock": 0,
                    "total_stock": 0,
                    "unit_price": 0,
                    "in_stock": False,
                    "product_id": None,
                    "warehouse_positions": [],
                })
        return results

    # ═══════════════════════════════════════════════════════════
    # 訂單建立
    # ═══════════════════════════════════════════════════════════

    def create_sales_order(self, client_id: str, items_json: str) -> str:
        """建立訂單（舊介面，向後相容）"""
        if self.is_mock:
            return f"Mock訂單建立成功: 客戶 {client_id} 已購買 {items_json}"

        try:
            response = self.client.table('orders').insert({
                "client_id": client_id,
                "items": items_json,
                "status": "Pending"
            }).execute()
            return f"訂單建立成功 (Order ID: {response.data[0].get('id')})"
        except Exception as e:
            return f"建立訂單發生錯誤: {e}"

    def create_full_order(
        self,
        client_id: str,
        items: list[dict],
        contact_info: dict,
        total_price: int,
    ) -> dict:
        """
        建立完整訂單（含適用者資訊）並寫入 Supabase line_orders 表。

        參數:
            client_id:    LINE user_id
            items:        [{"product_name": str, "quantity": int, "unit_price": int}, ...]
            contact_info: {"name": str, "phone": str, "company": str, "address": str}
            total_price:  訂單總金額

        回傳:
            {"success": bool, "message": str, "order_id": str | None}
        """
        formatted_client_id = f"line:{client_id}" if not client_id.startswith("line:") else client_id
        payload_items = {
            "order_items": items,
            "source": "line",
            "note": contact_info.get("note", "無備註"),
            "process_steps": "1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9",
        }
        order_data = {
            "client_id": formatted_client_id,
            "items": json.dumps(payload_items, ensure_ascii=False),
            "contact_name": contact_info.get("name", ""),
            "contact_phone": contact_info.get("phone", ""),
            "company": contact_info.get("company", ""),
            "address": contact_info.get("address", ""),
            "total_price": total_price,
            "status": "Confirmed",
            "created_at": datetime.datetime.now().isoformat(),
        }

        if self.is_mock:
            mock_id = f"MOCK-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            print(f"📝 [Mock 訂單] 訂單 {mock_id} 建立成功")
            print(f"   品項: {order_data['items']}")
            print(f"   聯絡人: {order_data['contact_name']} / {order_data['contact_phone']}")
            print(f"   公司: {order_data['company']}")
            print(f"   地址: {order_data['address']}")
            print(f"   總金額: ${total_price}")
            return {
                "success": True,
                "message": f"訂單建立成功！（訂單編號：{mock_id}）",
                "order_id": mock_id,
            }

        try:
            # 寫入 line_orders 表（LINE Bot 專用訂單表）
            response = self.client.table('line_orders').insert(order_data).execute()
            order_id = response.data[0].get('id', 'N/A') if response.data else 'N/A'

            print(f"✅ [Supabase] 訂單 {order_id} 已寫入 line_orders 表")
            print(f"   品項: {order_data['items']}")
            print(f"   聯絡人: {order_data['contact_name']} / {order_data['contact_phone']}")

            return {
                "success": True,
                "message": f"訂單建立成功！（訂單編號：{order_id}）",
                "order_id": str(order_id),
            }
        except Exception as e:
            print(f"❌ [Supabase] 建立訂單失敗: {e}")
            return {
                "success": False,
                "message": f"訂單建立失敗：{e}",
                "order_id": None,
            }

    # ═══════════════════════════════════════════════════════════
    # 訂單歷史查詢（支援單一客戶多筆訂單）
    # ═══════════════════════════════════════════════════════════

    def get_orders_by_client_id(self, client_id: str) -> list[dict]:
        """
        依據 LINE client_id 查詢該用戶所有歷史訂單。
        按建立時間/編號由新到舊排序。
        """
        if self.is_mock:
            return []

        raw_id = client_id.replace("line:", "").strip()
        possible_ids = [raw_id, f"line:{raw_id}"]

        try:
            response = (
                self.client.table('line_orders')
                .select('*')
                .in_('client_id', possible_ids)
                .order('id', desc=True)
                .execute()
            )
            orders = response.data if response.data else []
            print(f"📋 [Supabase] 查到客戶 {raw_id[-6:]} 共有 {len(orders)} 筆訂單紀錄")
            return orders
        except Exception as e:
            print(f"❌ [Supabase] 查詢客戶訂單失敗: {e}")
            return []

    def search_orders(self, field: str, value: str, user_id: str = None) -> list[dict]:
        """
        依據指定欄位搜尋訂單（支援模糊搜尋）。
        
        Args:
            field: 搜尋欄位名稱，支援 "contact_name", "company", "contact_phone", "id"
            value: 搜尋值
            user_id: 可選，若提供則限縮搜尋範圍至該使用者
        
        Returns:
            符合條件的訂單列表
        """
        if self.is_mock:
            return []

        try:
            if field == "id":
                # 精確查詢訂單編號
                response = (
                    self.client.table('line_orders')
                    .select('*')
                    .eq('id', int(value))
                    .execute()
                )
            else:
                # 模糊搜尋（使用 ilike）
                db_field_map = {
                    "contact_name": "contact_name",
                    "company": "company",
                    "contact_phone": "contact_phone",
                }
                db_field = db_field_map.get(field)
                if not db_field:
                    print(f"⚠️ [Supabase] 不支援的搜尋欄位: {field}")
                    return []

                response = (
                    self.client.table('line_orders')
                    .select('*')
                    .ilike(db_field, f'%{value}%')
                    .order('id', desc=True)
                    .execute()
                )

            orders = response.data if response.data else []
            print(f"🔍 [Supabase] 條件搜尋 ({field}={value}) 找到 {len(orders)} 筆訂單")
            return orders
        except Exception as e:
            print(f"❌ [Supabase] 條件搜尋訂單失敗: {e}")
            return []

    def format_orders_for_user(self, orders: list[dict]) -> str:
        """
        將使用者的歷史訂單格式化為美觀親切的 LINE 訊息文字。
        """
        if not orders:
            return (
                "🔍 目前查無您的歷史訂單紀錄。\n\n"
                "如需採購下單，請隨時告訴我您需要的品項與數量（例如：「我要訂 10 個黑色保險絲盒」），我會立即協助您建立訂單！"
            )

        status_map = {
            "Confirmed": "已確認（工廠排產中）",
            "active": "工廠生產中",
            "Pending": "待處理",
            "Completed": "已完工出貨",
            "Cancelled": "已取消",
        }

        count = len(orders)
        lines = [f"📋 為您查到 {count} 筆訂單紀錄：", ""]

        for idx, o in enumerate(orders, 1):
            oid = o.get("id", "—")
            raw_status = o.get("status", "Confirmed")
            display_status = status_map.get(raw_status, raw_status)
            total_price = o.get("total_price", 0)
            contact_name = o.get("contact_name") or "—"
            contact_phone = o.get("contact_phone") or "—"
            address = o.get("address") or "—"
            mes_ono = o.get("mes_ono")
            if not mes_ono and "MES ONo:" in str(raw_status):
                try:
                    mes_ono = int(str(raw_status).split("MES ONo:")[1].split(")")[0].strip())
                    display_status = f"🏭 工廠全自動排產加工中 (工單 ONo: {mes_ono})"
                except Exception:
                    pass

            # 嘗試查詢本地工廠即時加工進度
            factory_detail = None
            try:
                import sqlite3
                sqlite_path = "/workspace/tutorials/Festo/shopping_website/database/order_management.db"
                if os.path.exists(sqlite_path):
                    s_conn = sqlite3.connect(sqlite_path)
                    s_cur = s_conn.cursor()
                    s_cur.execute(
                        "SELECT state, count(*) FROM piece_step_progress WHERE order_id = ? OR order_id = ? GROUP BY state",
                        (f"LINE-{int(oid):04d}", str(oid))
                    )
                    prog_rows = dict(s_cur.fetchall())
                    total_steps = sum(prog_rows.values())
                    fin_steps = prog_rows.get("finished", 0)
                    if total_steps > 0:
                        pct = int((fin_steps / total_steps) * 100)
                        s_cur.execute(
                            "SELECT station FROM station_state WHERE current_order_id = ? OR current_order_id = ?",
                            (f"LINE-{int(oid):04d}", str(oid))
                        )
                        st_row = s_cur.fetchone()
                        cur_st = st_row[0] if st_row else "機台調度流水線中"
                        if pct >= 100:
                            factory_detail = "✅ 工廠全工序加工完畢，已出庫！"
                        else:
                            factory_detail = f"⚙️ 產線實時進度 {pct}% (正在 {cur_st})"
                    s_conn.close()
            except Exception:
                pass

            # 處理時間（轉成在地日期時間）
            created_at_str = o.get("created_at", "")
            time_display = created_at_str[:16].replace("T", " ") if created_at_str else "—"

            lines.append(f"📦 訂單編號：#{oid}")
            if mes_ono:
                lines.append(f"  🏭 工廠工令：{mes_ono}")
            lines.append(f"  📅 下單時間：{time_display}")
            lines.append(f"  🏷️ 處理狀態：{display_status}")
            if factory_detail:
                lines.append(f"  {factory_detail}")

            # 解析訂購品項
            items_raw = o.get("items")
            parsed_items = []
            if isinstance(items_raw, list):
                parsed_items = items_raw
            elif isinstance(items_raw, dict):
                parsed_items = items_raw.get("order_items", [])
            elif isinstance(items_raw, str):
                try:
                    loaded = json.loads(items_raw)
                    if isinstance(loaded, list):
                        parsed_items = loaded
                    elif isinstance(loaded, dict):
                        parsed_items = loaded.get("order_items", [])
                except Exception:
                    pass

            if parsed_items:
                lines.append("  🛒 訂購品項：")
                for it in parsed_items:
                    pname = it.get("product_name") or it.get("name") or "產品"
                    pqty = it.get("quantity") or it.get("qty") or 1
                    puprice = it.get("unit_price")
                    price_note = f"（單價 NT${puprice}）" if puprice else ""
                    lines.append(f"    • {pname} × {pqty} 件 {price_note}".rstrip())
            elif isinstance(items_raw, str) and items_raw:
                lines.append(f"  🛒 訂購品項：{items_raw[:50]}")

            lines.append(f"  💰 訂單總額：NT${total_price:,}")
            lines.append(f"  👤 收件資訊：{contact_name}（{contact_phone}）")
            if address and address != "—":
                lines.append(f"  📍 送貨地址：{address}")

            if idx < count:
                lines.append("──────────────────")

        lines.append("\n💡 若需查詢特定訂單的工廠生產步驟進度，或需調整訂單，請隨時告訴我！")
        return "\n".join(lines)

    def update_order_info(self, client_id: str, field_key: str, new_value: str, order_id: int | None = None) -> dict:
        """
        修改已成立訂單的收件人、電話、公司、地址等資訊。
        若未指定 order_id，預設修改該客戶最新一筆未完工的訂單。
        """
        orders = self.get_orders_by_client_id(client_id)
        if not orders:
            return {"success": False, "message": "目前查無您的訂單紀錄，無法修改。"}

        target_order = None
        if order_id:
            target_order = next((o for o in orders if o.get("id") == order_id), None)
            if not target_order:
                return {"success": False, "message": f"找不到訂單編號 #{order_id}。"}
        else:
            # 優先找最新一筆未完工/未取消的訂單
            target_order = next((o for o in orders if o.get("status") not in ("Completed", "Cancelled")), orders[0])

        target_id = target_order["id"]
        status = target_order.get("status", "Confirmed")

        if status == "Completed":
            return {
                "success": False,
                "message": f"訂單 #{target_id} 已經完工出貨，無法修改資料。如需協助請輸入「真人」由客服專員為您處理！"
            }
        if status == "Cancelled":
            return {
                "success": False,
                "message": f"訂單 #{target_id} 已經取消，無法修改資料。"
            }

        field_name_map = {
            "name": "contact_name",
            "contact_name": "contact_name",
            "phone": "contact_phone",
            "contact_phone": "contact_phone",
            "company": "company",
            "address": "address",
            "note": "note",
        }

        db_col = field_name_map.get(field_key, field_key)

        try:
            # 更新 Supabase line_orders
            self.client.table("line_orders").update({db_col: new_value}).eq("id", target_id).execute()
            print(f"✅ [Supabase] 訂單 #{target_id} 的 {db_col} 已更新為：{new_value}")

            # 同步更新 SQLite
            try:
                import sqlite3
                sqlite_path = "/workspace/tutorials/Festo/shopping_website/database/order_management.db"
                if os.path.exists(sqlite_path):
                    conn = sqlite3.connect(sqlite_path)
                    cur = conn.cursor()
                    cur.execute(
                        f"UPDATE order_list SET {db_col} = ? WHERE supabase_order_id = ? OR order_id = ?",
                        (new_value, target_id, f"LINE-{target_id:04d}")
                    )
                    conn.commit()
                    conn.close()
            except Exception as se:
                print(f"⚠️ [OrderUpdate] SQLite 同步更新失敗: {se}")

            return {
                "success": True,
                "order_id": target_id,
                "field": db_col,
                "new_value": new_value,
                "message": f"訂單 #{target_id} 資料更新成功！"
            }
        except Exception as e:
            print(f"❌ [Supabase] 更新訂單失敗: {e}")
            return {"success": False, "message": f"更新訂單失敗: {e}"}

    def cancel_order(self, client_id: str, order_id: int | None = None) -> dict:
        """
        取消（軟刪除）已成立的訂單。
        將訂單狀態設為 'Cancelled'，不會從資料庫中刪除。
        若未指定 order_id，預設取消最新一筆未完工的訂單。
        """
        orders = self.get_orders_by_client_id(client_id)
        if not orders:
            return {"success": False, "message": "目前查無您的訂單紀錄，無法取消。"}

        target_order = None
        if order_id:
            target_order = next((o for o in orders if o.get("id") == order_id), None)
            if not target_order:
                return {"success": False, "message": f"找不到訂單編號 #{order_id}。"}
        else:
            # 優先找最新一筆未完工/未取消的訂單
            target_order = next((o for o in orders if o.get("status") not in ("Completed", "Cancelled")), None)
            if not target_order:
                return {"success": False, "message": "您所有的訂單都已完工出貨或已取消，無可取消的訂單。"}

        target_id = target_order["id"]
        status = target_order.get("status", "Confirmed")

        if status == "Completed":
            return {
                "success": False,
                "message": f"訂單 #{target_id} 已經完工出貨，無法取消。如需退貨請輸入「真人」由客服專員為您處理！"
            }
        if status == "Cancelled":
            return {
                "success": False,
                "message": f"訂單 #{target_id} 已經是取消狀態。"
            }

        try:
            # 更新 Supabase line_orders 狀態為 Cancelled
            self.client.table("line_orders").update({"status": "Cancelled"}).eq("id", target_id).execute()
            print(f"✅ [Supabase] 訂單 #{target_id} 已取消")

            # 同步更新 SQLite
            try:
                import sqlite3
                sqlite_path = "/workspace/tutorials/Festo/shopping_website/database/order_management.db"
                if os.path.exists(sqlite_path):
                    conn = sqlite3.connect(sqlite_path)
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE order_list SET status = 'Cancelled' WHERE supabase_order_id = ? OR order_id = ?",
                        (target_id, f"LINE-{target_id:04d}")
                    )
                    conn.commit()
                    conn.close()
                    print(f"✅ [SQLite] 訂單 #{target_id} 本地狀態已同步取消")
            except Exception as se:
                print(f"⚠️ [CancelOrder] SQLite 同步取消失敗: {se}")

            return {
                "success": True,
                "order_id": target_id,
                "message": f"訂單 #{target_id} 已成功取消！"
            }
        except Exception as e:
            print(f"❌ [Supabase] 取消訂單失敗: {e}")
            return {"success": False, "message": f"取消訂單失敗: {e}"}

    def delete_order(self, client_id: str, order_id: int) -> dict:
        """
        永久刪除訂單（硬刪除）。
        會從 Supabase line_orders 中刪除該筆記錄。
        """
        orders = self.get_orders_by_client_id(client_id)
        if not orders:
            return {"success": False, "message": "目前查無您的訂單紀錄，無法刪除。"}

        target_order = next((o for o in orders if o.get("id") == order_id), None)
        if not target_order:
            return {"success": False, "message": f"找不到訂單編號 #{order_id}，或該訂單不屬於您。"}

        try:
            # 從 Supabase 刪除
            self.client.table("line_orders").delete().eq("id", order_id).execute()
            print(f"🗑️ [Supabase] 訂單 #{order_id} 已永久刪除")

            # 同步刪除 SQLite
            try:
                import sqlite3
                sqlite_path = "/workspace/tutorials/Festo/shopping_website/database/order_management.db"
                if os.path.exists(sqlite_path):
                    conn = sqlite3.connect(sqlite_path)
                    cur = conn.cursor()
                    cur.execute(
                        "DELETE FROM order_list WHERE supabase_order_id = ? OR order_id = ?",
                        (order_id, f"LINE-{order_id:04d}")
                    )
                    conn.commit()
                    conn.close()
                    print(f"🗑️ [SQLite] 訂單 #{order_id} 本地記錄已同步刪除")
            except Exception as se:
                print(f"⚠️ [DeleteOrder] SQLite 同步刪除失敗: {se}")

            return {
                "success": True,
                "order_id": order_id,
                "message": f"訂單 #{order_id} 已永久刪除！"
            }
        except Exception as e:
            print(f"❌ [Supabase] 刪除訂單失敗: {e}")
            return {"success": False, "message": f"刪除訂單失敗: {e}"}

    # ═══════════════════════════════════════════════════════════
    # 工具方法：格式化倉儲資訊（給 LLM 用）
    # ═══════════════════════════════════════════════════════════

    def format_inventory_for_llm(self) -> str:
        """
        產生一段結構化的庫存資訊文字，可注入 LLM 的 system prompt 中，
        讓 LLM 根據即時庫存回答客戶的問題。
        """
        warehouse = self.get_warehouse_inventory()
        products = self.get_all_products()

        lines = [
            "【Festo 產品庫存資訊】",
            "",
            "＝ ASRS 倉儲即時狀態 ＝",
            f"倉儲總位置：{warehouse['total_capacity']} 格",
            f"已佔用：{warehouse['total_occupied']} 格",
            f"空位：{warehouse['empty']['count']} 格",
            "",
        ]

        for p in products:
            name = p["name"]
            wh = warehouse.get(name, {})
            wh_count = wh.get("count", 0)
            # 以 ASRS 倉儲即時資料為唯一可信來源 (SSOT)
            total = wh_count
            price = p.get("base_price", 0)
            desc = p.get("description", "")

            lines.append(f"📦 {name}")
            lines.append(f"   說明：{desc}")
            lines.append(f"   單價：NT${price}")
            lines.append(f"   📊 即時庫存（可供訂購）：{total} 件")
            lines.append(f"      - ASRS 實體倉儲現貨：{wh_count} 件")
            if not self.is_mock and wh.get("positions"):
                lines.append(f"   倉位：{wh['positions']}")
            lines.append("")

        lines.append("【重要庫存原則】")
        lines.append("- 庫存以 ASRS 倉儲即時資料為準（單一可信來源）")
        lines.append("- 客戶訂購數量不得超過即時庫存。")

        return "\n".join(lines)


supabase_client = FestoSupabaseClient()
