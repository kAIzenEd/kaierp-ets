# -*- coding: utf-8 -*-
"""Ensure Faculty never implies the portal Student group.

A stale implication made Manager/admin inherit the portal own-record rule,
so Student directory (and All Students) returned 0 rows for those users.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM res_groups_implied_rel
        WHERE gid IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'kaierp' AND name = 'group_school_teacher'
              AND model = 'res.groups'
        )
        AND hid IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'kaierp' AND name = 'group_school_student'
              AND model = 'res.groups'
        )
        """
    )
    if cr.rowcount:
        _logger.info(
            "Removed stale Faculty → Student group implication (%s row(s)).",
            cr.rowcount,
        )
