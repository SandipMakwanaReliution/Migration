import xmlrpc.client
import pandas as pd

# ---------------- CONFIGURATION ----------------
url = "http://localhost:1750/"
db = "v17_Leviotto_Production_01_11_25_02"
username = "admin"
password = "admin"
# company_id = 2
excel_path = "/home/sandip/Downloads/Contact_payment_Term.xlsx"  # path to your Excel file
dry_run = False  # change to True to simulate updates without saving
# ------------------------------------------------

# Load Excel
df = pd.read_excel(excel_path)

# Expected columns: ID, customer_term, vendor_term
expected_cols = {'ID', 'Customer Payment Terms', 'Vendor Payment Terms'}
if not expected_cols.issubset(df.columns):
    raise ValueError(f"Excel must have columns: {expected_cols}")

# XML-RPC setup
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
if not uid:
    raise Exception("Login failed. Check credentials.")

models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
# context = {'company_id': company_id, 'force_company': company_id}

updated = 0
not_found = []
term_not_found = set()

for _, row in df.iterrows():
    old_id = row['ID']
    cust_term_name = str(row['Customer Payment Terms']).strip() if not pd.isna(row['Customer Payment Terms']) else None
    vend_term_name = str(row['Vendor Payment Terms']).strip() if not pd.isna(row['Vendor Payment Terms']) else None

    # --- 1️⃣ Search partner by old_id ---
    partner_ids = models.execute_kw(
        db, uid, password,
        'res.partner', 'search',
        [[['old_id', '=', old_id]]],
    )

    if not partner_ids:
        print(f"⚠️ Partner not found for old_id={old_id}")
        not_found.append(old_id)
        continue

    update_vals = {}

    # --- 2️⃣ Handle Customer Payment Term ---
    if cust_term_name:
        term_ids = models.execute_kw(
            db, uid, password,
            'account.payment.term', 'search',
            [[['name', '=', cust_term_name]]],
        )
        if term_ids:
            update_vals['property_payment_term_id'] = term_ids[0]
        else:
            print(f"⚠️ Customer term '{cust_term_name}' not found for old_id={old_id}")
            term_not_found.add(cust_term_name)

    # --- 3️⃣ Handle Vendor Payment Term ---
    if vend_term_name:
        vend_term_ids = models.execute_kw(
            db, uid, password,
            'account.payment.term', 'search',
            [[['name', '=', vend_term_name]]],
        )
        if vend_term_ids:
            update_vals['property_supplier_payment_term_id'] = vend_term_ids[0]
        else:
            print(f"⚠️ Vendor term '{vend_term_name}' not found for old_id={old_id}")
            term_not_found.add(vend_term_name)

    # --- 4️⃣ Update record ---
    if update_vals:
        if dry_run:
            print(f"💡 [DRY RUN] Would update Partner {partner_ids} → {update_vals}")
        else:
            models.execute_kw(
                db, uid, password,
                'res.partner', 'write',
                [partner_ids, update_vals],
            )
            print(f"✅ Updated Partner old_id={old_id} → {update_vals}")
            updated += len(partner_ids)
    else:
        print(f"⚠️ No valid payment terms found to update for old_id={old_id}")

print("\n----------------------------")
print(f"✅ Total Partners Updated: {updated}")
print(f"⚠️ Partners Not Found: {len(not_found)}")
print(f"⚠️ Payment Terms Not Found: {len(term_not_found)}")
print("----------------------------")
