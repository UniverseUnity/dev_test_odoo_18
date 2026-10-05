from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    supplier_feed_path = fields.Char(
        string='Supplier Feed Path',
        config_parameter='supplier_product_sync.supplier_feed_path',
        help='Local file path or URL for the JSN feed'
    )
    supplier_webhook_token = fields.Char(
        string='Webhook Token',
        config_parameter='supplier_product_sync.supplier_webhook_token',
        help='Token for the price update webhook'
    )
