# -*- coding: utf-8 -*-
"""Field-level visibility for school.student based on role field-access groups."""

from odoo import api, models

# XML IDs for field ACL groups (see security/school_security.xml)
G_BASIC = "kaierp.group_see_student_basic"
G_ACADEMIC = "kaierp.group_see_student_academic"
G_FULL = "kaierp.group_see_student_full"
G_FIN_CONTACT = "kaierp.group_see_student_finance_contact"
G_FEES = "kaierp.group_see_student_fees"

_BASIC = G_BASIC
_ACADEMIC = G_ACADEMIC
_FULL = G_FULL
_FIN_OR_FULL = f"{G_FIN_CONTACT},{G_FULL}"
_FEES = G_FEES

STUDENT_FIELD_GROUPS = {
    "name": _BASIC,
    "student_id": _BASIC,
    "display_name": _BASIC,
    "first_name": _FULL,
    "middle_name": _FULL,
    "last_name": _FULL,
    "title": _FULL,
    "photo": _FULL,
    "photo_filename": _FULL,
    "ata_number": _ACADEMIC,
    "admission_id": _FULL,
    "partner_id": _FIN_OR_FULL,
    "roll_number": _ACADEMIC,
    "class_id": _ACADEMIC,
    "course": _ACADEMIC,
    "study_mode": _ACADEMIC,
    "year_of_study": _ACADEMIC,
    "ets_campus_location": _ACADEMIC,
    "family_quarters": _FULL,
    "current_residence": _FULL,
    "academic_year": _ACADEMIC,
    "state": _ACADEMIC,
    "admission_date": _FULL,
    "graduation_date": _FULL,
    "whatsapp_number": _FULL,
    "date_of_birth": _FULL,
    "birth_day": _FULL,
    "birth_month": _FULL,
    "birth_year": _FULL,
    "gender": _FULL,
    "nationality": _FULL,
    "age": _FULL,
    "marital_status": _FULL,
    "plan_married_during_study": _FULL,
    "email": _FIN_OR_FULL,
    "ets_email": _FIN_OR_FULL,
    "mobile_number": _FIN_OR_FULL,
    "phone_number": _FIN_OR_FULL,
    "postal_address": _FULL,
    "state_name": _FULL,
    "zip_code": _FULL,
    "city": _FULL,
    "country_id": _FULL,
    "has_different_physical_address": _FULL,
    "physical_address": _FULL,
    "emergency_title": _FULL,
    "emergency_name": _FULL,
    "emergency_relationship": _FULL,
    "emergency_mobile": _FULL,
    "emergency_email": _FULL,
    "church_name": _FULL,
    "church_location": _FULL,
    "church_denomination": _FULL,
    "church_ministry_type": _FULL,
    "is_ordained": _FULL,
    "church_financial_support": _FULL,
    "graduated_seminary_last_two_years": _FULL,
    "working_for_organisation": _FULL,
    "personal_reference_1": _FULL,
    "personal_reference_2": _FULL,
    "personal_reference_3": _FULL,
    "class_x_year": _FULL,
    "diploma_after_class_x": _FULL,
    "class_xii_diploma_year": _FULL,
    "has_undergraduate_theology": _FULL,
    "has_undergraduate_non_theology": _FULL,
    "has_postgraduate_theology": _FULL,
    "has_postgraduate_non_theology": _FULL,
    "has_doctoral_non_theology": _FULL,
    "monthly_support_inr": _FULL,
    "monthly_support_usd": _FULL,
    "has_financial_sponsor": _FULL,
    "financial_supporter_role": _FULL,
    "financial_supporter_name": _FULL,
    "financial_supporter_relation": _FULL,
    "financial_supporter_email": _FULL,
    "financial_supporter_phone": _FULL,
    "financial_supporter_address": _FULL,
    "father_name": _FULL,
    "father_occupation": _FULL,
    "mother_name": _FULL,
    "mother_occupation": _FULL,
    "parents_born_again": _FULL,
    "parents_believers": _FULL,
    "family_postal_addresses": _FULL,
    "family_email_addresses": _FULL,
    "family_contact_details": _FULL,
    "has_children": _FULL,
    "religious_background_birth": _FULL,
    "believers_baptism": _FULL,
    "called_to_ministry": _FULL,
    "read_doctrinal_statement": _FULL,
    "agree_doctrinal_statement": _FULL,
    "currently_employed": _FULL,
    "active_christian_ministry": _FULL,
    "how_knew_seminary": _FULL,
    "blood_group": _FULL,
    "height_cm": _FULL,
    "weight_kg": _FULL,
    "allergies": _FULL,
    "chronic_illness": _FULL,
    "prolonged_medication": _FULL,
    "vision_hearing_problem": _FULL,
    "uses_tobacco": _FULL,
    "uses_intoxicants": _FULL,
    "suffers_sleeplessness": _FULL,
    "psychiatric_care_history": _FULL,
    "other_medical_problems": _FULL,
    "notes": _FULL,
    "chaplain_note_ids": _BASIC,
    "chaplain_document_ids": _BASIC,
    "field_education_note_ids": _BASIC,
    "field_education_document_ids": _BASIC,
    "enrollment_ids": _ACADEMIC,
    "enrollment_count": _ACADEMIC,
    "grade_ids": _ACADEMIC,
    "grade_count": _ACADEMIC,
    "gpa": _ACADEMIC,
    "attendance_ids": _ACADEMIC,
    "attendance_percentage": _ACADEMIC,
    "fee_ids": _FEES,
    "total_fees_due": _FEES,
}


class SchoolStudentFieldSecurity(models.Model):
    _inherit = "school.student"

    @api.model
    def _setup_complete(self):
        super()._setup_complete()
        for field_name, groups in STUDENT_FIELD_GROUPS.items():
            field = self._fields.get(field_name)
            if field is not None:
                field.groups = groups
