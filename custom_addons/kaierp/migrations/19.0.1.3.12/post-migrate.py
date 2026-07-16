# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID, fields

    env = api.Environment(cr, SUPERUSER_ID, {})

    students = env['school.student'].search([('partner_id', '=', False)])
    if students:
        students._ensure_partner()
        _logger.info('Created billing contacts for %s student(s).', len(students))

    paid_without_invoice = env['school.fee'].search([
        ('state', '=', 'paid'),
        ('invoice_id', '=', False),
    ])
    for fee in paid_without_invoice:
        try:
            fee._create_invoice_record()
            fee._register_invoice_payment(fee.invoice_id)
            fee.write({
                'state': 'paid',
                'amount_paid': fee.amount_due,
                'payment_date': fields.Date.today(),
            })
        except Exception:
            _logger.exception(
                'Could not backfill invoice for fee %s (student %s).',
                fee.id, fee.student_id.name,
            )

    invoiced_fees = env['school.fee'].search([
        ('invoice_id', '!=', False),
        ('state', '!=', 'paid'),
    ])
    for fee in invoiced_fees:
        if fee.invoice_id.payment_state == 'paid':
            fee.write({
                'state': 'paid',
                'amount_paid': fee.amount_due,
                'payment_date': fee.invoice_id.date or fields.Date.today(),
            })
