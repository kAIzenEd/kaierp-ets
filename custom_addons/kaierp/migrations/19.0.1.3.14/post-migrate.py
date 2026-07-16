# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    for student in env['school.student'].search([('student_id', '!=', False)]):
        if student.partner_id:
            if not student.partner_id.school_record_ref:
                student.partner_id.school_record_ref = student.student_id

    for admission in env['school.admission'].search([('registration_number', '!=', False)]):
        admission._ensure_applicant_partner()

    for student in env['school.student'].search([('email', '!=', False)]):
        student._ensure_partner()

    _logger.info('Stamped school_record_ref on billing contacts.')
