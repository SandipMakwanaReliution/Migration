from odoo import models, fields, api
import psycopg2
import logging

_logger = logging.getLogger(__name__)


class MigrationTable(models.Model):
    _name = "migration.table"
    _description = "Load the current and old database fields."

    name = fields.Char(string="Migration Table", readonly=True)
    old_db_table = fields.Char(string="Old Database Table", readonly=True)
    current_db_table = fields.Many2one(
        "ir.model", string="Current Database Table", readonly=False
    )
    relational_db_tables = fields.Char(string="Related Database Tables", readonly=False)
    connection_id = fields.Many2one(
        "database.connection", string="Database Connection", readonly=True
    )
    matched = fields.Boolean("Matched", default=False)
    field_comparison_ids = fields.One2many(
        "migration.field", "table_id", string="Fields Comparison"
    )

    def unlink(self):
        for table in self:
            table.field_comparison_ids.unlink()
        return super(MigrationTable, self).unlink()

    def load_fields(self):
        """Load and compare fields between old and current database for selected tables..."""
        self.field_comparison_ids.unlink()
        self.ensure_one()

        # Fetch fields from the old and current databases...
        old_fields = self._fetch_old_db_fields(self.old_db_table)
        current_fields_dict = self._fetch_current_db_fields(
            self.current_db_table.model, self.relational_db_tables
        )

        current_fields = list(current_fields_dict.values())

        # Create a mapping of current field names...
        current_field_mapping = {field["name"]: field for field in current_fields}

        # if 'old_id' not in current_field_mapping:
        #  _logger.info("Old Id is not there so created new.")
        # self._create_field_in_current_table(field_name='old_id', field_type='integer', model_name=self.current_db_table.model)

        field_comparisons = []
        for old_field in old_fields:
            # Get name from current_fields and find name mapping in old_field...
            current_field = current_field_mapping.get(old_field["name"])

            # Initialize comparison data
            comparison_data = {
                "old_field_name": old_field["name"],
                "old_data_type": old_field["data_type"],
                "matched": False,
            }

            # If a match is found in the current model's fields
            if current_field:
                comparison_data.update(
                    {
                        "current_field_name": current_field["id"],
                        "current_data_type": current_field["data_type"],
                        "matched": True,
                    }
                )

                if not current_field.get("id"):
                    comparison_data.update(
                        {
                            "relational_field_name": current_field["name"],
                            "current_data_type": current_field["data_type"],
                            "matched": True,
                        }
                    )

                # Add relational information if it's a relational field
                if current_field["data_type"] in ["many2many", "one2many", "many2one"]:
                    comparison_data["relation"] = current_field["relation"]

            field_comparisons.append((0, 0, comparison_data))

        # Update field comparison records...
        self.write({"field_comparison_ids": field_comparisons})

        # This action will open the new view for fields...
        action = self.env.ref("database_migration.action_load_fields").read()[0]
        return action

    def _create_field_in_current_table(self, field_name, field_type, model_name):
        model_record = self.env["ir.model"].search(
            [("model", "=", model_name)], limit=1
        )

        if not model_record:
            raise ValueError(
                f"Model '{model_name}' does not exist in 'ir.model'. Cannot create the field."
            )

        model_id = model_record.id
        table_name = model_record.model
        t_name = table_name.replace(".", "_")

        try:
            self._cr.execute(
                f"""
               SELECT column_name
               FROM information_schema.columns
               WHERE table_name = %s AND column_name = %s;
           """,
                (t_name, field_name),
            )

            # If the column exists, the query will return a result
            column_exists = self._cr.fetchone()

            if column_exists:
                _logger.info(
                    f"Field '{field_name}' already exists in table '{t_name}'. No action taken."
                )
                return

        except psycopg2.Error as e:
            _logger.error(f"Error checking for column {field_name}: {e}")
            return

        # Add the column to the table if it does not exist
        try:
            self._cr.execute(
                f"""
               ALTER TABLE {t_name} ADD COLUMN {field_name} {field_type};
           """
            )
            _logger.info(
                f"Field '{field_name}' added to model '{model_name}' and table '{table_name}'."
            )
        except psycopg2.Error as e:
            _logger.error(f"Error adding field '{field_name}' to table '{t_name}': {e}")

    def _fetch_old_db_fields(self, table_name):
        """Fetch fields from the old database including relational fields."""
        connection = self.connection_id
        conn = psycopg2.connect(
            dbname=connection.old_db_name,
            user=connection.pg_username,
            password=connection.pg_password,
            host=connection.pg_host,
        )

        # Fetch standard fields from information_schema
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table_name}';
        """
        )
        standard_fields = cursor.fetchall()
        conn.close()

        m_name = table_name.replace("_", ".")

        # Prepare standard fields for comparison
        fields_list = [
            {"name": field[0], "data_type": field[1]} for field in standard_fields
        ]

        # Fetch relational fields using Odoo model metadata
        model_obj = self.env["ir.model"].search([("model", "=", m_name)], limit=1)
        if model_obj:
            relational_fields = self.env["ir.model.fields"].search(
                [
                    ("model_id", "=", model_obj.id),
                    ("ttype", "in", ["one2many", "many2many"]),
                ]
            )

            for field in relational_fields:
                fields_list.append(
                    {
                        "name": field.name,
                        "data_type": field.ttype,
                        "relation": field.relation,
                    }
                )

        return fields_list

    def _fetch_current_db_fields(self, model_name, table_name):
        """Fetch fields from the current Odoo model, including One2many and Many2many fields."""

        connection = self.connection_id
        conn = psycopg2.connect(
            dbname=self._cr.dbname,
            user="odoo",
            password="odoo",
            host="localhost",
        )

        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table_name}';
        """
        )
        standard_fields = cursor.fetchall()
        conn.close()

        field_dict = {
            field[0]: {
                "name": field[0],
                "data_type": field[1],
                "id": None,
                "relation": None,
            }
            for field in standard_fields
        }

        fields = self.env["ir.model.fields"].search([("model", "=", model_name)])

        for field in fields:
            if field.name in field_dict:
                field_dict[field.name].update(
                    {
                        "id": field.id,
                        "data_type": field.ttype,
                        "relation": field.relation
                        if field.ttype in ["many2one", "one2many", "many2many"]
                        else None,
                    }
                )
            else:
                field_dict[field.name] = {
                    "name": field.name,
                    "id": field.id,
                    "data_type": field.ttype,
                    "relation": field.relation
                    if field.ttype in ["many2one", "one2many", "many2many"]
                    else None,
                }

        return field_dict
