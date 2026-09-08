# -*- coding: utf-8 -*-


def ensure_dashboard_layout_column(cr):
    """Create res_users.kaierp_dashboard_layout if the Python field loaded before -u."""
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = 'res_users'
           AND column_name = 'kaierp_dashboard_layout'
        """
    )
    if cr.fetchone():
        return
    cr.execute(
        "ALTER TABLE res_users ADD COLUMN IF NOT EXISTS kaierp_dashboard_layout text"
    )


def pre_init_hook(env):
    ensure_dashboard_layout_column(env.cr)


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
    admissions._ensure_applicant_partner()


def post_init_hook(env):
    migrate_admission_workflow(env)
    env['res.users'].kaierp_set_dashboard_home_for_all_school_users()
