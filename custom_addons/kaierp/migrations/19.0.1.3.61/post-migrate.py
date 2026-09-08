# -*- coding: utf-8 -*-
"""Convert birth_year to text and backfill age from date_of_birth."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT data_type
          FROM information_schema.columns
         WHERE table_name = 'school_student'
           AND column_name = 'birth_year'
        """
    )
    row = cr.fetchone()
    if row and row[0] != 'character varying':
        cr.execute(
            """
            ALTER TABLE school_student
            ALTER COLUMN birth_year TYPE varchar
            USING CASE
                WHEN birth_year IS NULL OR birth_year = 0 THEN NULL
                ELSE birth_year::text
            END
            """
        )

    cr.execute(
        """
        UPDATE school_student
           SET age = EXTRACT(YEAR FROM age(CURRENT_DATE, date_of_birth))::int
         WHERE date_of_birth IS NOT NULL
        """
    )
    cr.execute(
        """
        UPDATE school_admission
           SET age = EXTRACT(YEAR FROM age(CURRENT_DATE, date_of_birth))::int
         WHERE date_of_birth IS NOT NULL
        """
    )
