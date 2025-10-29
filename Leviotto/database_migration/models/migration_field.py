import odoo
from odoo import models, api, fields, SUPERUSER_ID
import psycopg2
import logging
import xmlrpc.client

_logger = logging.getLogger(__name__)


class MigrationField(models.Model):
    _name = "migration.field"
    _description = "Migrate the fields from old to current database using SQL queries."

    table_id = fields.Many2one("migration.table", "Migration Table")
    old_field_name = fields.Char("Old Field Name")
    current_field_name = fields.Many2one("ir.model.fields", "Current Field Name")
    relational_field_name = fields.Char("Relational Field Names")
    old_data_type = fields.Char("Old Data Type")
    current_data_type = fields.Char("Current Data Type")
    matched = fields.Boolean("Matched", default=False)
    relation = fields.Char(string="Related Model")
    not_store = fields.Boolean("Not Stored", default=False)

    def action_migrate_relational_fields(self):
        """Migrate many2many, one2many, and binary fields using XML-RPC."""

        try:
            connection = self.table_id.connection_id
            url = f"{connection.old_odoo_url}"
            old_db = connection.old_db_name
            username = connection.old_username
            password = connection.old_password

            common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
            old_uid = common.authenticate(old_db, username, password, {})
            if not old_uid:
                raise ValueError("Failed to authenticate to the old database.")

            # New database connection
            models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

            selected_field_ids = self.env.context.get("active_ids", [])
            selected_fields = self.browse(selected_field_ids)

            if not selected_fields:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "No Fields Selected",
                        "message": "Please select fields to migrate.",
                        "type": "warning",
                        "sticky": False,
                    },
                }

            for field in selected_fields:
                old_table_name = self.table_id.old_db_table
                old_table_cus_name = old_table_name.replace("_", ".")
                current_model_name = self.table_id.current_db_table.model
                old_field_name = field.old_field_name
                current_field_name = field.current_field_name.name
                related_model = field.relation

                # Fetch records from the old database
                old_records = models.execute_kw(
                    old_db,
                    old_uid,
                    password,
                    old_table_cus_name,
                    "search_read",
                    [[]],
                    {"fields": ["id", old_field_name]},
                )

                if not isinstance(old_records, list):
                    continue

                # Handle many2many and one2many fields
                if field.current_data_type in ["many2many", "one2many"]:
                    for old_record in old_records:
                        old_id = old_record["id"]
                        related_ids = old_record.get(old_field_name, [])

                        if not isinstance(related_ids, list):
                            continue

                        related_ids = [
                            rid for rid in related_ids if isinstance(rid, int)
                        ]

                        if not related_ids:
                            continue

                        current_record = self.env[current_model_name].search(
                            [("old_id", "=", old_id)], limit=1
                        )

                        if current_record:
                            new_related_ids = []

                            for old_related_id in related_ids:
                                if hasattr(self.env[related_model], "active"):
                                    mapped_record = self.env[related_model].search(
                                        [
                                            ("old_id", "=", old_related_id),
                                            "|",
                                            ("active", "=", True),
                                            ("active", "=", False),
                                        ],
                                        limit=1,
                                    )
                                else:
                                    mapped_record = self.env[related_model].search(
                                        [("old_id", "=", old_related_id)], limit=1
                                    )

                                if mapped_record:
                                    new_related_ids.append(mapped_record.id)

                            current_record.write(
                                {current_field_name: [(6, 0, new_related_ids)]}
                            )
                            self.env.cr.commit()
                            _logger.info("Record Written Successfully...")

                # Handle binary fields (e.g., images)
                elif field.current_data_type == "binary":
                    for old_record in old_records:
                        old_id = old_record["id"]
                        binary_data = old_record.get(old_field_name)

                        if not binary_data:
                            continue

                        # Find the corresponding record in the new database
                        current_record = self.env[current_model_name].search(
                            [("old_id", "=", old_id)], limit=1
                        )

                        if current_record:
                            # Update the binary field with the fetched data
                            current_record.write({current_field_name: binary_data})

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Fields Migration Successful",
                    "message": f"Fields migrated into {current_model_name} successfully!",
                    "type": "success",
                    "sticky": False,
                },
            }

        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Migration Error",
                    "message": f"Error during migration: {str(e)}",
                    "type": "danger",
                    "sticky": False,
                },
            }

    def get_related_fields(self, model_name):
        model = self.env[model_name]
        related_fields = {}

        # Fetch all relational fields (Many2one)
        for field in model._fields.values():
            if isinstance(field, fields.Many2one):
                related_fields[field.name] = field.comodel_name
        return related_fields

    def action_migrate(self):
        conn_old = None
        cursor_old = None
        conn_current = None
        cursor_current = None

        try:
            old_table_name = self.table_id.old_db_table
            current_table_name = self.table_id.current_db_table

            if old_table_name in (
                "stock_quant",
                "stock_picking",
                "purchase_order_line",
                "purchase_order",
                "sale_order_line",
                "payment_transaction",
                "pos_order_line",
                "stock_move",
                "stock_move_line",
                "product_product",
                "account_move_line",
                "account_move",
                "pos_payment",
                "pos_config",
                "pos_session",
                "res_users",
                "account_analytic_line",
                "hr_leave",
                "hr_leave_type",
                "sale_order",
                # "hr_expense_sheet",
                "res_partner",
                # "account_account",
                "account_full_reconcile",
                "account_payment",
                # "pdc_account_payment",
                # "account_move",
                # "account_move_line"
            ):
                connection = self.table_id.connection_id
                conn_old = psycopg2.connect(
                    dbname=connection.old_db_name,
                    user=connection.pg_username,
                    password=connection.pg_password,
                    host=connection.pg_host,
                )
                cursor_old = conn_old.cursor()

                # Connect to the current Odoo database
                conn_current = psycopg2.connect(
                    dbname=self.env.cr.dbname,
                    user="odoo",
                    password="odoo",
                    host="localhost",
                )
                cursor_current = conn_current.cursor()

                # Fetching only the selected fields (marked in the list view)
                selected_field_ids = self.env.context.get("active_ids", [])
                selected_fields = self.browse(selected_field_ids)

                if not selected_fields:
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": "No Fields Selected",
                            "message": "Please select fields to migrate.",
                            "type": "warning",
                            "sticky": False,
                        },
                    }

                # Getting the selected field names
                old_field_names = ", ".join(
                    [field.old_field_name for field in selected_fields]
                )
                current_field_names = [
                    field.current_field_name.name for field in selected_fields
                ]

                # Handling the 'id' field separately
                old_field_list = old_field_names.split(", ")
                old_field_list = [
                    "id AS old_id" if f == "id" else f for f in old_field_list
                ]
                old_field_names = ", ".join(old_field_list)
                current_field_names = [
                    "old_id" if f == "id" else f for f in current_field_names
                ]

                related_field_mappings = {}

                current_table_model = current_table_name.model
                # models_to_check = [
                #    'pos.order.line', 'hr.employee', 'res.partner', 'project.project', 'project.task', 'res.users',
                #    'hr.job', 'resource.resource', 'hr.leave.type', 'hr.leave', 'res.country', 'product.category',
                #    'product.product', 'uom.category', 'uom.uom', 'product.pricelist', 'project.task.type', 'product.template', 'stock.move',
                #    'sale.order.template', 'sale.order', 'purchase.order.line', 'pos.config', 'pos.session', 'pos.payment', 'account.move', 'stock.move.line', 'account.move.line']

                models_to_check = [current_table_model]

                for model_name in models_to_check:
                    related_field_mappings.update(self.get_related_fields(model_name))

                related_mappings = {}
                for field_name, model_name in related_field_mappings.items():
                    domain = []
                    if model_name == "hr.employee":
                        domain = ["|", ("active", "=", False), ("active", "=", True)]
                    if model_name in (
                        "res.partner",
                        "res.users",
                        "resource.resource",
                        "product.template",
                        "product.product",
                        "product.pricelist",
                        "stock.location",
                    ):
                        domain = ["|", ("active", "=", False), ("active", "=", True)]
                    try:
                        if model_name in ("res.currency"):
                            mapped_values = (
                                # self.env[model_name]
                                # .search(domain)
                                # .mapped(lambda r: (r.name, r.name))
                                self.env[model_name]
                                .search(domain)
                                .mapped(lambda r: (r.old_id, r.id))
                            )
                        else:
                            mapped_values = (
                                self.env[model_name]
                                .search(domain)
                                .mapped(lambda r: (r.old_id, r.id))
                            )

                        if not mapped_values:
                            continue

                        related_mappings[field_name] = dict(mapped_values)

                    except Exception as e:
                        _logger.error(
                            f"Error processing model {model_name} for field {field_name}: {str(e)}"
                        )
                        continue

                if old_table_name == 'res_users':
                    cursor_old.execute(f"SELECT {old_field_names} FROM {old_table_name} WHERE company_id = 2 or id In (6, 46, 52);")
                    rows = cursor_old.fetchall()
                elif old_table_name == 'product_product':
                    prefixed_field_names = ", ".join([f"pp.{f.strip()}" for f in old_field_names.split(",")])
                    cursor_old.execute(f"""
                        SELECT {prefixed_field_names}
                        FROM {old_table_name} pp
                        JOIN product_template pt ON pp.product_tmpl_id = pt.id
                        WHERE pt.company_id = 2 OR pt.company_id IS NULL;
                    """)
                    rows = cursor_old.fetchall()
                elif old_table_name in ['stock_quant', 'account_account', 'account_analytic_line', 'account_move',
                                        'account_move_line']:
                    cursor_old.execute(f"SELECT {old_field_names} FROM {old_table_name} WHERE company_id = 2;")
                    rows = cursor_old.fetchall()
                elif old_table_name == 'account_payment':
                    old_move_ids = self.env['account.move'].search([]).mapped('old_id') # already filtered by company earlier
                    if old_move_ids:
                        move_ids_tuple = tuple(old_move_ids)
                        query = f"SELECT {old_field_names} FROM {old_table_name} WHERE move_id IN %s"
                        cursor_old.execute(query, (move_ids_tuple,))
                        rows = cursor_old.fetchall()
                    else:
                        rows = []
                else:
                    cursor_old.execute(f"SELECT {old_field_names} FROM {old_table_name}")
                    rows = cursor_old.fetchall()

                for row in rows:
                    record_data = {}

                    for idx, field_name in enumerate(current_field_names):
                        value = row[idx] if row[idx] not in [None] else None
                        record_data[field_name] = value

                    # Handle Many2one fields, mapping old_id to the actual id in the current database
                    for field_name, mapping in related_mappings.items():
                        if (
                            field_name in record_data
                            and record_data[field_name] in mapping
                        ):
                            # Replace old_id with the corresponding current id
                            record_data[field_name] = mapping[record_data[field_name]]

                    # Skip if login is empty or in skip_logins
                    skip_logins = ["default", "__system__", "portaltemplate", "public"]
                    if "login" in record_data and (
                        not record_data["login"] or record_data["login"] in skip_logins
                    ):
                        continue

                    # current_table_model = current_table_name.model
                    current_table = current_table_model.replace(".", "_")

                    # Additional check for duplicates specifically for product_product
                    if (
                        current_table == "product_product"
                        and "product_tmpl_id" in record_data
                        and "combination_indices" in record_data
                    ):
                        original_combination_indices = record_data[
                            "combination_indices"
                        ]
                        duplicate_found = True
                        suffix_counter = 1

                        while duplicate_found:
                            cursor_current.execute(
                                f"SELECT id FROM {current_table} WHERE product_tmpl_id = %s AND combination_indices = %s",
                                (
                                    record_data["product_tmpl_id"],
                                    record_data["combination_indices"],
                                ),
                            )
                            duplicate_record = cursor_current.fetchone()

                            if duplicate_record:
                                # Record with the same product_tmpl_id and combination_indices exists, add suffix and check again
                                _logger.info(
                                    f"Duplicate found for product_tmpl_id: {record_data['product_tmpl_id']} and combination_indices: {record_data['combination_indices']}. Trying a new suffix."
                                )
                                # Append or increment the suffix
                                record_data[
                                    "combination_indices"
                                ] = f"{original_combination_indices}_{suffix_counter}"
                                suffix_counter += 1
                            else:
                                # No duplicate found, we can insert this record
                                duplicate_found = False

                    # if current_table == 'account_move' and 'name' in record_data and record_data['name']:
                    #     original_name = record_data['name']
                    #     duplicate_found = True
                    #     suffix_counter = 1
                    #
                    #     while duplicate_found:
                    #         cursor_current.execute(
                    #             f"SELECT id FROM account_move WHERE name = %s",
                    #            (record_data['name'],)
                    #         )
                    #         duplicate_record = cursor_current.fetchone()
                    #
                    #         if duplicate_record:
                    #            _logger.info(
                    #                f"Duplicate found in account_move for name: {record_data['name']}. Trying a new suffix."
                    #            )
                    #            record_data['name'] = f"{original_name}_dup{suffix_counter}"
                    #            suffix_counter += 1
                    #         else:
                    #            duplicate_found = False

                    if "default_code" in record_data and record_data["default_code"]:
                        cursor_current.execute(
                            f"SELECT id FROM {current_table} WHERE default_code = %s",
                            (record_data["default_code"],),
                        )
                        existing_variant = cursor_current.fetchone()
                    else:
                        existing_variant = None

                    if existing_variant:
                        update_fields = ", ".join(
                            [
                                f"{field} = %s"
                                for field in current_field_names
                                if field != "old_id"
                            ]
                        )
                        update_values = [
                            record_data[field]
                            for field in current_field_names
                            if field != "old_id"
                        ]
                        sql_update_query = f"UPDATE {current_table} SET {update_fields} WHERE default_code = %s"
                        cursor_current.execute(
                            sql_update_query,
                            (*update_values, record_data["default_code"]),
                        )
                        _logger.info(
                            f"Updated variant with default_code: {record_data['default_code']}"
                        )
                        conn_current.commit()

                    else:
                        if "old_id" in record_data and record_data["old_id"]:
                            cursor_current.execute(
                                f"SELECT id FROM {current_table} WHERE old_id = %s",
                                (record_data["old_id"],),
                            )
                            existing_record = cursor_current.fetchone()
                        else:
                            existing_record = None

                        if existing_record:
                            # _logger.info("Skipping the record...")
                            # continue
                            update_fields = ", ".join(
                                [
                                    f"{field} = %s"
                                    for field in current_field_names
                                    if field != "old_id"
                                ]
                            )
                            update_values = [
                                record_data[field]
                                for field in current_field_names
                                if field != "old_id"
                            ]
                            sql_update_query = f"UPDATE {current_table} SET {update_fields} WHERE old_id = %s"
                            cursor_current.execute(
                                sql_update_query,
                                (*update_values, record_data["old_id"]),
                            )
                            _logger.info(
                                f"Updated record with old_id: {record_data['old_id']}"
                            )
                            conn_current.commit()

                        else:
                            insert_fields = ", ".join(current_field_names)
                            insert_placeholders = ", ".join(
                                ["%s"] * len(current_field_names)
                            )
                            sql_insert_query = f"INSERT INTO {current_table} ({insert_fields}) VALUES ({insert_placeholders})"
                            insert_values = [
                                record_data[field] for field in current_field_names
                            ]
                            cursor_current.execute(sql_insert_query, insert_values)
                            _logger.info(f"Inserted new record: {record_data}")
                            conn_current.commit()

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Migration Successful",
                        "message": f"Migrated records into {current_table_name} successfully!",
                        "type": "success",
                        "sticky": False,
                    },
                }

            else:
                connection = self.table_id.connection_id
                conn = psycopg2.connect(
                    dbname=connection.old_db_name,
                    user=connection.pg_username,
                    password=connection.pg_password,
                    host=connection.pg_host,
                )
                cursor = conn.cursor()

                # Fetching only the selected fields (marked in the list view)
                selected_field_ids = self.env.context.get("active_ids", [])
                selected_fields = self.browse(selected_field_ids)

                # If no fields are selected, show a warning
                if not selected_fields:
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": "No Fields Selected",
                            "message": "Please select fields to migrate.",
                            "type": "warning",
                            "sticky": False,
                        },
                    }

                # Getting the selected field names
                old_field_names = ", ".join(
                    [field.old_field_name for field in selected_fields]
                )
                current_field_names = [
                    field.current_field_name.name for field in selected_fields
                ]

                # Handling the 'id' field separately
                old_field_list = old_field_names.split(", ")
                old_field_list = [
                    "id AS old_id" if f == "id" else f for f in old_field_list
                ]
                old_field_names = ", ".join(old_field_list)
                current_field_names = [
                    "old_id" if f == "id" else f for f in current_field_names
                ]

                related_field_mappings = {}

                current_table = current_table_name.model

                models_to_check = [current_table]

                for model_name in models_to_check:
                    related_field_mappings.update(self.get_related_fields(model_name))

                related_mappings = {}
                for field_name, model_name in related_field_mappings.items():
                    domain = []
                    if model_name == "hr.employee":
                        domain = ["|", ("active", "=", False), ("active", "=", True)]
                    if model_name in (
                        "res.partner",
                        "res.users",
                        "resource.resource",
                        "product.product",
                        "product.template",
                        "stock.location",
                        "product.pricelist",
                    ):
                        domain = ["|", ("active", "=", False), ("active", "=", True)]
                    try:
                        if model_name in ("res.country"):
                            mapped_values = (
                                self.env[model_name]
                                .search(domain)
                                .mapped(lambda r: (r.code, r.code))
                            )
                        else:
                            mapped_values = (
                                self.env[model_name]
                                .search(domain)
                                .mapped(lambda r: (r.old_id, r.id))
                            )

                        if not mapped_values:
                            continue

                        related_mappings[field_name] = dict(mapped_values)

                    except Exception as e:
                        _logger.error(
                            f"Error processing model {model_name} for field {field_name}: {str(e)}"
                        )
                        continue

                # Fetching the old table data for the selected fields
                BATCH_SIZE = 2500  # Define the batch size, you can adjust this value based on your needs


                if old_table_name == 'res_company':
                    cursor.execute(f"SELECT {old_field_names} FROM {old_table_name} WHERE id = 2;")
                    rows = cursor.fetchall()
                elif old_table_name == 'hr_employee':
                    cursor.execute(f"SELECT {old_field_names} FROM {old_table_name} WHERE company_id = 2 OR id IN (15, 36, 40);")
                    rows = cursor.fetchall()
                elif old_table_name == 'product_template':
                    cursor.execute(f"SELECT {old_field_names} FROM {old_table_name} WHERE company_id = 2 OR company_id Is Null;")
                    rows = cursor.fetchall()
                elif old_table_name == 'product_template_attribute_line':
                    template_records = self.env['product.template'].search([('old_id', '!=', False)])
                    old_template_ids = [tmpl.old_id for tmpl in template_records if tmpl.old_id]
                    id_list_str = ", ".join(map(str, old_template_ids))
                    cursor.execute(f"SELECT {old_field_names} FROM {old_table_name} WHERE product_tmpl_id In ({id_list_str});")
                    rows = cursor.fetchall()
                elif old_table_name == 'product_template_attribute_value':
                    attribute_lines = self.env['product.template.attribute.line'].search([('old_id','!=', False)])
                    old_attribute_lines_ids = [atr_val.old_id for atr_val in attribute_lines if atr_val.old_id]
                    attribute_lines_id_list_str = ", ".join(map(str, old_attribute_lines_ids))
                    cursor.execute(
                        f"SELECT {old_field_names} FROM {old_table_name} WHERE attribute_line_id In ({attribute_lines_id_list_str});")
                    rows = cursor.fetchall()
                elif old_table_name == 'product_supplierinfo':
                    template_records = self.env['product.template'].search([('old_id', '!=', False)])
                    old_template_ids = [tmpl.old_id for tmpl in template_records if tmpl.old_id]
                    id_list_str = ", ".join(map(str, old_template_ids))
                    cursor.execute(f"SELECT {old_field_names} FROM {old_table_name} WHERE product_tmpl_id In ({id_list_str});")
                    rows = cursor.fetchall()
                elif old_table_name in ['account_account', 'account_tax', 'account_tax_repartition_line', 'account_journal',
                                        'account_fiscal_position', 'account_fiscal_position_tax', 'account_tax_group',
                                        'account_analytic_account', 'hr_expense', 'hr_expense_sheet', 'account_partial_reconcile']:
                    cursor.execute(f"SELECT {old_field_names} FROM {old_table_name} WHERE company_id = 2;")
                    rows = cursor.fetchall()
                elif old_table_name == 'pdc_account_payment':
                    old_journal_ids = self.env['account.journal'].search([]).mapped('old_id')  # already filtered by company earlier
                    if old_journal_ids:
                        journal_ids_tuple = tuple(old_journal_ids)
                        query = f"SELECT {old_field_names} FROM {old_table_name} WHERE journal_id IN %s"
                        cursor.execute(query, (journal_ids_tuple,))
                        rows = cursor.fetchall()
                    else:
                        rows = []
                else:
                    cursor.execute(f"SELECT {old_field_names} FROM {old_table_name};")
                    rows = cursor.fetchall()

                # Divide the rows into batches
                total_rows = len(rows)
                batches = [
                    rows[i : i + BATCH_SIZE] for i in range(0, total_rows, BATCH_SIZE)
                ]

                for batch_index, batch in enumerate(batches):
                    _logger.info(
                        f"Processing batch {batch_index + 1}/{len(batches)} with {len(batch)} records"
                    )
                    records_to_create = []

                    for row in batch:
                        record_data = {}
                        skip_record = False

                        # this for loop create record data = { fields : value, ...}
                        for idx, field_name in enumerate(current_field_names):
                            value = row[idx] if row[idx] not in [None, False] else None

                            if field_name == "name" and not value:
                                value = "Unknown"

                            skip_logins = [
                                "default",
                                "__system__",
                                "portaltemplate",
                                "public",
                            ]
                            if field_name == "login":
                                if not value or value in skip_logins:
                                    continue

                            field_obj = self.env[current_table]._fields.get(field_name)
                            if field_obj and field_obj.type == "selection":
                                if callable(field_obj.selection):
                                    valid_selection_values = [
                                        val[0] for val in field_obj.selection(self)
                                    ]
                                else:
                                    valid_selection_values = [
                                        val[0] for val in field_obj.selection
                                    ]

                                if value not in valid_selection_values:
                                    skip_record = True
                                    _logger.info(
                                        f"Skipping record with invalid selection value '{value}' for field '{field_name}'"
                                    )
                                    break

                            if (
                                field_name in related_mappings
                                and value in related_mappings[field_name]
                            ):
                                record_data[field_name] = related_mappings[field_name][
                                    value
                                ]
                            else:
                                record_data[field_name] = value

                        if skip_record:
                            continue

                        old_id_value = record_data.get("old_id")
                        default_code_value = record_data.get("default_code")
                        name_value = record_data.get("name")

                        if default_code_value:
                            search_domain = [("default_code", "=", default_code_value)]
                            if "active" in self.env[current_table]._fields:
                                search_domain = [
                                    "|",
                                    ("active", "=", True),
                                    ("active", "=", False),
                                ] + search_domain
                            existing_record = self.env[current_table].search(
                                search_domain, limit=1
                            )

                            if existing_record:
                                keys_to_exclude = ["default_code"]
                                record_data_to_update = {
                                    key: value
                                    for key, value in record_data.items()
                                    if key not in keys_to_exclude
                                }
                                try:
                                    existing_record.write(record_data_to_update)
                                    self.env.cr.commit()
                                    _logger.info(
                                        f"Record with default_code {default_code_value} updated successfully."
                                    )
                                except Exception as update_error:
                                    _logger.error(
                                        f"Error updating record with default_code {default_code_value}: {update_error}"
                                    )
                            else:
                                if old_id_value:
                                    search_domain = [("old_id", "=", old_id_value)]
                                    if "active" in self.env[current_table]._fields:
                                        search_domain = [
                                            "|",
                                            ("active", "=", True),
                                            ("active", "=", False),
                                        ] + search_domain

                                    existing_record = self.env[current_table].search(
                                        search_domain, limit=1
                                    )

                                    if existing_record:
                                        record_data_to_update = {
                                            key: value
                                            for key, value in record_data.items()
                                            if key not in ["old_id", "default_code"]
                                        }
                                        try:
                                            existing_record.write(record_data_to_update)
                                            self.env.cr.commit()
                                            _logger.info(
                                                f"Record with old_id {old_id_value} updated successfully."
                                            )
                                        except Exception as update_error:
                                            _logger.error(
                                                f"Error updating record with old_id {old_id_value}: {update_error}"
                                            )
                                    else:
                                        try:
                                            self.env[current_table].sudo().create(
                                                record_data
                                            )
                                            self.env.cr.commit()
                                            _logger.info(
                                                f"New record with old_id {old_id_value} created successfully."
                                            )
                                        except Exception as create_error:
                                            _logger.error(
                                                f"Error creating new record with old_id {old_id_value}: {create_error}"
                                            )

                        elif old_id_value:
                            search_domain = [("old_id", "=", old_id_value)]
                            if "active" in self.env[current_table]._fields:
                                search_domain = [
                                    "|",
                                    ("active", "=", True),
                                    ("active", "=", False),
                                ] + search_domain
                            existing_record = self.env[current_table].search(
                                search_domain, limit=1
                            )

                            if existing_record:
                                record_data_to_update = {
                                    key: value
                                    for key, value in record_data.items()
                                    if key not in ["old_id", "default_code"]
                                }
                                try:
                                    if current_table == "product.category" and "property_valuation" not in record_data_to_update:
                                        record_data_to_update["property_valuation"] = "real_time"

                                    if current_table == "product.category" and "property_cost_method" not in record_data_to_update:
                                        record_data_to_update["property_cost_method"] = "average"

                                    existing_record.write(record_data_to_update)
                                    self.env.cr.commit()
                                    _logger.info(
                                        f"Record with old_id {old_id_value} updated successfully."
                                    )
                                except Exception as update_error:
                                    _logger.error(
                                        f"Error updating record with old_id {old_id_value}: {update_error}"
                                    )
                            else:
                                try:
                                    if current_table == "product.category" and "property_valuation" not in record_data:
                                        record_data["property_valuation"] = "real_time"

                                    if current_table == "product.category" and "property_cost_method" not in record_data:
                                        record_data["property_cost_method"] = "average"

                                    if current_table == "account.journal" and old_id_value in [15, 16]:
                                        for key, value in record_data.items():
                                            if isinstance(value, dict):
                                                record_data[key] = value.get("en_US") or next(iter(value.values()),
                                                                                              None)
                                                _logger.warning(
                                                    f"Converted dict to string for field '{key}' (old_id={old_id_value})"
                                                )

                                    self.env[current_table].sudo().create(record_data)
                                    self.env.cr.commit()
                                    _logger.info(
                                        f"New record with old_id======___________========----- {old_id_value} created successfully."
                                    )
                                except Exception as create_error:
                                    _logger.error(
                                        f"Error creating new record with old_id {old_id_value}: {create_error}"
                                    )
                        else:
                            try:
                                self.env[current_table].sudo().create(record_data)
                                self.env.cr.commit()
                                _logger.info(
                                    f"New record created successfully: {record_data}"
                                )
                            except Exception as create_error:
                                _logger.error(
                                    f"Error creating new record: {create_error}"
                                )

                        _logger.info(
                            f"Batch {batch_index + 1}/{len(batches)} processed successfully"
                        )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Migration Successful",
                        "message": f"Migrated records for {current_table} successfully!",
                        "type": "success",
                        "sticky": False,
                    },
                }

        except psycopg2.DatabaseError as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Database Error",
                    "message": f"Error during migration: {str(e)}",
                    "type": "danger",
                    "sticky": False,
                },
            }

        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Migration Failed",
                    "message": f"Unexpected error: {str(e)}",
                    "type": "danger",
                    "sticky": False,
                },
            }

        finally:
            # Close cursors and connections if they were created
            if cursor_old:
                cursor_old.close()
            if conn_old:
                conn_old.close()
            if cursor_current:
                cursor_current.close()
            if conn_current:
                conn_current.close()

    def action_migrate_for_related_tables(self):
        conn_old = None
        cursor_old = None
        conn_current = None
        cursor_current = None

        try:
            old_table_name = self.table_id.old_db_table
            current_table_name = self.table_id.relational_db_tables

            # Connect to the old database
            connection = self.table_id.connection_id
            conn_old = psycopg2.connect(
                dbname=connection.old_db_name,
                user=connection.pg_username,
                password=connection.pg_password,
                host=connection.pg_host,
            )
            cursor_old = conn_old.cursor()

            # Connect to the current Odoo database
            conn_current = psycopg2.connect(
                dbname=self.env.cr.dbname,
                user="odoo",
                password="odoo",
                host="localhost",
            )
            cursor_current = conn_current.cursor()

            # Fetching only the selected fields
            selected_field_ids = self.env.context.get("active_ids", [])
            selected_fields = self.browse(selected_field_ids)

            if not selected_fields:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "No Fields Selected",
                        "message": "Please select fields to migrate.",
                        "type": "warning",
                        "sticky": False,
                    },
                }

            # Get selected field names
            old_field_names = ", ".join(
                [field.old_field_name for field in selected_fields]
            )
            current_field_names = [
                field.relational_field_name for field in selected_fields
            ]

            unique_fields = current_field_names

            unique_field_names = " AND ".join(
                [f"{field} = %s" for field in unique_fields]
            )

            # Fetch data from old database
            cursor_old.execute(f"SELECT {old_field_names} FROM {old_table_name};")
            rows = cursor_old.fetchall()

            if current_table_name == "account_move_line_account_tax_rel":
                # Fetch specific company data from old database
                cursor_old.execute(f"""
                    SELECT {old_field_names}
                    FROM {old_table_name} rel
                    JOIN account_move_line aml ON aml.id = rel.account_move_line_id
                    WHERE aml.company_id = 2;
                """)
                rows = cursor_old.fetchall()

                for row in rows:
                    old_move_line_id, old_tax_id = row

                    # Get new account.move.line ID using old_id
                    cursor_current.execute("SELECT id FROM account_move_line WHERE old_id = %s", (old_move_line_id,))
                    result = cursor_current.fetchone()
                    new_move_line_id = result[0] if result else None

                    # Get new account.tax ID using old_id
                    cursor_current.execute("SELECT id FROM account_tax WHERE old_id = %s", (old_tax_id,))
                    result = cursor_current.fetchone()
                    new_tax_id = result[0] if result else None

                    # Skip if mapping fails
                    if not new_move_line_id or not new_tax_id:
                        _logger.warning(
                            f"Skipping row: account_move_line_id or account_tax_id not found for old_ids: {old_move_line_id}, {old_tax_id}"
                        )
                        continue

                    # Check for existing record to avoid duplicates
                    cursor_current.execute(
                        """
                        SELECT 1 FROM account_move_line_account_tax_rel
                        WHERE account_move_line_id = %s AND account_tax_id = %s
                        """,
                        (new_move_line_id, new_tax_id)
                    )
                    if cursor_current.fetchone():
                        _logger.info(
                            f"Relation already exists for account_move_line_id={new_move_line_id}, account_tax_id={new_tax_id}. Skipping."
                        )
                        continue

                    # Insert the new relation
                    cursor_current.execute(
                        """
                        INSERT INTO account_move_line_account_tax_rel (account_move_line_id, account_tax_id)
                        VALUES (%s, %s)
                        """,
                        (new_move_line_id, new_tax_id)
                    )
                    _logger.info(
                        f"Inserted relation: account_move_line_id={new_move_line_id}, account_tax_id={new_tax_id}"
                    )
            elif current_table_name == "account_account_tag_account_move_line_rel":
                # Fetch specific company data from old database
                cursor_old.execute(f"""
                    SELECT {old_field_names}
                    FROM {old_table_name} rel
                    JOIN account_move_line aml ON aml.id = rel.account_move_line_id
                    WHERE aml.company_id = 2;
                """)
                rows = cursor_old.fetchall()

                for row in rows:
                    # Assuming row contains old_move_line_id and old_tag_id from old DB
                    old_move_line_id, old_tag_id = row

                    # Get new account.move.line ID using old_id
                    cursor_current.execute("SELECT id FROM account_move_line WHERE old_id = %s", (old_move_line_id,))
                    result = cursor_current.fetchone()
                    new_move_line_id = result[0] if result else None

                    # Get new account.account.tag ID using old_id
                    cursor_current.execute("SELECT id FROM account_account_tag WHERE old_id = %s", (old_tag_id,))
                    result = cursor_current.fetchone()
                    new_tag_id = result[0] if result else None

                    # Skip if mapping fails
                    if not new_move_line_id or not new_tag_id:
                        _logger.warning(
                            f"Skipping row: account_move_line_id or account_account_tag_id not found for old_ids: {old_move_line_id}, {old_tag_id}"
                        )
                        continue

                    # Check for existing record to avoid duplicates
                    cursor_current.execute(
                        """
                        SELECT 1 FROM account_account_tag_account_move_line_rel
                        WHERE account_move_line_id = %s AND account_account_tag_id = %s
                        """,
                        (new_move_line_id, new_tag_id)
                    )
                    if cursor_current.fetchone():
                        _logger.info(
                            f"Relation already exists for account_move_line_id={new_move_line_id}, account_account_tag_id={new_tag_id}. Skipping."
                        )
                        continue

                    # Insert the new relation
                    cursor_current.execute(
                        """
                        INSERT INTO account_account_tag_account_move_line_rel (account_move_line_id, account_account_tag_id)
                        VALUES (%s, %s)
                        """,
                        (new_move_line_id, new_tag_id)
                    )
                    _logger.info(
                        f"Inserted relation: account_move_line_id={new_move_line_id}, account_account_tag_id={new_tag_id}"
                    )
            elif current_table_name in ["product_supplier_taxes_rel", "product_taxes_rel"]:
                for row in rows:
                    old_prod_id, old_tax_id = row

                    # Get new product_template ID using old_id
                    cursor_current.execute("SELECT id FROM product_template WHERE old_id = %s", (old_prod_id,))
                    result = cursor_current.fetchone()
                    new_prod_id = result[0] if result else None

                    # Get new account_tax ID using old_id
                    cursor_current.execute("SELECT id FROM account_tax WHERE old_id = %s", (old_tax_id,))
                    result = cursor_current.fetchone()
                    new_tax_id = result[0] if result else None

                    # Skip if either mapping not found
                    if not new_prod_id or not new_tax_id:
                        _logger.warning(
                            f"Skipping row: prod_id or tax_id not found for old_ids: {old_prod_id}, {old_tax_id}")
                        continue

                    # Check if the record already exists to prevent duplicates
                    cursor_current.execute(
                        f"""
                           SELECT 1 FROM {current_table_name}
                           WHERE prod_id = %s AND tax_id = %s
                           """,
                        (new_prod_id, new_tax_id)
                    )
                    if cursor_current.fetchone():
                        _logger.info(
                            f"Relation already exists for prod_id={new_prod_id}, tax_id={new_tax_id}. Skipping.")
                        continue

                    # Insert the record
                    cursor_current.execute(
                        f"INSERT INTO {current_table_name} (prod_id, tax_id) VALUES (%s, %s)",
                        (new_prod_id, new_tax_id)
                    )
                    _logger.info(f"Inserted new relation: prod_id={new_prod_id}, tax_id={new_tax_id}")

            # For HR Expense tax_ids fields
            elif current_table_name == "expense_tax":
                for row in rows:
                    old_expense_id, old_tax_id = row

                    # Get new hr_expense ID using old_id
                    cursor_current.execute("SELECT id FROM hr_expense WHERE old_id = %s", (old_expense_id,))
                    result = cursor_current.fetchone()
                    new_expense_id = result[0] if result else None

                    # Get new account_tax ID using old_id
                    cursor_current.execute("SELECT id FROM account_tax WHERE old_id = %s", (old_tax_id,))
                    result = cursor_current.fetchone()
                    new_tax_id = result[0] if result else None

                    # Skip if mapping fails
                    if not new_expense_id or not new_tax_id:
                        _logger.warning(
                            f"Skipping: expense_id or tax_id not found for old_ids: {old_expense_id}, {old_tax_id}")
                        continue

                    # Check for existing entry to avoid duplicates
                    cursor_current.execute(
                        f"""
                        SELECT 1 FROM {current_table_name}
                        WHERE expense_id = %s AND tax_id = %s
                        """,
                        (new_expense_id, new_tax_id)
                    )
                    if cursor_current.fetchone():
                        _logger.info(
                            f"Relation already exists for expense_id={new_expense_id}, tax_id={new_tax_id}. Skipping.")
                        continue

                    # Insert the relation
                    cursor_current.execute(
                        f"INSERT INTO {current_table_name} (expense_id, tax_id) VALUES (%s, %s)",
                        (new_expense_id, new_tax_id)
                    )
                    _logger.info(f"Inserted: expense_id={new_expense_id}, tax_id={new_tax_id}")
            else:
                for row in rows:
                    record_data = {}
                    for idx, field_name in enumerate(current_field_names):
                        value = row[idx]
                        if isinstance(value, dict):
                            value = psycopg2.extras.Json(value)  # Handle JSON if needed
                        record_data[field_name] = value

                    insert_fields = ", ".join(current_field_names)
                    insert_placeholders = ", ".join(["%s"] * len(current_field_names))
                    sql_insert_query = f"INSERT INTO {current_table_name} ({insert_fields}) VALUES ({insert_placeholders})"
                    insert_values = [record_data[field] for field in current_field_names]
                    cursor_current.execute(sql_insert_query, insert_values)
                    _logger.info(f"Inserted new record with fields: {insert_values}")

            cursor_current.connection.commit()

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Migration Successful",
                    "message": f"Records migrated into {current_table_name} successfully!",
                    "type": "success",
                    "sticky": False,
                },
            }

        except Exception as e:
            _logger.error(f"Error during migration: {str(e)}")
            raise
        finally:
            if cursor_old:
                cursor_old.close()
            if conn_old:
                conn_old.close()
            if cursor_current:
                cursor_current.close()
            if conn_current:
                conn_current.close()

    def action_migrate_not_stored_fields(self):
        try:
            connection = self.table_id.connection_id
            url = f"{connection.old_odoo_url}"
            old_db = connection.old_db_name
            username = connection.old_username
            password = connection.old_password

            common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
            old_uid = common.authenticate(old_db, username, password, {})
            if not old_uid:
                raise ValueError("Failed to authenticate to the old database.")

            # Old database connection
            models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

            selected_field_ids = self.env.context.get("active_ids", [])
            selected_fields = self.browse(selected_field_ids)

            if not selected_fields:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "No Fields Selected",
                        "message": "Please select fields to migrate.",
                        "type": "warning",
                        "sticky": False,
                    },
                }

            field_names = [field.old_field_name for field in selected_fields]
            if "id" not in field_names:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Missing Required Field",
                        "message": "You must select the 'id' field for migration.",
                        "type": "danger",
                        "sticky": False,
                    },
                }

            # Prepare old DB Table
            old_table_name = self.table_id.old_db_table
            old_table_cus_name = old_table_name.replace("_", ".")

            # Fetch records from old DB
            old_records = []
            if old_table_name == "res_partner":
                old_records = models.execute_kw(old_db, old_uid, password, old_table_cus_name, "search_read", [[]],
                    {"fields": field_names, 'context': {'active_test': False}})
            else:
                old_records = models.execute_kw(old_db, old_uid, password, old_table_cus_name, "search_read", [[]],
                    {"fields": field_names, 'context': {'active_test': False}})

            for old_rec in old_records:
                old_id = old_rec.get("id")
                if not old_id:
                    continue

                # Migrate data to current DB
                current_rec = self.env[old_table_cus_name].search([("old_id", "=", old_id)], limit=1)
                if not current_rec:
                    continue

                update_vals = {}
                for field in selected_fields:
                    if field.old_field_name == "id":
                        continue

                    if field.old_field_name in ["property_account_receivable_id", "property_account_payable_id"]:
                        acc_field = old_rec.get(field.old_field_name)
                        acc_id = acc_field[0] if acc_field else False # many2one field (ID only)
                        acc_data = models.execute_kw(old_db, old_uid, password, "account.account", "read", [acc_id],
                            {"fields": ["code"]})
                        if acc_data:
                            account_rec = self.env["account.account"].search([("code", "=", acc_data[0]['code'])], limit=1)
                            if account_rec:
                                update_vals[field.old_field_name] = account_rec.id
                    elif field.old_field_name in ["property_payment_term_id", "property_supplier_payment_term_id"]:
                        old_payment_term = old_rec.get(field.old_field_name)
                        old_payment_term_id = old_payment_term[0] if old_payment_term else False # many2one field (ID only)
                        new_payment_term_id = self.env["account.payment.term"].search([("old_id", "=", old_payment_term_id)], limit=1)
                        if new_payment_term_id:
                            update_vals[field.old_field_name] = new_payment_term_id.id
                    else:
                        update_vals[field.old_field_name] = old_rec.get(field.old_field_name)

                if update_vals:
                    current_rec.write(update_vals)
                    _logger.info(f"Update record with : ID - {current_rec.id} | Old Id - {old_id} | Value - {update_vals}")

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Fields Migration Successful",
                    "message": f"Fields migrated into {old_table_cus_name} successfully!",
                    "type": "success",
                    "sticky": False,
                },
            }

        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Migration Error",
                    "message": f"Error during migration: {str(e)}",
                    "type": "danger",
                    "sticky": False,
                },
            }

    def update_create_date(self):
        conn_old = None
        cursor_old = None
        conn_current = None
        cursor_current = None
        try:
            old_table_name = self.table_id.old_db_table

            # Connect to the old database
            connection = self.table_id.connection_id
            conn_old = psycopg2.connect(
                dbname=connection.old_db_name,
                user=connection.pg_username,
                password=connection.pg_password,
                host=connection.pg_host,
            )
            cursor_old = conn_old.cursor()

            # Connect to the current Odoo database
            conn_current = psycopg2.connect(
                dbname=self.env.cr.dbname,
                user="odoo",
                password="odoo",
                host="localhost",
            )
            cursor_current = conn_current.cursor()

            # Fetch data from old database
            if old_table_name in [ 'hr_expense', 'hr_expense_sheet']:
                cursor_old.execute(f"SELECT id, create_date FROM {old_table_name} WHERE company_id = 2;")
                rows = cursor_old.fetchall()

                if rows:
                    for old_id, create_date in rows:
                        cursor_current.execute(f"""UPDATE {old_table_name} SET create_date = %s WHERE old_id = %s;""", (create_date, old_id))
                        _logger.info(f"Updated : {old_table_name} , Old id : {old_id}, Total Record : {len(rows)}.")

                    conn_current.commit()

        except Exception as e:
            _logger.error(f"Error during migration: {str(e)}")
            raise
        finally:
            if cursor_old:
                cursor_old.close()
            if conn_old:
                conn_old.close()
            if cursor_current:
                cursor_current.close()
            if conn_current:
                conn_current.close()

    # def update_payment_terms(self):
    #     try:
    #         connection = self.table_id.connection_id
    #
    #         url = f"{connection.old_odoo_url}"
    #         old_db = connection.old_db_name
    #         username = connection.old_username
    #         password = connection.old_password
    #
    #         new_db_name = self.env.cr.dbname
    #         old_table_name = self.table_id.old_db_table
    #         old_table_name = old_table_name.replace('_', '.')
    #
    #         # XML-RPC setup
    #         common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    #         models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    #
    #         # Authenticate
    #         old_uid = common.authenticate(old_db, username, password, {})
    #         new_uid = common.authenticate(new_db_name, username, password, {})
    #
    #         payment_fields = ['property_supplier_payment_term_id'] # 'property_payment_term_id',
    #
    #         for field_name in payment_fields:
    #
    #             # Fetch records from old DB
    #             old_record_ids = models.execute_kw(old_db, old_uid, password, old_table_name, 'search', [[(field_name, '!=', False)]], {'context': {'active_test': False}},)
    #             if not old_record_ids:
    #                 continue
    #             old_record_data = models.execute_kw(old_db, old_uid, password, old_table_name, 'read',[old_record_ids], {'fields': ['id', field_name]},)
    #             print(f"Fetched {len(old_record_data)} records with {field_name} from old DB.")
    #
    #             for rec in old_record_data:
    #                 old_rec_id = rec['id']
    #                 old_term_field = rec.get(field_name)
    #                 if not old_term_field:
    #                     continue
    #
    #                 old_payment_term_id = old_term_field[0]  # many2one field (ID only)
    #
    #                 # Find matching record in NEW DB by old_id
    #                 new_record_find = models.execute_kw(new_db_name, new_uid, password, old_table_name, 'search', [[('old_id', '=', old_rec_id)]], {'context': {'active_test': False}},)
    #                 if not new_record_find:
    #                     print(f"⚠️ Partner old_id {old_rec_id} not found in new DB.")
    #                     continue
    #
    #                 # Find matching payment term in NEW DB by old_id
    #                 new_payment_term_ids = models.execute_kw(new_db_name, new_uid, password, 'account.payment.term', 'search', [[('old_id', '=', old_payment_term_id)]],)
    #
    #                 if not new_payment_term_ids:
    #                     print(f"⚠️ Payment Term old_id {old_payment_term_id} not found in new DB for partner old_id {old_rec_id}")
    #                     continue
    #
    #                 models.execute_kw(new_db_name, new_uid, password, old_table_name, 'write', [new_record_find, {field_name: new_payment_term_ids[0]}],)
    #
    #                 print(f"✅ Updated partner old_id {old_rec_id} field {field_name} → term old_id {old_payment_term_id}")
    #
    #     except Exception as e:
    #         return {
    #             "type": "ir.actions.client",
    #             "tag": "display_notification",
    #             "params": {
    #                 "title": "Migration Error",
    #                 "message": f"Error during migration: {str(e)}",
    #                 "type": "danger",
    #                 "sticky": False,
    #             },
    #         }
