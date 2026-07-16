# -*- coding: utf-8 -*-
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
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    report = env.ref("kaierp.report_student_directory", raise_if_not_found=False)
    if not report:
        _logger.warning("Student directory report not found; skip column refresh.")
        return

    # Recompute stored birth parts for existing students
    students = env["school.student"].search([])
    if students:
        students._compute_birth_parts()

    field_recs = {
        f.name: f
        for f in env["ir.model.fields"].search(
            [("model", "=", "school.student"), ("name", "in", _DIRECTORY_FIELDS)]
        )
    }
    report.field_ids.unlink()
    lines = []
    for seq, name in enumerate(_DIRECTORY_FIELDS, start=1):
        field = field_recs.get(name)
        if field:
            lines.append((0, 0, {"field_id": field.id, "sequence": seq * 10}))
    report.write({"field_ids": lines})
    _logger.info(
        "Refreshed Student directory report with %s columns.",
        len(lines),
    )
