# -*- coding: utf-8 -*-

def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    admissions = env['school.admission'].search([('partner_id', '=', False), ('email', '!=', False)])
    admissions._ensure_applicant_partner()
