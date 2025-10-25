from odoo import api, models, fields
import xmlrpc.client
import psycopg2
import logging

_logger = logging.getLogger(__name__)


class DBconnection(models.Model):
    _name = "database.connection"
    _description = "Connect to the database and load tables."

    name = fields.Char(string="Connection Name", required=True)
    uid = fields.Integer(string="Session UID", readonly=True)
    old_odoo_url = fields.Char(string="Instance URL", required=True)
    old_db_name = fields.Char(string="Database Name", required=True)
    old_username = fields.Char(string="Database Username", required=True)
    old_password = fields.Char(string="Database Password", required=True)
    pg_username = fields.Char(string="PostgreSQL Username", required=True)
    pg_password = fields.Char(string="PostgreSQL Password", required=True)
    pg_host = fields.Char(string="PostgreSQL Host", required=True, default="localhost")
    state = fields.Selection(
        [("not_connected", "Not Connected"), ("connected", "Connected")],
        default="not_connected",
        string="Connection Status",
    )
    migration_table_ids = fields.One2many(
        "migration.table", "connection_id", string="Migration Tables"
    )

    def connect_to_database(self):
        """Connect with the old database with the help of xmlrpc..."""
        common_url = f"{self.old_odoo_url}/xmlrpc/2/common"  # For Common URL
        object_url = f"{self.old_odoo_url}/xmlrpc/2/object"  # For Object URL
        try:
            # Connection Lines...
            common = xmlrpc.client.ServerProxy(common_url)
            uid = common.authenticate(
                self.old_db_name, self.old_username, self.old_password, {}
            )
            # If connected then show below notification...
            if uid:
                self.uid = uid
                self.state = "connected"
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "success",
                        "message": "Connected to the Database which you want to migrate...",
                        "type": "success",
                        "sticky": False,
                    },
                }
            # Otherwise if credentials wrong then show below error...
            else:
                raise Exception("Invalid credentials or unable to authenticate.")
        # Any other error then show below notification...
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Unexpected Error",
                    "message": f"An error occurred : str{e}",
                    "type": "danger",
                    "sticky": False,
                },
            }

    def disconnect_database(self):
        """For disconnecting the database connection..."""
        self.state = "not_connected"
        self.uid = None

        # Get tables from connection ID and unlink them...
        tables = self.env["migration.table"].search([("connection_id", "=", self.id)])
        tables.unlink()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Disconnected",
                "message": "Successfully disconnected and removed all related table and field records.",
                "type": "info",
                "sticky": False,
            },
        }

    def load_tables(self):
        """Load and display only matched tables with ID set in the current database..."""
        old_tables = self._fetch_old_db_tables()  # Fetch Old database tables
        current_tables = (
            self._fetch_current_db_tables()
        )  # Fetch Current database tables

        # Fetch existing migration.table records to avoid duplication...
        existing_tables = self.env["migration.table"].search(
            [("connection_id", "=", self.id)]
        )
        existing_table_names = {table.old_db_table: table for table in existing_tables}

        # Compare tables and update or create records for only those that are matched and have ID set
        for old_table in old_tables:
            match = next(
                (
                    t
                    for t in current_tables
                    if t["name"] == old_table["name"] and t["id"]
                ),
                None,
            )
            match1 = next(
                (
                    t
                    for t in current_tables
                    if t["name"] == old_table["name"] and not t["id"]
                ),
                None,
            )

            table_data = {
                "name": old_table["name"],
                "old_db_table": old_table["name"],
                "connection_id": self.id,
                "matched": False,
            }

            if match:
                table_data.update(
                    {
                        "current_db_table": match["id"],
                        "matched": True,
                    }
                )

            elif match1:
                table_data.update(
                    {
                        "relational_db_tables": match1["name"],
                        "matched": True,
                    }
                )

            if old_table["name"] in existing_table_names:
                existing_table_names[old_table["name"]].write(table_data)
            else:
                self.env["migration.table"].create(table_data)

        response = {
            "type": "ir.actions.client",
            "tag": "reload",
            "params": {
                "title": "Tables Loaded",
                "type": "success",
                "sticky": False,
            },
        }

        return response

    def _fetch_old_db_tables(self):
        """Fetch all tables from the old database using psycopg2..."""
        if self.state == "connected":  # If the database is connected...
            conn = psycopg2.connect(
                dbname=self.old_db_name,
                user=self.pg_username,
                password=self.pg_password,
                host=self.pg_host,
            )

            cursor = conn.cursor()
            # SQL Query for getting the all public schemas from old connected database...
            cursor.execute(
                """
                SELECT tablename
                FROM pg_catalog.pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
            """
            )
            old_db_tables = cursor.fetchall()

            conn.close()

            # Convert result to a list of dictionaries...
            return [{"name": table[0]} for table in old_db_tables]

        else:
            return []

    def _fetch_current_db_tables(self):
        """Fetch all tables from the current Odoo database using psycopg2..."""
        if self.state == "connected":
            current_conn = psycopg2.connect(
                dbname=self._cr.dbname, user="odoo", password="odoo", host="localhost"
            )

            current_cursor = current_conn.cursor()
            # SQL Query for getting the all public schemas from current odoo database...
            current_cursor.execute(
                """
                SELECT tablename
                FROM pg_catalog.pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
            """
            )

            current_tables = current_cursor.fetchall()

            current_conn.close()

            models = self.env["ir.model"].search([])
            model_table_mapping = {}

            for model in models:
                try:
                    env_model = self.env[model.model]
                    if hasattr(env_model, "_table"):
                        model_table_mapping[env_model._table] = model.id
                except KeyError:
                    _logger.warning("Model not found in registry: %s", model.model)

            table_list = []

            for table in current_tables:
                table_name = table[0]
                model_id = model_table_mapping.get(table_name, False)
                table_list.append(
                    {
                        "name": table_name,
                        "id": model_id if model_id else None,
                    }
                )

            return table_list

            # current_tables = [{'name': table[0], 'id': model_table_mapping.get(table[0], False)} for table in current_tables]

            # return current_tables
        else:
            return []
