# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_ets_fee = fields.Boolean(
        string='ETS Fee Product',
        help='Marks this product as part of the seminary fee catalog.',
    )
    ets_fee_code = fields.Char(
        string='Fee Code',
        help='Internal code used when assigning fees to students.',
    )
    billing_unit = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('credit_hour', 'Per Credit Hour'),
        ('month', 'Per Month'),
        ('night', 'Per Night'),
        ('annual', 'Annual'),
    ], string='Billing Unit', default='fixed')
    default_quantity = fields.Float(
        string='Default Quantity',
        default=1.0,
        help='Default units when assigning (e.g. 10 months for accommodation).',
    )
    is_refundable = fields.Boolean(string='Refundable Deposit')
    is_application_fee = fields.Boolean(string='Application Fee Product')
