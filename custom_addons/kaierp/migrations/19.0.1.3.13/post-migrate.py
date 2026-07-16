# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    admissions = env['school.admission'].search([('email', '!=', False)])
    for admission in admissions:
        expected_name = (admission.name or admission.email or '').strip()
        if (
            admission.partner_id
            and admission.partner_id.name != expected_name
        ):
            admission.partner_id = False
    admissions._ensure_applicant_partner()

    students = env['school.student'].search([('email', '!=', False)])
    for student in students:
        expected_name = (student.name or student.email or '').strip()
        if student.partner_id and student.partner_id.name != expected_name:
            student.partner_id = False
    students._ensure_partner()

    for admission in env['school.admission'].search([
        ('exam_accommodation_invoice_id', '!=', False),
    ]):
        invoice = admission.exam_accommodation_invoice_id
        if invoice.partner_id != admission.partner_id:
            cr.execute(
                'UPDATE account_move SET partner_id = %s WHERE id = %s',
                (admission.partner_id.id, invoice.id),
            )
            cr.execute(
                'UPDATE account_move_line SET partner_id = %s WHERE move_id = %s',
                (admission.partner_id.id, invoice.id),
            )
            _logger.info(
                'Updated invoice %s customer to %s.',
                invoice.name, admission.partner_id.name,
            )

    for fee in env['school.fee'].search([('invoice_id', '!=', False)]):
        expected_partner = fee.student_id.partner_id
        invoice = fee.invoice_id
        if expected_partner and invoice.partner_id != expected_partner:
            cr.execute(
                'UPDATE account_move SET partner_id = %s WHERE id = %s',
                (expected_partner.id, invoice.id),
            )
            cr.execute(
                'UPDATE account_move_line SET partner_id = %s WHERE move_id = %s',
                (expected_partner.id, invoice.id),
            )
            _logger.info(
                'Updated invoice %s customer to %s.',
                invoice.name, expected_partner.name,
            )
