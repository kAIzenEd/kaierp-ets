# -*- coding: utf-8 -*-
"""Route reference-form reply emails onto school.admission when headers are stripped."""
import logging
import re

from odoo import api, models

_logger = logging.getLogger(__name__)

# Example: [ETS-REF:ID:42-R2]
ETS_REF_TOKEN_RE = re.compile(
    r'\[ETS-REF:ID:(?P<id>\d+)-R(?P<slot>[1-4])\]',
    re.IGNORECASE,
)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None,
                      custom_values=None):
        """Fall back to ETS-REF subject token when normal routing finds nothing."""
        try:
            routes = super().message_route(
                message, message_dict, model=model, thread_id=thread_id,
                custom_values=custom_values,
            )
        except ValueError as err:
            routes = self._kaierp_reference_reply_routes(
                message_dict, custom_values,
            )
            if routes:
                return routes
            raise err

        if routes:
            return routes

        return self._kaierp_reference_reply_routes(message_dict, custom_values)

    @api.model
    def _kaierp_reference_reply_routes(self, message_dict, custom_values=None):
        subject = (message_dict or {}).get('subject') or ''
        match = ETS_REF_TOKEN_RE.search(subject)
        if not match:
            return []

        admission = self.env['school.admission'].sudo().browse(
            int(match.group('id')),
        ).exists()
        if not admission:
            _logger.warning(
                'Reference reply token pointed to missing admission id=%s',
                match.group('id'),
            )
            return []

        _logger.info(
            'Routed reference reply to admission %s via subject token (slot R%s)',
            admission.display_name, match.group('slot'),
        )
        return [(
            admission._name,
            admission.id,
            custom_values or {},
            self.env.user.id,
            None,
        )]
