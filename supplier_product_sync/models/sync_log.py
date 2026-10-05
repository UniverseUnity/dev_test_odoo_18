from odoo import fields, models, api, _
import json
import logging
import time
from datetime import datetime
import os
import requests

_logger = logging.getLogger(__name__)

class SyncLog(models.Model):
    _name = 'supplier.sync.log'
    _description = 'Supplier Sync Log'
    _order = 'start_time desc'

    name = fields.Char(string='Name', compute='_compute_name')
    start_time = fields.Datetime('Start Time', required=True, default=fields.Datetime.now)
    end_time = fields.Datetime('End Time')
    duration = fields.Float('Duration (s)', compute='_compute_duration')
    status = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ], string='Status', required=True)
    
    total_records = fields.Integer('Total Records', default=0)
    records_created = fields.Integer('Created', default=0)
    records_updated = fields.Integer('Updated', default=0)
    records_failed = fields.Integer('Failed', default=0)
    
    error_message = fields.Text('Error Message')
    line_ids = fields.One2many('supplier.sync.log.line', 'log_id', string='Failed Records')

    @api.depends('start_time')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Sync {rec.start_time}" if rec.start_time else "New Sync"

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time and rec.end_time:
                delta = rec.end_time - rec.start_time
                rec.duration = delta.total_seconds()
            else:
                rec.duration = 0.0

    def action_sync_now(self):
        self.env.ref('supplier_product_sync.ir_cron_supplier_product_sync')._trigger()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Supplier sync scheduled'),
                'message': _('The supplier feed will be processed in the background.'),
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def perform_sync(self):
        start_time = fields.Datetime.now()
        start_ts = time.time()
        feed_path = self.env['ir.config_parameter'].sudo().get_param('supplier_product_sync.supplier_feed_path')
        log_vals = {
            'start_time': start_time,
            'status': 'failed',
            'error_message': ''
        }
        if not feed_path:
            log_vals['error_message'] = 'Feed path not configured in Settings.'
            self.create(log_vals)
            return
            
        try:
            if feed_path.startswith('http://') or feed_path.startswith('https://'):
                resp = requests.get(feed_path, timeout=60)
                resp.raise_for_status()
                data = resp.json()
            else:
                if not os.path.exists(feed_path):
                    log_vals['error_message'] = f'File not found: {feed_path}'
                    self.create(log_vals)
                    return
                with open(feed_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
        except Exception as e:
            log_vals['error_message'] = f'Failed to read feed: {str(e)}'
            self.create(log_vals)
            return
        if not isinstance(data, list):
            log_vals['error_message'] = 'Invalid feed format. Expected a list.'
            self.create(log_vals)
            return

        # Prepare processing
        log_vals['total_records'] = len(data)
        failed_lines = []
        created_count = 0
        updated_count = 0
        
        product_category_obj = self.env['product.category'].sudo()
        product_product_obj = self.env['product.product'].sudo()
        stock_quant_obj = self.env['stock.quant'].sudo()
        stock_localtion_obj = self.env.ref('stock.stock_location_stock').sudo()
        

        existing_categories = {c.name: c.id for c in product_category_obj.search([])}
        
        existing_products = {}
        all_skus = [str(r.get('sku')) for r in data if r.get('sku')]
        
        batch_size = 5000

        for i in range(0, len(all_skus), batch_size):
            sku_batch = all_skus[i:i+batch_size]
            products = product_product_obj.search([('default_code', 'in', sku_batch)])
            for p in products:
                existing_products[p.default_code] = p.id

        products_to_create = []
        products_to_update = {}
        quants_to_update = {} # product_id: qty
        
        for record in data:
            try:
                sku = record.get('sku')
                name = record.get('name')
                cost = record.get('cost')
                price = record.get('price')
                qty = record.get('qty')
                category_name = record.get('category')
                
                # Validation
                if not sku or not isinstance(sku, str):
                    raise ValueError('Missing or invalid SKU')
                if not name or not isinstance(name, str):
                    raise ValueError('Missing or invalid Name')
                if not isinstance(cost, (int, float)) or cost < 0:
                    raise ValueError('Cost must be a positive number')
                if not isinstance(price, (int, float)) or price < 0:
                    raise ValueError('Price must be a positive number')
                if not isinstance(qty, int) or qty < 0:
                    raise ValueError('Qty must be a positive integer')
                    
                categ_id = False
                if category_name and isinstance(category_name, str):
                    if category_name not in existing_categories:
                        new_cat = product_category_obj.create({'name': category_name})
                        existing_categories[category_name] = new_cat.id
                    categ_id = existing_categories[category_name]
                product_vals = {
                    'default_code': sku,
                    'name': name,
                    'standard_price': cost,
                    'list_price': price,
                    'categ_id': categ_id,
                    'is_storable': True,
                    'type': 'consu',
                }
                
                if sku in existing_products:
                    product_id = existing_products[sku]
                    products_to_update[product_id] = product_vals
                else:
                    products_to_create.append(product_vals)
                
                quants_to_update[sku] = qty
                
            except Exception as e:
                _logger.warning("Skipping supplier record %s: %s", record.get('sku'), e)
                failed_lines.append({
                    'sku': str(record.get('sku', '')),
                    'error': str(e),
                })
        
        if products_to_create:
            create_batch_size = 500
            self.env['ir.cron']._commit_progress(remaining=len(products_to_create))
            for offset in range(0, len(products_to_create), create_batch_size):
                batch_vals = products_to_create[offset:offset + create_batch_size]
                created_products = product_product_obj.create(batch_vals)
                for product in created_products:
                    existing_products[product.default_code] = product.id
                created_count += len(created_products)
                self.env['ir.cron']._commit_progress(processed=len(batch_vals))
                
        for pid, vals in products_to_update.items():
            try:
                product_product_obj.browse(pid).with_context(tracking_disable=True).write(vals)
                updated_count += 1
            except Exception as e:
                sku = vals['default_code']
                _logger.exception("Could not update supplier product %s", sku)
                failed_lines.append({
                    'sku': sku,
                    'error': _('Could not update product: %s') % e,
                })
                existing_products.pop(sku, None)
            
        existing_quants = stock_quant_obj.search([
            ('product_id', 'in', list(existing_products.values())),
            ('location_id', '=', stock_localtion_obj.id)
        ])
        quant_by_product = {q.product_id.id: q for q in existing_quants}
        
        quants_to_apply = self.env['stock.quant']
        
        for sku, qty in quants_to_update.items():
            if sku in existing_products:
                try:
                    pid = existing_products[sku]
                    quant = quant_by_product.get(pid)
                    if quant:
                        if quant.quantity != qty:
                            quant.with_context(inventory_mode=True).inventory_quantity = qty
                            quants_to_apply |= quant
                    elif qty > 0:
                        quant = stock_quant_obj.with_context(inventory_mode=True).create({
                            'product_id': pid,
                            'location_id': stock_localtion_obj.id,
                            'inventory_quantity': qty,
                        })
                        quants_to_apply |= quant
                except Exception as e:
                    _logger.exception("Could not prepare stock adjustment for supplier product %s", sku)
                    failed_lines.append({
                        'sku': sku,
                        'error': _('Product was saved, but stock could not be set: %s') % e,
                    })
                        
        if quants_to_apply:
            try:
                quants_to_apply.action_apply_inventory()
            except Exception as e:
                _logger.exception("Could not apply supplier stock adjustments")
                failed_lines.append({
                    'sku': '',
                    'error': _('Products were saved, but stock adjustments could not be applied: %s') % e,
                })

        end_time = fields.Datetime.now()
        
        log_vals.update({
            'end_time': end_time,
            'status': 'partial' if failed_lines else 'success',
            'records_created': created_count,
            'records_updated': updated_count,
            'records_failed': len(failed_lines),
        })
        
        if failed_lines:
            log_vals['line_ids'] = [(0, 0, line) for line in failed_lines]
            
        self.create(log_vals)


class SyncLogLine(models.Model):
    _name = 'supplier.sync.log.line'
    _description = 'Supplier Sync Log Line'

    log_id = fields.Many2one('supplier.sync.log', string='Log', ondelete='cascade')
    sku = fields.Char('SKU')
    error = fields.Text('Error Message')
