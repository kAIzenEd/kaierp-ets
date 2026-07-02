# -*- coding: utf-8 -*-

def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    Admission = env['school.admission']
    Student = env['school.student']

    issued_counters = {}
    admissions = Admission.search(
        [('registration_number', '=', False)],
        order='application_date, id',
    )
    for admission in admissions:
        if not admission.course:
            continue
        year = Admission._registration_year_from_vals({}, record=admission)
        admission.registration_number = Admission._next_registration_number(
            admission.course, year, issued_counters,
        )

    for student in Student.search([('student_id', '=', False)]):
        admission = Admission.search(
            [('student_id', '=', student.id)],
            limit=1,
        )
        if admission and admission.registration_number:
            student.student_id = admission.registration_number
