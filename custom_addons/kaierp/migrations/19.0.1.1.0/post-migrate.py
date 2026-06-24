# -*- coding: utf-8 -*-

def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.kaierp.hooks import migrate_admission_workflow
    migrate_admission_workflow(env)
