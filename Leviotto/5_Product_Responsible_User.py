import xmlrpc.client
import pandas as pd
import math

# --- Connection Info ---
url = "http://localhost:1750"
db_name = "v17_Leviotto_Production_01_11_25_02"
username = "admin"
password = "admin"

# --- XMLRPC Authentication ---
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db_name, username, password, {})

if not uid:
    raise Exception("❌ Authentication failed. Check username/password or server connection.")

# --- Object Proxy ---
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

# --- Read Excel File ---
excel_path = "/home/sandip/Downloads/Product_Responsible_User.xlsx"
df = pd.read_excel(excel_path)

# --- Loop through each row in Excel ---
for _, row in df.iterrows():
    old_product_id = int(row['id'])
    old_responsible_id = row.get('responsible_id')

    # --- Find the new Product in current database ---
    product = models.execute_kw(
        db_name, uid, password,
        'product.template', 'search_read',
        [[('old_id', '=', old_product_id)]],
        {'fields': ['id', ], 'context': {'active_test': False}}
    )

    if not product:
        print(f"❌ Product with old_id={old_product_id} not found.")
        continue

    new_product_id = product[0]['id']

    # --- Handle responsible_id ---
    if old_responsible_id is None or (isinstance(old_responsible_id, float) and math.isnan(old_responsible_id)):
        responsible_id = False
    else:
        user_record = models.execute_kw(
            db_name, uid, password,
            'res.users', 'search_read',
            [[('old_id', '=', int(old_responsible_id))]],
            {'fields': ['id'], 'limit': 1}
        )
        responsible_id = user_record[0]['id'] if user_record else False

    # --- Update Product Responsible ---
    models.execute_kw(
        db_name, uid, password,
        'product.template', 'write',
        [[new_product_id], {'responsible_id': responsible_id}]
    )

    print(f"✅ Updated Product Old ID: {old_product_id}) with Responsible User Old ID: {old_responsible_id}")

print("🎉 All product responsible updates completed successfully.")