import xmlrpc.client
import pandas as pd

# ---------------- CONFIGURATION ----------------
url = "http://localhost:1750/"
db = "leviotto_v17_production_05"
username = "admin"
password = "admin"
# company_id = 2
excel_path = "/home/sandip/Desktop/Projects/v17_Projects/v17_Leviotto/Contact_Cost_Price.xlsx"  # path to your Excel file
# ------------------------------------------------

# Load Excel
df = pd.read_excel(excel_path)

# Validate columns
if 'ID' not in df.columns or 'Cost' not in df.columns:
    raise ValueError("Excel must have columns: ID, standard_price")

# XML-RPC setup
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
if not uid:
    raise Exception("Login failed. Check credentials.")

models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

# Context for correct company
# context = {'company_id': company_id, 'force_company': company_id}

updated = 0
not_found = []

for _, row in df.iterrows():
    old_id = int(row['ID'])
    new_price = float(row['Cost']) if not pd.isna(row['Cost']) else None

    if new_price is None:
        continue

    # Search product by old_id
    product_ids = models.execute_kw(
        db, uid, password,
        'product.product', 'search',
        [[['old_id', '=', old_id]]],
        {'context': {'active_test': False}}
    )

    if not product_ids:
        not_found.append(old_id)
        continue

    # Update standard_price for all found products
    models.execute_kw(
        db, uid, password,
        'product.product', 'write',
        [product_ids, {'standard_price': new_price}]
    )

    updated += len(product_ids)

    print(f"\n✅ Updated {updated} products successfully.")
if not_found:
    print(f"⚠️ Not found ({len(not_found)}): {not_found[:10]}{' ...' if len(not_found) > 10 else ''}")

print("🎉 All updates completed successfully.")