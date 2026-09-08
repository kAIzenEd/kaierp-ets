# -*- coding: utf-8 -*-
"""Recompute ages, ignoring ACAWEB placeholder dates of birth."""


def migrate(cr, version):
    if not version:
        return
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    students = env['school.student'].search([])
    if students:
        students._compute_age()
    admissions = env['school.admission'].search([])
    if admissions:
        admissions._compute_age()
