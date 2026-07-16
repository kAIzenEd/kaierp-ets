# -*- coding: utf-8 -*-
"""Include photo in Students curated columns for PDF directory exports."""
import logging

_logger = logging.getLogger(__name__)

_DIRECTORY_FIELDS = [
    "photo",
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
    if source:
        fields = env["ir.model.fields"].sudo().search(
            [("model", "=", "school.student"), ("name", "in", _DIRECTORY_FIELDS)]
        )
        by_name = {field.name: field for field in fields}
        ordered_ids = [
            by_name[name].id for name in _DIRECTORY_FIELDS if name in by_name
        ]
        source.default_field_ids = [(6, 0, ordered_ids)]
        _logger.info("Students curated columns now include photo (%s).", len(ordered_ids))

    report = env.ref("kaierp.report_student_directory", raise_if_not_found=False)
    if not report:
        return
    photo = env["ir.model.fields"].sudo().search(
        [("model", "=", "school.student"), ("name", "=", "photo")], limit=1
    )
    if not photo:
        return
    existing = report.field_ids.filtered(lambda line: line.field_id.name == "photo")
    if existing:
        return
    # Insert photo as the first column for Open/list; PDF export uses selected fields.
    for line in report.field_ids:
        line.sequence = line.sequence + 10
    env["kai.view.report.field"].create(
        {
            "report_id": report.id,
            "field_id": photo.id,
            "sequence": 1,
        }
    )
    report._sync_list_view()
    _logger.info("Added photo column to Student directory saved report.")
