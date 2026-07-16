# -*- coding: utf-8 -*-
"""Refresh Students report-source recommended columns to the directory set."""
import logging

_logger = logging.getLogger(__name__)

_DIRECTORY_FIELDS = [
    "student_id",
    "name",
    "gender",
    "course",
    "year_of_study",
    "ets_email",
    "marital_status",
    "current_residence",
    "ets_campus_location",
    "family_quarters",
    "father_name",
    "mother_name",
    "church_denomination",
    "state_name",
    "birth_day",
    "birth_month",
    "birth_year",
    "email",
    "phone_number",
    "whatsapp_number",
    "blood_group",
    "emergency_name",
    "emergency_relationship",
    "emergency_mobile",
    "emergency_email",
    "postal_address",
]


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    source = env.ref("kaierp.report_source_students", raise_if_not_found=False)
    if not source:
        _logger.warning("Students report source missing; skip curated columns.")
        return
    fields = env["ir.model.fields"].sudo().search(
        [("model", "=", "school.student"), ("name", "in", _DIRECTORY_FIELDS)]
    )
    by_name = {field.name: field for field in fields}
    ordered_ids = [
        by_name[name].id for name in _DIRECTORY_FIELDS if name in by_name
    ]
    source.default_field_ids = [(6, 0, ordered_ids)]
    _logger.info(
        "Updated Students data source curated columns (%s fields).",
        len(ordered_ids),
    )
