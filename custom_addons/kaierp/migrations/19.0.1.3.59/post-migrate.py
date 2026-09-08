# -*- coding: utf-8 -*-
"""Backfill admission full_name from legacy split name columns before field removal."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_name = 'school_admission'
           AND column_name IN ('first_name', 'middle_name', 'last_name', 'full_name')
        """
    )
    columns = {row[0] for row in cr.fetchall()}
    if 'full_name' not in columns or 'first_name' not in columns:
        return
    cr.execute(
        """
        UPDATE school_admission
           SET full_name = TRIM(
               CONCAT_WS(
                   ' ',
                   NULLIF(TRIM(first_name), ''),
                   NULLIF(TRIM(middle_name), ''),
                   NULLIF(TRIM(last_name), '')
               )
           )
         WHERE (full_name IS NULL OR TRIM(full_name) = '')
           AND (
               NULLIF(TRIM(first_name), '') IS NOT NULL
               OR NULLIF(TRIM(middle_name), '') IS NOT NULL
               OR NULLIF(TRIM(last_name), '') IS NOT NULL
           )
        """
    )
