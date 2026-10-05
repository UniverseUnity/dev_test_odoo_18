# © 2026 - Sale Order Approval Module
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

# add field
# fetch user 
# when confirm check user
# if its manager or above then not to send in approve dircor confirm
# if normal user then send approval notification
class SaleOrder(models.Model):

    _inherit = 'sale.order'

    state = fields.Selection(
        selection_add=[('to_approve', "To Approve")],
        ondelete={'to_approve': 'set draft'},
    )

    
    def _is_sale_manager(self):
        return self.env.user.has_group('sales_team.group_sale_manager')

    def _get_approval_limit(self):
        return self.company_id.sale_order_approval_limit

    def action_confirm(self):
        
        orders_to_approve = self.env['sale.order']
        orders_to_confirm = self.env['sale.order']

        for order in self:
            if order.state not in ('draft', 'sent'):
                orders_to_confirm |= order
                continue

            if not self._is_sale_manager() and order.amount_total > order._get_approval_limit():
                orders_to_approve |= order
            else:
                orders_to_confirm |= order

        if orders_to_approve:
            orders_to_approve._action_request_approval()

        if orders_to_confirm:
            orders_to_confirm.super_action_confirm()

        return True

    def super_action_confirm(self):
        return super().action_confirm()

  
    def _confirmation_error_message(self):
        if self.state == 'to_approve':
            return False
        return super()._confirmation_error_message()

    def _action_request_approval(self):
        self.write({'state': 'to_approve'})
        for order in self:
            order._notify_approval_needed()
            order.message_post(
                body=_(
                    "Approval requested by <b>%(user)s</b>. "
                    "The order total (%(amount)s) exceeds the approval limit.",
                    user=self.env.user.name,
                    amount=order._format_amount(order.amount_total),
                )
            )

    def _notify_approval_needed(self):
        self.ensure_one()
        manager_group = self.env.ref('sales_team.group_sale_manager')
        managers = manager_group.all_user_ids.filtered(lambda u: not u.share)
        if not managers:
            return

        activity_type = self.env.ref(
            'sale_order_approval.mail_activity_type_approve_order',
            raise_if_not_found=False,
        )
        if not activity_type:
            activity_type = self.env.ref('mail.mail_activity_data_todo')

        for manager in managers:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                summary=_("Review and approve sale order %s", self.name),
                note=_(
                    "The order total (%(amount)s) exceeds the approval limit. "
                    "Please review and approve or reject.",
                    amount=self._format_amount(self.amount_total),
                ),
                user_id=manager.id,
            )

    def _mark_approval_activities_done(self):
        self.ensure_one()
        activity_type = self.env.ref(
            'sale_order_approval.mail_activity_type_approve_order',
            raise_if_not_found=False,
        )
        domain = [
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.id),
        ]
        if activity_type:
            domain.append(('activity_type_id', '=', activity_type.id))

        activities = self.env['mail.activity'].search(domain)
        activities.action_done()

    def _format_amount(self, amount):
        return '{0:,.2f} {1}'.format(amount, self.currency_id.name)


    def action_approve(self):
        self._check_manager_access()
        for order in self:
            if order.state != 'to_approve':
                raise UserError(_(
                    "Order %s is not waiting for approval.", order.name
                ))
            order._mark_approval_activities_done()
            order.message_post(
                body=_(
                    "Order approved by <b>%(user)s</b>.",
                    user=self.env.user.name,
                )
            )
            
            order.super_action_confirm()



    def action_reject(self):
        self.ensure_one()
        self._check_manager_access()
        if self.state != 'to_approve':
            raise UserError(_(
                "Order %s is not waiting for approval.", self.name
            ))
        return {
            'name': _("Reject Order"),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }


    def _check_manager_access(self):
        if not self._is_sale_manager():
            raise AccessError(_(
                "Only users in the Sales / Administrator group can approve "
                "or reject sale orders."
            ))
