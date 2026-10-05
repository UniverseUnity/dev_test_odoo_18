from odoo import fields, models


class ResCompany(models.Model):

    _inherit = 'res.company'

    sale_order_approval_limit = fields.Monetary(
        string="Order Approval Limit",
        currency_field='currency_id',
        default=10000.0,
        help="Sale orders with a total above this amount will require approval "
             "from a Sales Manager before they can be confirmed.",
    )
