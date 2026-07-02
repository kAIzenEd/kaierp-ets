# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SchoolWhatsappReplyWizard(models.TransientModel):
    _name = 'school.whatsapp.reply.wizard'
    _description = 'Send WhatsApp Reply'

    admission_id = fields.Many2one(
        'school.admission', string='Admission', readonly=True,
    )
    applicant_name = fields.Char(
        string='Contact', compute='_compute_applicant_name', readonly=True,
    )
    phone = fields.Char(string='WhatsApp Number', required=True, readonly=True)
    message = fields.Text(string='Message', required=True)

    def _compute_applicant_name(self):
        for wiz in self:
            if wiz.admission_id:
                wiz.applicant_name = wiz.admission_id.name
            else:
                wiz.applicant_name = wiz.phone or _('Unknown contact')

    def action_send(self):
        self.ensure_one()
        body = (self.message or '').strip()
        if not body:
            raise UserError(_('Please enter a message to send.'))
        if not self.phone:
            raise UserError(_('No WhatsApp number to send to.'))

        Whatsapp = self.env['school.whatsapp.message']
        if not Whatsapp.is_enabled():
            raise UserError(_(
                'WhatsApp is not enabled. Turn it on under kAI-ERP → Settings → WhatsApp.',
            ))

        admission = self.admission_id if self.admission_id else False
        log = Whatsapp.send_text(self.phone, body, admission=admission)
        if not log or log.state == 'failed':
            detail = log.error_message if log else _('Unknown error')
            raise UserError(_('WhatsApp message failed: %s') % detail)

        if admission:
            admission.message_post(
                body=Markup(
                    '<p><strong>WhatsApp sent to applicant:</strong></p><p>%s</p>'
                ) % escape(body),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
        return {'type': 'ir.actions.act_window_close'}
