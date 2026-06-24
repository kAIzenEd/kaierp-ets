# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from werkzeug.exceptions import Forbidden, Unauthorized

_logger = logging.getLogger(__name__)


class AdmissionApiController(http.Controller):
    """Receive admission applications from the ETS-ACA website via Railway."""

    def _get_expected_webhook_secret(self):
        expected = request.env['ir.config_parameter'].sudo().get_param(
            'kaierp.admission_webhook_secret',
        )
        return (expected or '').strip()

    def _authenticate_as_integration_user(self):
        integration_user = request.env.ref(
            'kaierp.user_ets_website_api', raise_if_not_found=False,
        )
        if not integration_user:
            raise Forbidden('Integration user is not configured')
        request.update_env(user=integration_user.id)

    def _authenticate_request(self):
        """
        Accept either:
          - Authorization: Bearer <odoo_api_key>
          - Authorization: Bearer <webhook_secret>  (shared secret)
          - X-Webhook-Secret: <kaierp.admission_webhook_secret>
        """
        headers = request.httprequest.headers
        expected_secret = self._get_expected_webhook_secret()

        bearer = headers.get('Authorization', '')
        if bearer.lower().startswith('bearer '):
            token = bearer.split(' ', 1)[1].strip()
            uid = request.env['res.users.apikeys']._check_credentials(
                scope='rpc', key=token,
            )
            if uid:
                request.update_env(user=uid)
                return
            if expected_secret and token == expected_secret:
                self._authenticate_as_integration_user()
                return
            raise Unauthorized('Invalid API key or webhook secret')

        webhook_secret = (
            headers.get('X-Webhook-Secret')
            or headers.get('X-Kaierp-Webhook-Secret')
            or ''
        ).strip()

        if webhook_secret and expected_secret and webhook_secret == expected_secret:
            self._authenticate_as_integration_user()
            return

        _logger.warning(
            'Admission API auth failed (bearer=%s, webhook_header=%s, secret_configured=%s)',
            bool(bearer),
            bool(webhook_secret),
            bool(expected_secret),
        )
        raise Unauthorized(
            'Provide Authorization: Bearer <api_key> or X-Webhook-Secret header',
        )

    @http.route(
        '/kaierp/api/admission/submit',
        type='json2',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def submit_admission(self, **payload):
        """
        Create an admission record from a website submission.

        Headers:
          X-Odoo-Database: odoo_ets
          Content-Type: application/json
          Authorization: Bearer <odoo_api_key>
            OR
          X-Webhook-Secret: <value of kaierp.admission_webhook_secret>

        Body: JSON object with admission fields (see admission_website.py aliases).
        """
        self._authenticate_request()
        correlation_id = payload.get('correlationId')
        _logger.info(
            'Admission API request correlationId=%s keys=%s',
            correlation_id,
            sorted(payload.keys()) if isinstance(payload, dict) else type(payload),
        )
        try:
            result = request.env['school.admission'].create_from_website_payload(payload)
            _logger.info(
                'Admission API success correlationId=%s referenceId=%s',
                result.get('correlationId'),
                result.get('referenceId'),
            )
            return result
        except ValidationError as exc:
            _logger.warning(
                'Admission API validation failed correlationId=%s error=%s',
                correlation_id,
                exc,
            )
            raise
        except Exception as exc:
            _logger.exception(
                'Admission API submission failed correlationId=%s',
                correlation_id,
            )
            return {
                'ok': False,
                'error': str(exc),
                'correlationId': correlation_id,
            }

    @http.route(
        '/kaierp/api/admission/health',
        type='json2',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
        save_session=False,
    )
    def health_check(self):
        """Simple connectivity check for Railway / ngrok."""
        return {'ok': True, 'service': 'kaierp-admission-api'}
