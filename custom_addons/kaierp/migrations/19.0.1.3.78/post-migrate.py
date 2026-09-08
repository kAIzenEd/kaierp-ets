# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Seed Admission Registration Year to 2027 for the upcoming intake."""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    ICP = env['ir.config_parameter'].sudo()
    current = (ICP.get_param('kaierp.admission_registration_year') or '').strip()
    if not current:
        ICP.set_param('kaierp.admission_registration_year', '2027')
