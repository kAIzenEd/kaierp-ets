# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    students = env['school.student'].search([('admission_id', '!=', False)])
    for student in students:
        copy_vals = student.admission_id._get_student_copy_vals(include_student_meta=False)
        if copy_vals:
            student.write(copy_vals)
    _logger.info(
        'Backfilled admission data onto %s student profile(s).',
        len(students),
    )
