# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging
import re
import urllib.error
import urllib.request

from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SchoolWhatsappMessage(models.Model):
    _name = 'school.whatsapp.message'
    _description = 'WhatsApp Message Log'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    admission_id = fields.Many2one('school.admission', string='Admission', index=True, ondelete='set null')
    direction = fields.Selection([
        ('outbound', 'Outbound'),
        ('inbound', 'Inbound'),
    ], string='Direction', required=True, default='outbound')
    phone = fields.Char(string='Phone', required=True, index=True)
    message_type = fields.Selection([
        ('template', 'Template'),
        ('text', 'Text'),
        ('status', 'Status Update'),
    ], string='Type', default='template')
    template_name = fields.Char(string='Template Name')
    body = fields.Text(string='Message Body')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
        ('received', 'Received'),
    ], string='Status', default='pending', required=True)
    meta_message_id = fields.Char(string='Meta Message ID', index=True, copy=False)
    error_message = fields.Text(string='Error')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('direction', 'phone', 'template_name', 'body', 'create_date')
    def _compute_display_name(self):
        for rec in self:
            label = rec.template_name or (rec.body[:40] + '…' if rec.body and len(rec.body) > 40 else rec.body) or rec.phone
            rec.display_name = f"[{rec.direction}] {label}"

    # ── Configuration helpers ─────────────────────────────────────

    @api.model
    def _config(self, key, default=''):
        return (self.env['ir.config_parameter'].sudo().get_param(key, default) or '').strip()

    @api.model
    def is_enabled(self):
        return self._config('kaierp.whatsapp_enabled') == 'True' and bool(
            self._config('kaierp.whatsapp_access_token')
            and self._config('kaierp.whatsapp_phone_number_id')
        )

    @api.model
    def get_webhook_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        return f'{base}/kaierp/whatsapp/webhook' if base else '/kaierp/whatsapp/webhook'

    @api.model
    def normalize_phone(self, number, country=None):
        """Return digits-only phone in international format (no + prefix for Meta API).

        Meta webhook ``from`` values already include the country code (e.g. US
        ``15635528122``, India ``919398011837``). Do not prepend the default
        country code when the number already looks international.
        """
        if not number:
            return ''
        digits = re.sub(r'\D', '', str(number))
        if not digits:
            return ''

        default_code = re.sub(
            r'\D', '', self._config('kaierp.whatsapp_default_country_code', '91'),
        )

        # E.164 (+...) or Meta-style numbers that already include country code.
        if str(number).strip().startswith('+') or len(digits) >= 11:
            return digits

        if country and country.phone_code:
            cc = str(country.phone_code)
            if digits.startswith(cc):
                return digits
            if digits.startswith('0'):
                digits = digits.lstrip('0')
            return f'{cc}{digits}'

        if default_code:
            if digits.startswith(default_code):
                return digits
            if digits.startswith('0'):
                digits = digits.lstrip('0')
            return f'{default_code}{digits}'
        return digits

    @api.model
    def phone_variants(self, phone):
        """Return alternate digit forms so we can match / display a full thread."""
        normalized = self.normalize_phone(phone)
        variants = {v for v in (phone, normalized, re.sub(r'\D', '', str(phone or ''))) if v}
        # Also include a form with default country removed if wrongly prefixed earlier.
        default_code = re.sub(
            r'\D', '', self._config('kaierp.whatsapp_default_country_code', '91'),
        )
        for value in list(variants):
            if default_code and value.startswith(default_code) and len(value) > len(default_code) + 8:
                variants.add(value[len(default_code):])
            if default_code and not value.startswith(default_code) and 8 <= len(value) <= 10:
                variants.add(f'{default_code}{value}')
        return list(variants)

    @api.model
    def search_thread(self, phone):
        """All messages for a phone number (handles historical mis-normalized values)."""
        variants = self.phone_variants(phone)
        if not variants:
            return self.browse()
        return self.search(
            [('phone', 'in', variants)],
            order='create_date asc, id asc',
        )

    @api.model
    def _render_conversation_html(self, messages):
        """Build chat-bubble HTML for a message recordset (oldest → newest)."""
        if not messages:
            return Markup(
                '<div class="o_wa_chat_empty text-muted">%s</div>'
            ) % escape(_('No messages in this conversation yet.'))

        parts = ['<div class="o_wa_chat">']
        for msg in messages:
            side = 'out' if msg.direction == 'outbound' else 'in'
            label = _('You') if side == 'out' else _('Them')
            when = fields.Datetime.context_timestamp(
                msg, msg.create_date,
            ).strftime('%d %b %Y %H:%M') if msg.create_date else ''
            body = escape(msg.body or msg.template_name or '')
            state = escape(msg.state or '')
            err = ''
            if msg.error_message:
                err = (
                    f'<div class="o_wa_chat_error">{escape(msg.error_message)}</div>'
                )
            parts.append(
                f'<div class="o_wa_chat_row o_wa_chat_row--{side}">'
                f'<div class="o_wa_chat_bubble">'
                f'<div class="o_wa_chat_meta">'
                f'<span class="o_wa_chat_who">{escape(label)}</span>'
                f'<span class="o_wa_chat_time">{escape(when)}</span>'
                f'<span class="o_wa_chat_state">{state}</span>'
                f'</div>'
                f'<div class="o_wa_chat_body">{body}</div>'
                f'{err}'
                f'</div></div>'
            )
        parts.append('</div>')
        return Markup(''.join(parts))

    @api.model
    def _graph_request(self, payload):
        token = self._config('kaierp.whatsapp_access_token')
        phone_number_id = self._config('kaierp.whatsapp_phone_number_id')
        api_version = self._config('kaierp.whatsapp_api_version', 'v21.0')
        if not token or not phone_number_id:
            raise UserError(_('WhatsApp access token and phone number ID are required.'))

        url = f'https://graph.facebook.com/{api_version}/{phone_number_id}/messages'
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')
            _logger.error('WhatsApp API error %s: %s', exc.code, body)
            try:
                err = json.loads(body)
                message = err.get('error', {}).get('message', body)
            except json.JSONDecodeError:
                message = body
            raise UserError(_('WhatsApp API error: %s') % message) from exc
        except urllib.error.URLError as exc:
            raise UserError(_('Could not reach WhatsApp API: %s') % exc.reason) from exc

    @api.model
    def verify_signature(self, raw_body, signature_header):
        secret = self._config('kaierp.whatsapp_app_secret')
        if not secret or not signature_header:
            return not secret
        if not signature_header.startswith('sha256='):
            return False
        expected = hmac.new(
            secret.encode('utf-8'),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature_header[7:], expected)

    # ── Send API ──────────────────────────────────────────────────

    @api.model
    def send_template(self, phone, template_name, body_parameters=None, admission=None):
        """Send a Meta-approved template message and log the result."""
        if not self.is_enabled():
            return False
        if not template_name:
            _logger.info('WhatsApp template not configured; skipping send to %s', phone)
            return False

        to_phone = self.normalize_phone(
            phone,
            country=admission.country_id if admission else None,
        )
        if not to_phone:
            _logger.warning('WhatsApp: invalid phone number %r', phone)
            return False

        language = self._config('kaierp.whatsapp_template_language', 'en')
        components = []
        if body_parameters:
            components.append({
                'type': 'body',
                'parameters': [{'type': 'text', 'text': str(p)} for p in body_parameters],
            })

        payload = {
            'messaging_product': 'whatsapp',
            'to': to_phone,
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {'code': language},
            },
        }
        if components:
            payload['template']['components'] = components

        log_model = self.sudo()
        log = log_model.create({
            'admission_id': admission.id if admission else False,
            'direction': 'outbound',
            'phone': to_phone,
            'message_type': 'template',
            'template_name': template_name,
            'body': '\n'.join(str(p) for p in (body_parameters or [])),
            'state': 'pending',
        })

        try:
            result = self._graph_request(payload)
            message_id = ''
            messages = result.get('messages') or []
            if messages:
                message_id = messages[0].get('id', '')
            log.write({
                'state': 'sent',
                'meta_message_id': message_id,
            })
            return log
        except UserError as exc:
            log.write({
                'state': 'failed',
                'error_message': str(exc),
            })
            _logger.warning('WhatsApp send failed for %s: %s', to_phone, exc)
            return log

    @api.model
    def send_text(self, phone, text, admission=None):
        """Send a plain text message (only works inside Meta's 24-hour session window)."""
        if not self.is_enabled():
            raise UserError(_(
                'WhatsApp is not enabled. Turn it on under kAI-ERP → Settings → WhatsApp.',
            ))
        if not text:
            raise UserError(_('Please enter a message to send.'))

        to_phone = self.normalize_phone(
            phone,
            country=admission.country_id if admission else None,
        )
        if not to_phone:
            raise UserError(_('Invalid WhatsApp phone number: %s') % (phone or _('(empty)')))

        log_model = self.sudo()
        log = log_model.create({
            'admission_id': admission.id if admission else False,
            'direction': 'outbound',
            'phone': to_phone,
            'message_type': 'text',
            'body': text,
            'state': 'pending',
        })
        payload = {
            'messaging_product': 'whatsapp',
            'to': to_phone,
            'type': 'text',
            'text': {'body': text},
        }
        try:
            result = self._graph_request(payload)
            message_id = (result.get('messages') or [{}])[0].get('id', '')
            log.write({'state': 'sent', 'meta_message_id': message_id})
            return log
        except UserError as exc:
            log.write({'state': 'failed', 'error_message': str(exc)})
            raise

    @api.model
    def log_inbound(self, phone, body, meta_message_id, admission=None):
        stored_phone = self.normalize_phone(phone) or phone
        return self.sudo().create({
            'admission_id': admission.id if admission else False,
            'direction': 'inbound',
            'phone': stored_phone,
            'message_type': 'text',
            'body': body,
            'state': 'received',
            'meta_message_id': meta_message_id,
        })

    @api.model
    def update_delivery_status(self, meta_message_id, status, errors=None):
        log = self.sudo().search([('meta_message_id', '=', meta_message_id)], limit=1)
        if not log:
            return
        state_map = {
            'sent': 'sent',
            'delivered': 'delivered',
            'read': 'read',
            'failed': 'failed',
        }
        mapped = state_map.get(status)
        vals = {}
        if mapped:
            vals['state'] = mapped
        if errors:
            parts = []
            for err in errors:
                title = err.get('title') or err.get('message') or ''
                code = err.get('code')
                detail = (err.get('error_data') or {}).get('details') or ''
                bits = [str(x) for x in (code, title, detail) if x]
                if bits:
                    parts.append(' — '.join(bits))
            if parts:
                vals['error_message'] = '; '.join(parts)
        if vals:
            log.write(vals)
            _logger.info(
                'WhatsApp status update %s → %s (%s)',
                meta_message_id, vals.get('state', log.state), vals.get('error_message', ''),
            )

    @api.model
    def find_admission_by_phone(self, phone):
        normalized = self.normalize_phone(phone)
        if not normalized:
            return self.env['school.admission']
        candidates = self.env['school.admission'].search([
            ('whatsapp_number', '!=', False),
        ], order='application_date desc')
        for admission in candidates:
            if self.normalize_phone(
                admission.whatsapp_number,
                country=admission.country_id,
            ) == normalized:
                return admission
        return self.env['school.admission']

    def action_whatsapp_reply(self):
        """Open reply wizard for this phone number (with or without a linked admission)."""
        self.ensure_one()
        if not self.phone:
            raise UserError(_('This message has no phone number.'))
        # Prefer the Meta-normalized form; avoid double-prefixing.
        reply_phone = self.normalize_phone(self.phone) or self.phone
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Conversation'),
            'res_model': 'school.whatsapp.reply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_admission_id': self.admission_id.id if self.admission_id else False,
                'default_phone': reply_phone,
            },
        }

    @api.model
    def action_test_connection(self):
        """Send a hello_world template to the configured test number."""
        test_phone = self._config('kaierp.whatsapp_test_phone')
        if not test_phone:
            raise UserError(_('Set a test phone number in kAI-ERP WhatsApp settings first.'))
        template = self._config('kaierp.whatsapp_template_test') or 'hello_world'
        log = self.send_template(test_phone, template)
        if log and log.state == 'sent':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('WhatsApp test sent'),
                    'message': _('Template "%s" sent to %s.') % (template, test_phone),
                    'type': 'success',
                    'sticky': False,
                },
            }
        raise UserError(
            _('Test message failed: %s') % (log.error_message or _('Check the WhatsApp message log.'))
        )
