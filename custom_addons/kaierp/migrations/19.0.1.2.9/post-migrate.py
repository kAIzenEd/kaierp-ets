# -*- coding: utf-8 -*-

def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Student = env['school.student']
    Admission = env['school.admission']

    for student in Student.search([('admission_id', '=', False)]):
        admission = Admission.search([('student_id', '=', student.id)], limit=1)
        if not admission:
            continue
        copy_vals = {
            field: admission[field]
            for field in admission._student_copy_field_names()
            if field in Student._fields and not student[field]
        }
        copy_vals['admission_id'] = admission.id
        if not student.student_id and admission.registration_number:
            copy_vals['student_id'] = admission.registration_number
        if copy_vals:
            student.write(copy_vals)
