import xmlrpc.client

old_odoo_url = "http://localhost:1750"

old_db_name = "leviotto_v17_upgraded"
username = "admin"
password = "admin"

new_db_name = "leviotto_v17_production_03"
table_name = "res.partner"

# XML-RPC setup
common = xmlrpc.client.ServerProxy(f"{old_odoo_url}/xmlrpc/2/common")
models = xmlrpc.client.ServerProxy(f"{old_odoo_url}/xmlrpc/2/object")

# Authenticate
old_uid = common.authenticate(old_db_name, username, password, {})
new_uid = common.authenticate(new_db_name, username, password, {})

old_record_ids = models.execute_kw(old_db_name, old_uid, password, table_name, 'search', [[('property_payment_term_id', '!=', False)]], {'context': {'active_test': False}})
old_record_data = models.execute_kw(old_db_name, old_uid, password, 'res.partner', 'read', [old_record_ids], {'fields': ['id', 'property_payment_term_id']})

result = f"Fetched partners from old DB: {old_record_data}"
print(result)

for rec in old_record_data:
    old_rec_id = rec['id']
    old_payment_term_id = rec['property_payment_term_id'][0]  # many2one field (ID only)

    new_record_find = models.execute_kw(new_db_name, new_uid, password, table_name, 'search', [[('old_id', '=', old_rec_id)]], {'context': {'active_test': False}})

    if not new_record_find:
        result = f"⚠️ Partner with old_id {old_rec_id} not found in new DB."
        continue

    # Find payment term in NEW DB by old_id
    new_payment_term_ids = models.execute_kw(new_db_name, new_uid, password, 'account.payment.term', 'search', [[('old_id', '=', old_payment_term_id)]])

    if not new_payment_term_ids:
        result = f"⚠️ Payment Term with old_id {old_payment_term_id} not found in new DB for partner old_id {old_rec_id}"
        print(result)
        continue

    # Update partner's payment term
    models.execute_kw(new_db_name, new_uid, password, table_name, 'write', [new_record_find, {'property_payment_term_id': new_payment_term_ids[0]}])

    result = f"✅ Updated partner old_id {old_rec_id} with new payment term old_id {old_payment_term_id}"
    print(result)