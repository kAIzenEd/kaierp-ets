# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def _sql_update_partner(cr, partner_id, move_id):
    cr.execute(
        'UPDATE account_move SET partner_id = %s WHERE id = %s',
        (partner_id, move_id),
    )
    cr.execute(
        'UPDATE account_move_line SET partner_id = %s WHERE move_id = %s',
        (partner_id, move_id),
    )


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    admissions = env['school.admission'].search([('email', '!=', False)])
    admissions._ensure_applicant_partner()

    students = env['school.student'].search([('email', '!=', False)])
    students._ensure_partner()

    for admission in env['school.admission'].search([
        ('exam_accommodation_invoice_id', '!=', False),
    ]):
        invoice = admission.exam_accommodation_invoice_id
        partner = admission.partner_id
        if partner and invoice.partner_id != partner:
            _sql_update_partner(cr, partner.id, invoice.id)
            _logger.info(
                'Fixed invoice %s customer → %s.',
                invoice.name, partner.name,
            )

    for fee in env['school.fee'].search([('invoice_id', '!=', False)]):
        partner = fee.student_id.partner_id
        invoice = fee.invoice_id
        if partner and invoice.partner_id != partner:
            _sql_update_partner(cr, partner.id, invoice.id)
            _logger.info(
                'Fixed invoice %s customer → %s.',
                invoice.name, partner.name,
            )

    for payment in env['account.payment'].sudo().search([]):
        invoices = payment.reconciled_invoice_ids
        if len(invoices) != 1:
            continue
        partner = invoices.partner_id
        if not partner or payment.partner_id == partner:
            continue
        cr.execute(
            'UPDATE account_payment SET partner_id = %s WHERE id = %s',
            (partner.id, payment.id),
        )
        if payment.move_id:
            _sql_update_partner(cr, partner.id, payment.move_id.id)
        _logger.info(
            'Fixed payment %s customer → %s (invoice %s).',
            payment.name, partner.name, invoices.name,
        )
