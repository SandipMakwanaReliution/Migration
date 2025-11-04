import xmlrpc.client
import pandas as pd

# ---------------- CONFIGURATION ----------------
url = "http://localhost:1750/"
db = "v17_Leviotto_Production_01_11_25_02"
username = "admin"
password = "admin"
# company_id = 2
excel_path = "/home/sandip/Downloads/Product_Cost_Sale_Price.xlsx"  # Path to your Excel file
# ------------------------------------------------

# Load Excel
df = pd.read_excel(excel_path)

# Validate required columns
required_cols = ['ID']
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise ValueError(f"Excel must have at least the following column(s): {missing_cols}")

if 'Cost' not in df.columns and 'SalesPrice' not in df.columns:
    raise ValueError("Excel must have at least one of these columns: 'Cost' or 'SalesPrice'")

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
    if pd.isna(row['ID']):
        print("⚠️ Skipping row with missing ID")
        continue

    old_id = int(row['ID'])

    # Extract values from Excel (handle missing columns safely)
    cost_price = float(row['Cost']) if 'Cost' in df.columns and not pd.isna(row['Cost']) else None
    sale_price = float(row['SalesPrice']) if 'SalesPrice' in df.columns and not pd.isna(row['SalesPrice']) else None

    # Skip if neither price is provided
    if cost_price is None and sale_price is None:
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

    # Prepare update values
    vals = {}
    if cost_price is not None:
        vals['standard_price'] = cost_price
    if sale_price is not None:
        vals['lst_price'] = sale_price

    # Update product(s)
    models.execute_kw(
        db, uid, password,
        'product.product', 'write',
        [product_ids, vals]
    )

    updated += len(product_ids)
    print(f"✅ Updated old_id={old_id} → {vals}")

# Final summary
print(f"\n🎯 Total updated products: {updated}")
if not_found:
    print(f"⚠️ Not found ({len(not_found)}): {not_found[:10]}{' ...' if len(not_found) > 10 else ''}")

print("🎉 All updates completed successfully.")
