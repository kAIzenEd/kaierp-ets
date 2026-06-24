# -*- coding: utf-8 -*-

def migrate(cr, version):
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'school_admission_document_review'
          AND column_name = 'status'
    """)
    if not cr.fetchone():
        return
    cr.execute("""
        UPDATE school_admission_document_review
           SET is_verified = TRUE
         WHERE status = 'ok'
    """)
    cr.execute("""
        UPDATE school_admission_document_review
           SET has_issue = TRUE
         WHERE status = 'issue'
    """)
    cr.execute("""
        ALTER TABLE school_admission_document_review DROP COLUMN IF EXISTS status
    """)
    cr.execute("""
        ALTER TABLE school_admission_document_review
        DROP COLUMN IF EXISTS verified
    """)
