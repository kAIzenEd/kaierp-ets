# -*- coding: utf-8 -*-
import json
import logging
import urllib.error
import urllib.request

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


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
    document_upload_token_days = fields.Integer(
        string='Document Upload Link Validity (days)',
        config_parameter='kaierp.document_upload_token_days',
        default=14,
        help='How long the applicant secure upload link remains valid (1–90 days).',
    )

    # ── WhatsApp / Meta Cloud API ─────────────────────────────────
    whatsapp_enabled = fields.Boolean(
        string='Enable WhatsApp Notifications',
        config_parameter='kaierp.whatsapp_enabled',
    )
    whatsapp_access_token = fields.Char(
        string='WhatsApp Access Token',
        config_parameter='kaierp.whatsapp_access_token',
    )
    whatsapp_phone_number_id = fields.Char(
        string='Phone Number ID',
        config_parameter='kaierp.whatsapp_phone_number_id',
    )
    whatsapp_phone_display = fields.Char(
        string='Resolved WhatsApp Number',
        compute='_compute_whatsapp_phone_display',
        help='Live number Meta associates with the Phone Number ID above.',
    )
    whatsapp_app_secret = fields.Char(
        string='App Secret',
        config_parameter='kaierp.whatsapp_app_secret',
    )
    whatsapp_webhook_verify_token = fields.Char(
        string='Webhook Verify Token',
        config_parameter='kaierp.whatsapp_webhook_verify_token',
    )
    whatsapp_api_version = fields.Char(
        string='Graph API Version',
        config_parameter='kaierp.whatsapp_api_version',
        default='v21.0',
    )
    whatsapp_default_country_code = fields.Char(
        string='Default Country Code',
        config_parameter='kaierp.whatsapp_default_country_code',
        default='91',
        help='Used when applicant numbers omit + prefix (digits only, e.g. 91 for India).',
    )
    whatsapp_template_language = fields.Char(
        string='Template Language Code',
        config_parameter='kaierp.whatsapp_template_language',
        default='en',
    )
    whatsapp_test_phone = fields.Char(
        string='Test Phone Number',
        config_parameter='kaierp.whatsapp_test_phone',
        help='Number to use when clicking "Send Test Message" (with country code).',
    )
    whatsapp_template_test = fields.Char(
        string='Test Template Name',
        config_parameter='kaierp.whatsapp_template_test',
        default='hello_world',
    )
    whatsapp_template_received = fields.Char(
        string='Application Received Template',
        config_parameter='kaierp.whatsapp_template_received',
        help='Meta template name. Body vars: {{1}} name, {{2}} reference, {{3}} course.',
    )
    whatsapp_template_pending_applicant = fields.Char(
        string='Pending Applicant Response Template',
        config_parameter='kaierp.whatsapp_template_pending_applicant',
        help='Body vars: {{1}} name, {{2}} reference.',
    )
    whatsapp_template_exam_interview = fields.Char(
        string='Exam & Interview Template',
        config_parameter='kaierp.whatsapp_template_exam_interview',
        help='Body vars: {{1}} name, {{2}} reference.',
    )
    whatsapp_template_accepted = fields.Char(
        string='Admission Accepted Template',
        config_parameter='kaierp.whatsapp_template_accepted',
        help='Body vars: {{1}} name, {{2}} course.',
    )
    whatsapp_template_denied = fields.Char(
        string='Admission Denied Template',
        config_parameter='kaierp.whatsapp_template_denied',
        help='Body vars: {{1}} name, {{2}} reference.',
    )
    whatsapp_webhook_url = fields.Char(
        compute='_compute_whatsapp_webhook_url',
        string='Webhook Callback URL',
    )

    # ── Razorpay (Payment Links) ────────────────────────────────
    razorpay_key_id = fields.Char(
        string='Razorpay Key ID',
        config_parameter='kaierp.razorpay_key_id',
    )
    razorpay_key_secret = fields.Char(
        string='Razorpay Key Secret',
        config_parameter='kaierp.razorpay_key_secret',
    )
    razorpay_webhook_secret = fields.Char(
        string='Razorpay Webhook Secret',
        config_parameter='kaierp.razorpay_webhook_secret',
        help='From Razorpay Dashboard → Webhooks. Used to verify payment_link.paid events.',
    )
    razorpay_webhook_url = fields.Char(
        compute='_compute_razorpay_webhook_url',
        string='Razorpay Webhook URL',
    )

    @api.depends()
    def _compute_razorpay_webhook_url(self):
        url = self.env['school.razorpay.payment'].get_webhook_url()
        for rec in self:
            rec.razorpay_webhook_url = url

    @api.depends()
    def _compute_whatsapp_webhook_url(self):
        Whatsapp = self.env['school.whatsapp.message']
        url = Whatsapp.get_webhook_url()
        for rec in self:
            rec.whatsapp_webhook_url = url

    @api.depends('whatsapp_phone_number_id', 'whatsapp_access_token', 'whatsapp_api_version')
    def _compute_whatsapp_phone_display(self):
        for rec in self:
            rec.whatsapp_phone_display = rec._lookup_whatsapp_phone_label(
                rec.whatsapp_phone_number_id,
                rec.whatsapp_access_token,
                rec.whatsapp_api_version,
            )

    @api.model
    def _lookup_whatsapp_phone_label(self, phone_number_id, token, api_version):
        phone_number_id = (phone_number_id or '').strip()
        token = (token or '').strip()
        if not phone_number_id:
            return _('Enter a Phone Number ID to verify.')
        if not token:
            return _('Save an access token to verify this Phone Number ID.')
        version = (api_version or 'v25.0').strip() or 'v25.0'
        url = (
            f'https://graph.facebook.com/{version}/{phone_number_id}'
            f'?fields=display_phone_number,verified_name'
        )
        req = urllib.request.Request(
            url, headers={'Authorization': f'Bearer {token}'},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
            display = data.get('display_phone_number') or _('(unknown number)')
            name = data.get('verified_name') or ''
            return f'{display} — {name}'.strip(' —') if name else display
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')
            _logger.warning('WhatsApp phone lookup failed %s: %s', phone_number_id, body)
            return _('Could not verify Phone Number ID (HTTP %s). Check the ID and token.') % exc.code
        except Exception as exc:
            _logger.warning('WhatsApp phone lookup error: %s', exc)
            return _('Could not verify Phone Number ID: %s') % exc

    def set_values(self):
        """Force-persist WhatsApp secrets even if the settings UI omits empty password fields."""
        super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        for rec in self:
            if rec.whatsapp_phone_number_id:
                ICP.set_param(
                    'kaierp.whatsapp_phone_number_id',
                    rec.whatsapp_phone_number_id.strip(),
                )
            if rec.whatsapp_access_token:
                ICP.set_param(
                    'kaierp.whatsapp_access_token',
                    rec.whatsapp_access_token.strip(),
                )
            if rec.whatsapp_app_secret:
                ICP.set_param(
                    'kaierp.whatsapp_app_secret',
                    rec.whatsapp_app_secret.strip(),
                )

    def action_whatsapp_test_connection(self):
        self.ensure_one()
        return self.env['school.whatsapp.message'].action_test_connection()
