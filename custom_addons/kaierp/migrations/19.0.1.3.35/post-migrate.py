# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    student_group = env.ref("kaierp.group_school_student", raise_if_not_found=False)
    internal = env.ref("base.group_user", raise_if_not_found=False)
    if not student_group or not internal:
        return

    # Old Faculty/Manager chain implied Student; strip it from internal users.
    users = env["res.users"].search([
        ("group_ids", "in", student_group.id),
        ("group_ids", "in", internal.id),
    ])
    if users:
        users.write({"group_ids": [(3, student_group.id)]})
        _logger.info(
            "Removed School Student group from %s internal user(s).",
            len(users),
        )
