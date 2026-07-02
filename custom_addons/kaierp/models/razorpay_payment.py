# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SchoolRazorpayPayment(models.AbstractModel):
    _name = 'school.razorpay.payment'
    _description = 'Razorpay Payment Links API'

    @api.model
    def _config(self, key, default=''):
        return (self.env['ir.config_parameter'].sudo().get_param(key, default) or '').strip()

    @api.model
    def is_configured(self):
        return bool(self._config('kaierp.razorpay_key_id') and self._config('kaierp.razorpay_key_secret'))

    @api.model
    def get_webhook_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        return f'{base}/kaierp/razorpay/webhook' if base else '/kaierp/razorpay/webhook'

    @api.model
    def _api_request(self, method, path, payload=None):
        key_id = self._config('kaierp.razorpay_key_id')
        key_secret = self._config('kaierp.razorpay_key_secret')
        if not key_id or not key_secret:
            raise UserError(_(
                'Razorpay is not configured. Add Key ID and Key Secret under kAI-ERP Settings.',
            ))

        url = f'https://api.razorpay.com/v1{path}'
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        auth = base64.b64encode(f'{key_id}:{key_secret}'.encode()).decode()
        request_obj = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                'Authorization': f'Basic {auth}',
                'Content-Type': 'application/json',
            },
        )
        try:
            with urllib.request.urlopen(request_obj, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')
            _logger.error('Razorpay API error %s: %s', exc.code, body)
            raise UserError(_('Razorpay API error: %s') % body) from exc
        except urllib.error.URLError as exc:
            _logger.error('Razorpay connection error: %s', exc)
            raise UserError(_('Could not reach Razorpay. Check your network connection.')) from exc

    @api.model
    def create_payment_link(self, admission, amount_inr, description, reference_id):
        """Create a Razorpay Payment Link for an admission."""
        amount_paise = int(round(amount_inr * 100))
        if amount_paise <= 0:
            raise UserError(_('Payment amount must be greater than zero.'))

        admission._ensure_applicant_partner()
        contact = (
            admission.mobile_number
            or admission.whatsapp_number
            or admission.phone_number
            or ''
        )
        payload = {
            'amount': amount_paise,
            'currency': 'INR',
            'description': description,
            'reference_id': reference_id,
            'customer': {
                'name': admission.name or admission.email,
                'email': admission.email,
                'contact': contact,
            },
            'notify': {
                'email': True,
                'sms': False,
            },
            'reminder_enable': True,
            'notes': {
                'admission_id': str(admission.id),
                'payment_type': 'exam_accommodation',
                'registration_number': admission.registration_number or '',
            },
        }
        return self._api_request('POST', '/payment_links', payload)

    @api.model
    def verify_webhook_signature(self, body, signature):
        secret = self._config('kaierp.razorpay_webhook_secret')
        if not secret:
            _logger.warning('Razorpay webhook secret not configured')
            return False
        if not signature:
            return False
        digest = hmac.new(
            secret.encode('utf-8'),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(digest, signature)

    @api.model
    def process_webhook_event(self, event_name, payload):
        """Route Razorpay webhook events to the correct handler."""
        if event_name != 'payment_link.paid':
            return False

        payment_link = (
            payload.get('payment_link', {}).get('entity')
            or payload.get('payment_link')
            or {}
        )
        payment = (
            payload.get('payment', {}).get('entity')
            or payload.get('payment')
            or {}
        )
        notes = payment_link.get('notes') or {}
        admission_id = notes.get('admission_id')
        if not admission_id:
            _logger.warning('Razorpay payment_link.paid without admission_id in notes')
            return False

        admission = self.env['school.admission'].sudo().browse(int(admission_id)).exists()
        if not admission:
            _logger.warning('Razorpay payment for unknown admission %s', admission_id)
            return False

        if notes.get('payment_type') != 'exam_accommodation':
            return False

        admission._register_exam_accommodation_payment(payment_link, payment)
        return True
