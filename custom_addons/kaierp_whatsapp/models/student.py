# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SchoolStudentWhatsapp(models.Model):
    _inherit = 'school.student'

    # Ensure the field exists for clients whose kaierp lacks it.
    whatsapp_number = fields.Char(
        string='WhatsApp Number',
        help='Phone number used for WhatsApp conversations with this student.',
    )
    whatsapp_message_ids = fields.One2many(
        'school.whatsapp.message', 'student_id', string='WhatsApp Messages',
    )
    whatsapp_can_message = fields.Boolean(compute='_compute_whatsapp_can_message')

    def _whatsapp_phone(self):
        self.ensure_one()
        for name in ('whatsapp_number', 'mobile_number', 'phone_number', 'phone', 'mobile'):
            if name in self._fields:
                value = self[name]
                if value:
                    return str(value).strip()
        return ''

    @api.depends('whatsapp_number', 'whatsapp_message_ids')
    def _compute_whatsapp_can_message(self):
        for rec in self:
            rec.whatsapp_can_message = bool(rec._whatsapp_phone() or rec.whatsapp_message_ids)

    def action_whatsapp_open_conversation(self):
        """Open the WhatsApp conversation thread for this student."""
        self.ensure_one()
        phone = self._whatsapp_phone()
        if not phone and self.whatsapp_message_ids:
            phone = self.whatsapp_message_ids[0].phone
        if not phone:
            raise ValidationError(_('This student has no WhatsApp number.'))
        Whatsapp = self.env['school.whatsapp.message']
        country = getattr(self, 'country_id', False)
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Conversation'),
            'res_model': 'school.whatsapp.reply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_id': self.id,
                'default_phone': Whatsapp.normalize_phone(
                    phone, country=country,
                ) or phone,
            },
        }
