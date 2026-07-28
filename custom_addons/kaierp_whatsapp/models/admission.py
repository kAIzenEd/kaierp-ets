# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SchoolAdmissionWhatsapp(models.Model):
    _inherit = 'school.admission'

    # Defined here so clients whose kaierp lacks this column still install.
    # Keep optional at model level; ETS can still require it in their form view.
    whatsapp_number = fields.Char(
        string='WhatsApp Number',
        help='Applicant phone for WhatsApp templates and conversation threads.',
    )
    whatsapp_message_ids = fields.One2many(
        'school.whatsapp.message', 'admission_id', string='WhatsApp Messages',
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._send_whatsapp_for_trigger('on_create')
        return records

    def write(self, vals):
        track_state = 'state' in vals
        old_states = {rec.id: rec.state for rec in self} if track_state else {}
        result = super().write(vals)
        if track_state:
            for rec in self:
                previous = old_states.get(rec.id)
                if previous and previous != rec.state:
                    rec._send_whatsapp_for_trigger('on_state', state=rec.state)
        return result

    def _whatsapp_phone(self):
        """Best available phone for WhatsApp (field may be empty on some clients)."""
        self.ensure_one()
        return (
            (self.whatsapp_number or '').strip()
            or (getattr(self, 'mobile_number', None) or '')
            or (getattr(self, 'phone_number', None) or '')
            or (getattr(self, 'phone', None) or '')
            or (getattr(self, 'mobile', None) or '')
        )

    def _send_whatsapp_for_trigger(self, trigger, state=None):
        """Send WhatsApp templates matching configured event rules."""
        if 'school.whatsapp.message' not in self.env:
            return
        if 'school.whatsapp.event.rule' not in self.env:
            return
        Whatsapp = self.env['school.whatsapp.message']
        if not Whatsapp.is_enabled():
            return

        Rule = self.env['school.whatsapp.event.rule']
        rules = Rule.find_rules(trigger, state=state)
        if not rules:
            return

        for admission in self:
            phone = admission._whatsapp_phone()
            if not phone:
                continue
            for rule in rules:
                template_name = (rule.template_name or '').strip()
                if not template_name:
                    continue
                Whatsapp.send_template(
                    phone,
                    template_name,
                    body_parameters=rule.resolve_body_parameters(admission),
                    admission=admission,
                )

    def action_whatsapp_open_conversation(self):
        """Open the WhatsApp conversation thread for this applicant."""
        self.ensure_one()
        phone = self._whatsapp_phone()
        if not phone and self.whatsapp_message_ids:
            phone = self.whatsapp_message_ids[0].phone
        if not phone:
            raise ValidationError(_('This application has no WhatsApp number.'))
        Whatsapp = self.env['school.whatsapp.message']
        country = getattr(self, 'country_id', False)
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Conversation'),
            'res_model': 'school.whatsapp.reply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_admission_id': self.id,
                'default_phone': Whatsapp.normalize_phone(
                    phone, country=country,
                ) or phone,
            },
        }
