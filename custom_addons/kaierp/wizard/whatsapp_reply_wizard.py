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
    conversation_html = fields.Html(
        string='Conversation',
        compute='_compute_conversation_html',
        sanitize=False,
    )
    message = fields.Text(string='Message', required=True)

    @api.depends('admission_id', 'phone')
    def _compute_applicant_name(self):
        for wiz in self:
            if wiz.admission_id:
                wiz.applicant_name = wiz.admission_id.name
            else:
                wiz.applicant_name = wiz.phone or _('Unknown contact')

    @api.depends('phone', 'admission_id')
    def _compute_conversation_html(self):
        Whatsapp = self.env['school.whatsapp.message']
        for wiz in self:
            messages = Whatsapp.browse()
            if wiz.phone:
                messages = Whatsapp.search_thread(wiz.phone)
            elif wiz.admission_id:
                messages = wiz.admission_id.whatsapp_message_ids.sorted(
                    key=lambda m: (m.create_date or fields.Datetime.now(), m.id),
                )
            wiz.conversation_html = Whatsapp._render_conversation_html(messages)

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
        # send_text raises UserError on API failure; also returns the log on success.
        log = Whatsapp.send_text(self.phone, body, admission=admission)

        if admission and log and log.state != 'failed':
            # Internal note only — do not email the applicant or followers.
            admission.message_post(
                body=Markup(
                    '<p><strong>WhatsApp sent to applicant:</strong></p><p>%s</p>'
                ) % escape(body),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

        # Open a fresh wizard so the conversation thread includes this reply.
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Conversation'),
            'res_model': 'school.whatsapp.reply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_admission_id': admission.id if admission else False,
                'default_phone': self.phone,
            },
        }
