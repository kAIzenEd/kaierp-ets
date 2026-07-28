# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SchoolWhatsappEventRule(models.Model):
    """Maps admission lifecycle events to Meta WhatsApp templates.

    Clients configure their own state codes and template names here — no
    Python changes required when reusing kaierp_whatsapp on another school.
    """

    _name = 'school.whatsapp.event.rule'
    _description = 'WhatsApp Admission Event Rule'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    trigger = fields.Selection(
        [
            ('on_create', 'On application create'),
            ('on_state', 'On state change'),
        ],
        required=True,
        default='on_state',
    )
    state = fields.Char(
        string='Admission State',
        help='Technical state value on school.admission (e.g. accepted). '
             'Required when trigger is On state change.',
    )
    template_name = fields.Char(
        string='Meta Template Name',
        required=True,
        help='Exact template name approved in Meta Business Manager.',
    )
    body_param_keys = fields.Char(
        string='Body Parameters',
        help='Comma-separated tokens for {{1}}, {{2}}, … '
             'Supported: name, reference, course, state, email, phone, '
             'whatsapp_number, or any admission field name. '
             'Use selection:field_name for human-readable selection labels.',
        default='name,reference',
    )
    notes = fields.Char(
        string='Notes',
        help='Internal reminder of what the Meta template expects.',
    )

    @api.constrains('trigger', 'state')
    def _check_state_for_trigger(self):
        for rule in self:
            if rule.trigger == 'on_state' and not (rule.state or '').strip():
                raise ValidationError(_(
                    'Rule "%s": set an Admission State when trigger is '
                    'On state change.',
                ) % rule.name)

    def _param_tokens(self):
        self.ensure_one()
        raw = (self.body_param_keys or '').strip()
        if not raw:
            return []
        return [part.strip() for part in raw.split(',') if part.strip()]

    def resolve_body_parameters(self, admission):
        """Build ordered template body values from an admission record."""
        self.ensure_one()
        values = []
        for token in self._param_tokens():
            values.append(self._resolve_token(admission, token))
        return values

    @api.model
    def _resolve_token(self, admission, token):
        token = (token or '').strip()
        if not token:
            return ''

        if token.startswith('selection:'):
            field_name = token.split(':', 1)[1].strip()
            if field_name in admission._fields and hasattr(admission, 'format_selection'):
                return admission.format_selection(field_name) or ''
            return str(admission[field_name] or '') if field_name in admission._fields else ''

        # Friendly aliases used by ETS templates
        if token == 'course':
            if hasattr(admission, 'format_selection') and 'course' in admission._fields:
                return admission.format_selection('course') or ''
            return str(getattr(admission, 'course', '') or '')
        if token == 'state':
            if hasattr(admission, 'format_selection') and 'state' in admission._fields:
                return admission.format_selection('state') or ''
            return str(getattr(admission, 'state', '') or '')
        if token == 'phone':
            return (
                getattr(admission, 'whatsapp_number', None)
                or getattr(admission, 'phone', None)
                or ''
            )

        if token in admission._fields:
            value = admission[token]
            if hasattr(value, 'name'):
                return value.name or ''
            return '' if value is False or value is None else str(value)
        return ''

    @api.model
    def find_rules(self, trigger, state=None):
        domain = [('trigger', '=', trigger), ('active', '=', True)]
        if trigger == 'on_state':
            domain.append(('state', '=', state))
        return self.search(domain, order='sequence, id')
