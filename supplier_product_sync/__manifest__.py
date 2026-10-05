{
    'name': 'Supplier Product & Stock Sync',
    'version': '1.0',
    'category': 'Inventory/Inventory',
    'summary': 'Sync products and stock from supplier feed',
    'depends': ['stock', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
        'views/sync_log_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
