# -*- coding: utf-8 -*-
import json
import logging

from markupsafe import Markup, escape

from odoo import http, _
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class WhatsappWebhookController(http.Controller):
    """Meta WhatsApp Cloud API webhook for verification and inbound messages."""

    @http.route(
        '/kaierp/whatsapp/webhook',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def webhook_verify(self, **kwargs):
        mode = kwargs.get('hub.mode')
        token = kwargs.get('hub.verify_token', '')
        challenge = kwargs.get('hub.challenge', '')
        expected = request.env['school.whatsapp.message'].sudo()._config(
            'kaierp.whatsapp_webhook_verify_token',
        )
        if mode == 'subscribe' and expected and token == expected:
            _logger.info('WhatsApp webhook verified successfully')
            return Response(challenge, status=200, content_type='text/plain')
        _logger.warning('WhatsApp webhook verification failed (mode=%s)', mode)
        return Response('Forbidden', status=403)

    @http.route(
        '/kaierp/whatsapp/webhook',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def webhook_receive(self, **kwargs):
        Whatsapp = request.env['school.whatsapp.message'].sudo()
        raw_body = request.httprequest.get_data()

        signature = request.httprequest.headers.get('X-Hub-Signature-256', '')
        if not Whatsapp.verify_signature(raw_body, signature):
            _logger.warning('WhatsApp webhook rejected: invalid signature')
            return Response('Invalid signature', status=403)

        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response('Bad request', status=400)

        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                self._process_status_updates(Whatsapp, value)
                self._process_inbound_messages(Whatsapp, value)

        return Response('OK', status=200, content_type='text/plain')

    def _process_status_updates(self, Whatsapp, value):
        for status in value.get('statuses', []):
            meta_id = status.get('id')
            state = status.get('status')
            if meta_id and state:
                Whatsapp.update_delivery_status(meta_id, state)

    def _process_inbound_messages(self, Whatsapp, value):
        for message in value.get('messages', []):
            if message.get('type') != 'text':
                continue
            phone = message.get('from', '')
            body = (message.get('text') or {}).get('body', '')
            meta_id = message.get('id', '')
            admission = Whatsapp.find_admission_by_phone(phone)
            log = Whatsapp.log_inbound(phone, body, meta_id, admission=admission)
            if admission:
                admission.message_post(
                    body=Markup(
                        '<p><strong>WhatsApp from applicant:</strong></p><p>%s</p>'
                    ) % escape(body),
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
            _logger.info(
                'WhatsApp inbound message %s from %s (admission=%s)',
                log.id,
                phone,
                admission.reference if admission else 'none',
            )
