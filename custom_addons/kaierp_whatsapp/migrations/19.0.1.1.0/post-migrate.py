# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Seed notification rules from legacy settings on upgrade to Phase 2."""
    from odoo.addons.kaierp_whatsapp.hooks import _ensure_event_rules

    env = api.Environment(cr, SUPERUSER_ID, {})
    _ensure_event_rules(env)
