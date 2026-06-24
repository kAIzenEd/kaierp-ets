# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    admission_webhook_secret = fields.Char(
        string='Admission Webhook Secret',
        config_parameter='kaierp.admission_webhook_secret',
        help='Shared secret sent by Railway as the X-Webhook-Secret header.',
    )
    admission_registrar_email = fields.Char(
        string='Registrar Notification Email',
        config_parameter='kaierp.admission_registrar_email',
        help='Receives an email whenever a new admission application is submitted.',
    )
