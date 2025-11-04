import xmlrpc.client
import pandas as pd

# --- Connection Info ---
url = "http://localhost:1750/"
db_name = "v17_Leviotto_Production_01_11_25_02"
username = "admin"
password = "admin"

# --- XMLRPC Authentication ---
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db_name, username, password, {})

# Database connection
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

# --- Read Excel file --- In Excel file add Contact Id and Fiscal Position Id
excel_path = "/home/sandip/Downloads/Contact_Fiscal_Position.xlsx"
df = pd.read_excel(excel_path)

# --- Loop through rows ---
for _, row in df.iterrows():
    old_id = int(row['id'])
    old_position_id = row['property_account_position_id']

    partner = models.execute_kw(db_name, uid, password, 'res.partner', 'search_read', [[('old_id', '=', old_id)]],
                                {'fields': ['id'], 'context': {'active_test': False}})

    if not partner:
        print(f"❌ Partner with old_id={partner} not found.")
        continue

    new_partner_id = partner[0]['id']

    if not pd.isna(old_position_id):
        new_fiscal_pos_id = models.execute_kw(db_name, uid, password, 'account.fiscal.position', 'search_read',
                                              [[('old_id', '=', int(old_position_id))]], {'fields': ['id'], 'limit': 1})

        if new_fiscal_pos_id:
            fiscal_position_id = new_fiscal_pos_id[0]['id']
        else:
            print(f"⚠️ Fiscal Position with old_id={old_id} not found. Skipping partner {old_id}.")
            continue
    else:
        fiscal_position_id = False

    models.execute_kw(db_name, uid, password, 'res.partner', 'write',
                      [[new_partner_id], {'property_account_position_id': fiscal_position_id}])
    print(f"✅ Updated Fiscal Position Partner Id : {new_partner_id} | Old Id : {old_id}")

print("🎉 All updates completed successfully.")