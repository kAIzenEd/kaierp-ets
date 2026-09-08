# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

SETTINGS_REDIRECT = '/web#action=kaierp.action_kaierp_configuration'


class CanvasOAuthController(http.Controller):

    @http.route(
        '/kaierp/canvas/oauth/callback',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        sitemap=False,
        save_session=False,
    )
    def oauth_callback(self, **kwargs):
        icp = request.env['ir.config_parameter'].sudo()
        api = request.env['school.canvas.api'].sudo()
        error = kwargs.get('error')
        error_desc = kwargs.get('error_description') or ''
        if error:
            message = error_desc or error
            icp.set_param('kaierp.canvas_last_oauth_error', message)
            _logger.warning('Canvas OAuth denied: %s', message)
            return request.redirect(SETTINGS_REDIRECT)

        code = kwargs.get('code')
        state = kwargs.get('state')
        try:
            api.consume_oauth_state(state)
            if not code:
                raise ValueError('Canvas did not return an authorization code.')
            api.exchange_authorization_code(code)
        except Exception as err:
            icp.set_param('kaierp.canvas_last_oauth_error', str(err))
            _logger.exception('Canvas OAuth callback failed')
            return request.redirect(SETTINGS_REDIRECT)
        return request.redirect(SETTINGS_REDIRECT)
