# -*- coding: utf-8 -*-
from odoo import api, models


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def _kaierp_keep_sent_mail_logs(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'kaierp.mail_keep_sent_logs', 'True',
        ) != 'False'

    @api.model_create_multi
    def create(self, vals_list):
        if self._kaierp_keep_sent_mail_logs():
            for vals in vals_list:
                vals['auto_delete'] = False
        return super().create(vals_list)
