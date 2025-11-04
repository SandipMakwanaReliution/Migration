import odoo
import odoo.tools.config as config
import odoo.service.server
from odoo import SUPERUSER_ID

config.parse_config(['-c', '/home/sandip/Desktop/Projects/v17_Projects/v17_Leviotto/conf/odoo.conf'])

old_db = 'leviotto_v17_upgraded'
new_db = 'leviotto_v17_production_03'
table_name = 'res.partner'

# Step 1: Get mapping of partner_id => receivable_account_id from old DB
old_partner_account_map = {}

odoo.service.server.preload_registries([old_db])
old_registry = odoo.registry(old_db)
with old_registry.cursor() as cr :
    env = odoo.api.Environment(cr, SUPERUSER_ID, {})
    partners = env[table_name].search([])
    for partner in partners :
        if partner.property_account_receivable_id :
            old_partner_account_map[partner.id] = partner.property_account_receivable_id.code
            # Optional print
            print(f"Old Partner ID {partner.id} -> Old Receivable Account Code {partner.property_account_receivable_id.code}")

# Step 2: Update new DB based on old_id match and mapped account
odoo.service.server.preload_registries([new_db])
new_registry = odoo.registry(new_db)
with new_registry.cursor() as cr :
    env = odoo.api.Environment(cr, SUPERUSER_ID, {})

    for old_partner_id, old_account_id in old_partner_account_map.items() :
        # Find new partner with old_id
        new_partner = env[table_name].search([('old_id', '=', old_partner_id)], limit=1)
        if not new_partner :
            continue

        # Find new account with old_id
        new_account = env['account.account'].search([('code', '=', old_account_id)], limit=1)
        if not new_account :
            print(f"⚠️ Account with old_id {old_account_id} not found in new DB for partner old_id {old_partner_id}")
            continue

        # print(new_account.name)

        # Update partner's receivable account
        new_partner.write({'property_account_receivable_id' : new_account.id})
        print(
            f"✅ Updated partner {new_partner.name} (old_id {old_partner_id}) with new receivable account {new_account.code}")