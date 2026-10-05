from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class SupplierSyncController(http.Controller):

    @http.route('/api/supplier/price', type='http', auth='public', methods=['POST'], csrf=False)
    def update_price(self, **kwargs):
        # Keep this key aligned with res.config.settings.  Webhook requests
        # are public and therefore do not reliably carry a company context.
        expected_token = request.env['ir.config_parameter'].sudo().get_param(
            'supplier_product_sync.supplier_webhook_token',
            default='',
        )
        
        auth_header = request.httprequest.headers.get('Authorization')
        token = ''
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
        if not expected_token or token != expected_token:
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Unauthorized'}),
                headers=[('Content-Type', 'application/json')],
                status=401
            )
            
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        except Exception:
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Invalid JSON'}),
                headers=[('Content-Type', 'application/json')],
                status=400
            )

        if not isinstance(data, dict):
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': 'Invalid payload. Expected a JSON object with sku and price.',
                }),
                headers=[('Content-Type', 'application/json')],
                status=400,
            )
            
        sku = data.get('sku')
        price = data.get('price')
        
        if not sku or not isinstance(sku, str):
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Invalid or missing SKU'}),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
            
        if not isinstance(price, (int, float)) or price < 0:
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Invalid price, must be positive number'}),
                headers=[('Content-Type', 'application/json')],
                status=400
            )
            
        product = request.env['product.product'].sudo().search([('default_code', '=', sku)], limit=1)
        if not product:
            return request.make_response(
                json.dumps({'status': 'error', 'message': 'Unknown SKU'}),
                headers=[('Content-Type', 'application/json')],
                status=404
            )
            
        old_price = product.list_price
        product.write({'list_price': price})
        
        product.message_post(
            body=f"Price updated via webhook from {old_price} to {price}"
        )
        
        return request.make_response(
            json.dumps({'status': 'success', 'message': 'Price updated successfully'}),
            headers=[('Content-Type', 'application/json')],
            status=200
        )
