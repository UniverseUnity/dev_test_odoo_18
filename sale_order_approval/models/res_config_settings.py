from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    sale_order_approval_limit = fields.Monetary(
        string="Order Approval Limit",
        related='company_id.sale_order_approval_limit',
        currency_field='company_currency_id',
        help="Sale orders whose total exceeds this amount must be approved by "
             "a Sales Manager before they can be confirmed.",
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string="Company Currency",
    )
