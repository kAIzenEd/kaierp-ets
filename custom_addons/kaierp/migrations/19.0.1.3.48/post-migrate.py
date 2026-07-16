# -*- coding: utf-8 -*-
"""Map legacy Term 1–4 class semesters to ETS Summer/Fall/Spring."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE school_class
           SET semester = CASE semester
                WHEN '1' THEN 'summer'
                WHEN '2' THEN 'fall'
                WHEN '3' THEN 'spring'
                WHEN '4' THEN 'spring'
                ELSE semester
           END
         WHERE semester IN ('1', '2', '3', '4')
        """
    )
