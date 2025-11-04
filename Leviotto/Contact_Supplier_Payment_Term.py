import odoo
import odoo.tools.config as config
import odoo.service.server
from odoo import SUPERUSER_ID

config.parse_config(['-c', '/home/sandip/Desktop/Projects/v17_Projects/v17_Leviotto/conf/odoo.conf'])

old_db = 'leviotto_v17_upgraded'
new_db = 'leviotto_v17_production_03'
table_name = 'res.partner'

# Step 1: Get mapping of partner_id => supplier_payment_term_id from old DB
old_partner_supplier_term_map = {}

odoo.service.server.preload_registries([old_db])
old_registry = odoo.registry(old_db)
with old_registry.cursor() as cr:
    env = odoo.api.Environment(cr, SUPERUSER_ID, {})
    partners = env[table_name].search([])
    for partner in partners:
        if partner.property_supplier_payment_term_id:
            old_partner_supplier_term_map[partner.id] = partner.property_supplier_payment_term_id.id
            print(f"Old Partner ID {partner.id} -> Old Supplier Payment Term ID {partner.property_supplier_payment_term_id.id}")

# Step 2: Update new DB using old_id and mapped payment terms
odoo.service.server.preload_registries([new_db])
new_registry = odoo.registry(new_db)
with new_registry.cursor() as cr:
    env = odoo.api.Environment(cr, SUPERUSER_ID, {})

    for old_partner_id, old_payment_term_id in old_partner_supplier_term_map.items():
        new_partner = env[table_name].search([('old_id', '=', old_partner_id)], limit=1)
        if not new_partner:
            continue

        new_payment_term = env['account.payment.term'].search([('old_id', '=', old_payment_term_id)], limit=1)
        if not new_payment_term:
            print(f"⚠️ Supplier Payment Term with old_id {old_payment_term_id} not found in new DB for partner old_id {old_partner_id}")
            continue

        new_partner.write({'property_supplier_payment_term_id': new_payment_term.id})
        print(f"✅ Updated partner {new_partner.name} (old_id {old_partner_id}) with supplier payment term {new_payment_term.name}")