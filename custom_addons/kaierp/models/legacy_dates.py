# -*- coding: utf-8 -*-
from datetime import date

# SQL Server / ACAWEB empty DOB
_SENTINEL_YEAR = 1900
_MIN_PLAUSIBLE_AGE = 15
_MAX_PLAUSIBLE_AGE = 90


def is_missing_dob(dob):
    """True when ACAWEB used a placeholder instead of a real birth date."""
    if not dob:
        return True
    return dob.year <= _SENTINEL_YEAR


def age_in_years(dob, on_date=None):
    """Full years of age, or 0 when DOB is missing or not plausible for a student."""
    if is_missing_dob(dob):
        return 0
    on_date = on_date or date.today()
    years = on_date.year - dob.year - (
        (on_date.month, on_date.day) < (dob.month, dob.day)
    )
    if years < _MIN_PLAUSIBLE_AGE or years > _MAX_PLAUSIBLE_AGE:
        return 0
    return years
