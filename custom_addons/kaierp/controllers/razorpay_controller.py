# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class RazorpayWebhookController(http.Controller):
    """Razorpay webhook for Payment Link events."""

    @http.route(
        '/kaierp/razorpay/webhook',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def webhook_receive(self, **kwargs):
        body = request.httprequest.get_data()
        signature = request.httprequest.headers.get('X-Razorpay-Signature', '')
        Razorpay = request.env['school.razorpay.payment'].sudo()

        if not Razorpay.verify_webhook_signature(body, signature):
            _logger.warning('Razorpay webhook rejected: invalid signature')
            return Response('Invalid signature', status=403)

        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            _logger.warning('Razorpay webhook: invalid JSON body')
            return Response('Bad request', status=400)

        event_name = payload.get('event', '')
        event_payload = payload.get('payload', {})
        try:
            Razorpay.process_webhook_event(event_name, event_payload)
        except Exception:
            _logger.exception('Razorpay webhook processing failed for %s', event_name)
            return Response('Processing error', status=500)

        return Response('OK', status=200, content_type='text/plain')
