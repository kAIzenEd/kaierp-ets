# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model
    def set_param(self, key, value):
        if key == 'web.base.url' and value:
            value = str(value).strip()
            if self._kaierp_block_web_base_url_http_downgrade(value):
                current = self.sudo().get_param('web.base.url', '').strip()
                _logger.warning(
                    'Blocked web.base.url downgrade to HTTP (%s); keeping %s',
                    value, current or '(unset)',
                )
                return current
        return super().set_param(key, value)

    @api.model
    def _kaierp_block_web_base_url_http_downgrade(self, new_value):
        """Prevent Odoo from rewriting https public URL to http behind proxies."""
        if not str(new_value).lower().startswith('http://'):
            return False
        lock = self.sudo().get_param('kaierp.lock_web_base_url_https', 'True')
        if lock == 'False':
            return False
        current = self.sudo().get_param('web.base.url', '').strip()
        return current.lower().startswith('https://')
