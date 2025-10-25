{
    "name": "Database Migration",
    "version": "1.0",
    "category": "Tools",
    "Summary": "Module to connect to older Odoo versions for data migration",
    "description": "Allows users to connect to old Odoo databases for migration purposes.",
    "author": "Karan Herma",
    "depends": [
        "base",
        "hr",
        "sale",
        "customer_post_dated_cheque_app",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/db_conn.xml",
        "views/migration_field.xml",
        "views/old_field.xml",
    ],
    "installable": True,
    "application": False,
}
