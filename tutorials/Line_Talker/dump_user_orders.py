import sys
sys.path.append("/workspace/tutorials/Line_Talker")
from app.supabase_client import supabase_client

client_id = "U2ced6c962379c726f1286b84f3f88bea"
orders = supabase_client.get_orders_by_client_id(client_id)
print(f"=== Found {len(orders)} orders for user {client_id} ===")
for o in orders:
    print("--- Order #", o["id"], "---")
    print("Created at:", o.get("created_at"))
    print("Status:", o.get("status"))
    print("Contact:", o.get("contact_name"), o.get("contact_phone"))
    print("Company:", o.get("company"))
    print("Address:", o.get("address"))
    print("Items:", o.get("items"))
    print("Total price:", o.get("total_price"))
