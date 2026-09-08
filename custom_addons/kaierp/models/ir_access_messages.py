# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import AccessError

_ETS_ACCESS_MESSAGE = _(
    'You do not have access to this, contact your IT Admin',
)


class IrRule(models.Model):
    _inherit = 'ir.rule'

    def _make_access_error(self, operation, records):
        """Replace Odoo's informal cookie message with a clear ETS message."""
        return AccessError(_ETS_ACCESS_MESSAGE)


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    def _make_access_error(self, model, mode):
        """Replace default ACL denial text with a clear ETS message (Odoo 19)."""
        return AccessError(_ETS_ACCESS_MESSAGE)
