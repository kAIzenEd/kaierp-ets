# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Grant kaisight access to existing registrar users."""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    registrar_group = env.ref("kaierp.group_school_registrar", raise_if_not_found=False)
    kaisight_group = env.ref("kaisight.group_kai_view_user", raise_if_not_found=False)
    if not registrar_group or not kaisight_group:
        return

    users = env["res.users"].search([("group_ids", "in", registrar_group.id)])
    users_to_update = users.filtered(lambda user: kaisight_group not in user.group_ids)
    if users_to_update:
        users_to_update.write({"group_ids": [(4, kaisight_group.id)]})
        _logger.info(
            "Granted kaisight User to %s registrar account(s).",
            len(users_to_update),
        )
