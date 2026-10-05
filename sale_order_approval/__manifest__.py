{
    'name': 'Sale Order Approval',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Require manager approval for large sale orders',
    'description': """
        Adds an approval workflow for sale orders that exceed a configurable limit.
        Orders above the limit require approval from a Sales Manager before
        they can be confirmed.
    """,
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_activity_data.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'wizard/sale_order_reject_wizard_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
