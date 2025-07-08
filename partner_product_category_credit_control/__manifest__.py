{
    "name": "Partner Product Category Credit Control",
    "version": "18.0.1.0.0",
    "depends": ["contacts", "account"],
    "author": "Tu Empresa",
    "category": "Accounting",
    "description": "Gestión de líneas de crédito por categoría de producto para contactos",
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/product_category_credit_views.xml",
        # "views/account_move_views.xml"
    ],
    "installable": True,
    "auto_install": False,
}
