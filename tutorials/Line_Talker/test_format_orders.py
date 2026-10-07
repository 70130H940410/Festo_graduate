import sys
sys.path.append("/workspace/tutorials/Line_Talker")
from app.supabase_client import supabase_client

orders = supabase_client.get_orders_by_client_id("U2ced6c962379c726f1286b84f3f88bea")
formatted = supabase_client.format_orders_for_user(orders)
print(formatted)
