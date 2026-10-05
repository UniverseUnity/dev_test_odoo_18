from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class SaleOrderRejectWizard(models.TransientModel):

    _name = 'sale.order.reject.wizard'
    _description = "Sale Order Rejection Wizard"

    order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Sale Order",
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    reason = fields.Text(
        string="Rejection Reason",
        required=True,
        help="Please provide a reason for rejecting this sale order.",
    )

    def action_confirm_reject(self):
        self.ensure_one()

        if not self.reason or not self.reason.strip():
            raise UserError(_("A rejection reason is required."))

        order = self.order_id

        if not self.env.user.has_group('sales_team.group_sale_manager'):
            raise AccessError(_(
                "Only users in the Sales / Administrator group can reject sale orders."
            ))

        if order.state != 'to_approve':
            raise UserError(_(
                "Order %s is not waiting for approval.", order.name
            ))

        order._mark_approval_activities_done()

        order.message_post(
            body=_(
                "Order rejected by <b>%(user)s</b>.<br/>"
                "<b>Reason:</b> %(reason)s",
                user=self.env.user.name,
                reason=self.reason,
            )
        )

        order.write({
            'state': 'draft',
        })

        return {'type': 'ir.actions.act_window_close'}
