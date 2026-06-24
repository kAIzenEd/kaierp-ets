# -*- coding: utf-8 -*-

STATE_MIGRATION = {
    'draft': 'initial_review',
    'under_review': 'initial_review',
    'interview': 'pending_exam_interview',
    'approved': 'accepted',
    'rejected': 'admission_denied',
    'waitlisted': 'pending_applicant',
    'enrolled': 'accepted',
}


def migrate_admission_workflow(env):
    """Map legacy admission states to the new workflow."""
    for old_state, new_state in STATE_MIGRATION.items():
        env.cr.execute(
            "UPDATE school_admission SET state = %s WHERE state = %s",
            (new_state, old_state),
        )
    admissions = env['school.admission'].search([])
    admissions._ensure_document_reviews()


def post_init_hook(cr, registry):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    migrate_admission_workflow(env)
