# -*- coding: utf-8 -*-
from odoo import models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None):
        email_values = dict(email_values or {})
        if self.env['mail.mail']._kaierp_keep_sent_mail_logs():
            email_values['auto_delete'] = False
        return super().send_mail(
            res_id,
            force_send=force_send,
            raise_exception=raise_exception,
            email_values=email_values,
        )
