# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    admissions = env['school.admission'].search([
        '|',
        ('application_fee_paid', '=', True),
        ('payment_successful', '=', True),
    ])
    admissions._register_application_fee_accounting_if_paid()
    created = admissions.filtered('application_fee_invoice_id')
    _logger.info(
        'Created application fee invoices for %s admission(s).',
        len(created),
    )

    # Post and register payment on exam accommodation invoices created earlier.
    for admission in env['school.admission'].search([
        ('exam_accommodation_invoice_id', '!=', False),
        ('exam_accommodation_paid', '=', True),
    ]):
        invoice = admission.exam_accommodation_invoice_id
        if invoice.payment_state != 'paid':
            admission._post_invoice_and_register_payment(invoice)
