# -*- coding: utf-8 -*-
import base64
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SchoolAdmissionWebsite(models.Model):
    _inherit = 'school.admission'

    # Maps website / Railway payload keys → Odoo field names
    _PAYLOAD_FIELD_ALIASES = {
        'submission_id': 'website_submission_id',
        'website_submission_id': 'website_submission_id',
        'course': 'course',
        'applied_term': 'applied_term',
        'term': 'applied_term',
        'study_mode': 'study_mode',
        'title': 'title',
        'first_name': 'first_name',
        'middle_name': 'middle_name',
        'last_name': 'last_name',
        'whatsapp_number': 'whatsapp_number',
        'whatsapp': 'whatsapp_number',
        'date_of_birth': 'date_of_birth',
        'dob': 'date_of_birth',
        'gender': 'gender',
        'nationality': 'nationality',
        'age': 'age',
        'marital_status': 'marital_status',
        'mother_tongue': 'mother_tongue',
        'plan_married_during_study': 'plan_married_during_study',
        'agree_inform_marital_status': 'agree_inform_marital_status',
        'bring_family': 'bring_family',
        'email': 'email',
        'mobile_number': 'mobile_number',
        'mobile': 'mobile_number',
        'phone_number': 'phone_number',
        'phone': 'phone_number',
        'postal_address': 'postal_address',
        'address': 'postal_address',
        'state_name': 'state_name',
        'state': 'state_name',
        'zip_code': 'zip_code',
        'zip': 'zip_code',
        'postal_code': 'zip_code',
        'city': 'city',
        'country': 'country_id',
        'country_id': 'country_id',
        'has_different_physical_address': 'has_different_physical_address',
        'physical_address': 'physical_address',
        'physical_city': 'physical_city',
        'physical_zip': 'physical_zip',
        'physical_country_id': 'physical_country_id',
        'emergency_title': 'emergency_title',
        'emergency_name': 'emergency_name',
        'emergency_relationship': 'emergency_relationship',
        'emergency_mobile': 'emergency_mobile',
        'church_name': 'church_name',
        'church_location': 'church_location',
        'church_denomination': 'church_denomination',
        'church_ministry_type': 'church_ministry_type',
        'is_ordained': 'is_ordained',
        'church_financial_support': 'church_financial_support',
        'graduated_seminary_last_two_years': 'graduated_seminary_last_two_years',
        'working_for_organisation': 'working_for_organisation',
        'personal_reference_1': 'personal_reference_1',
        'personal_reference_2': 'personal_reference_2',
        'personal_reference_3': 'personal_reference_3',
        'reference1': 'personal_reference_1',
        'reference2': 'personal_reference_2',
        'reference3': 'personal_reference_3',
        'applicant_type': 'applicant_type',
        'marksheet_name': 'marksheet_name',
        'indian_state': 'indian_state',
        'academic_country': 'academic_country',
        'class_x_month_year': 'class_x_month_year',
        'class_x_year': 'class_x_year',
        'diploma_after_class_x': 'diploma_after_class_x',
        'diploma_subject': 'diploma_subject',
        'diploma_enroll_year': 'diploma_enroll_year',
        'diploma_complete_month_year': 'diploma_complete_month_year',
        'diploma_program_duration': 'diploma_program_duration',
        'class_xii_month_year': 'class_xii_month_year',
        'class_xii_diploma_year': 'class_xii_diploma_year',
        'ug_degree_type': 'ug_degree_type',
        'ug_theo_diploma_bible_college': 'ug_theo_diploma_bible_college',
        'ug_theo_diploma_enroll_year': 'ug_theo_diploma_enroll_year',
        'ug_theo_diploma_grad_month_year': 'ug_theo_diploma_grad_month_year',
        'ug_theo_diploma_duration': 'ug_theo_diploma_duration',
        'ug_theo_diploma_grade': 'ug_theo_diploma_grade',
        'ug_theo_bth_bible_college': 'ug_theo_bth_bible_college',
        'ug_theo_bth_enroll_year': 'ug_theo_bth_enroll_year',
        'ug_theo_bth_grad_month_year': 'ug_theo_bth_grad_month_year',
        'ug_theo_bth_duration': 'ug_theo_bth_duration',
        'ug_theo_bth_grade': 'ug_theo_bth_grade',
        'ug_non_theo_college': 'ug_non_theo_college',
        'ug_non_theo_university': 'ug_non_theo_university',
        'ug_non_theo_enroll_year': 'ug_non_theo_enroll_year',
        'ug_non_theo_grad_month_year': 'ug_non_theo_grad_month_year',
        'ug_non_theo_duration': 'ug_non_theo_duration',
        'ug_non_theo_grade': 'ug_non_theo_grade',
        'pg_degree_type': 'pg_degree_type',
        'pg_theo_mdiv_seminary': 'pg_theo_mdiv_seminary',
        'pg_theo_mdiv_enroll_year': 'pg_theo_mdiv_enroll_year',
        'pg_theo_mdiv_grad_month_year': 'pg_theo_mdiv_grad_month_year',
        'pg_theo_mdiv_duration': 'pg_theo_mdiv_duration',
        'pg_theo_mdiv_grade': 'pg_theo_mdiv_grade',
        'pg_non_theo_masters_college': 'pg_non_theo_masters_college',
        'pg_non_theo_masters_university': 'pg_non_theo_masters_university',
        'pg_non_theo_masters_enroll_year': 'pg_non_theo_masters_enroll_year',
        'pg_non_theo_masters_grad_month_year': 'pg_non_theo_masters_grad_month_year',
        'pg_non_theo_masters_duration': 'pg_non_theo_masters_duration',
        'pg_non_theo_masters_grade': 'pg_non_theo_masters_grade',
        'pg_non_theo_doctorate_college': 'pg_non_theo_doctorate_college',
        'pg_non_theo_doctorate_university': 'pg_non_theo_doctorate_university',
        'pg_non_theo_doctorate_enroll_year': 'pg_non_theo_doctorate_enroll_year',
        'pg_non_theo_doctorate_grad_month_year': 'pg_non_theo_doctorate_grad_month_year',
        'pg_non_theo_doctorate_duration': 'pg_non_theo_doctorate_duration',
        'pg_non_theo_doctorate_grade': 'pg_non_theo_doctorate_grade',
        'has_undergraduate_theology': 'has_undergraduate_theology',
        'has_undergraduate_non_theology': 'has_undergraduate_non_theology',
        'has_postgraduate_theology': 'has_postgraduate_theology',
        'has_postgraduate_non_theology': 'has_postgraduate_non_theology',
        'has_doctoral_non_theology': 'has_doctoral_non_theology',
        'monthly_support_inr': 'monthly_support_inr',
        'monthly_support_usd': 'monthly_support_usd',
        'has_financial_sponsor': 'has_financial_sponsor',
        'financial_supporter_role': 'financial_supporter_role',
        'financial_supporter_name': 'financial_supporter_name',
        'financial_supporter_relation': 'financial_supporter_relation',
        'financial_supporter_email': 'financial_supporter_email',
        'financial_supporter_phone': 'financial_supporter_phone',
        'financial_supporter_address': 'financial_supporter_address',
        'father_name': 'father_name',
        'father_occupation': 'father_occupation',
        'mother_name': 'mother_name',
        'mother_occupation': 'mother_occupation',
        'parents_born_again': 'parents_born_again',
        'parents_believers': 'parents_believers',
        'family_postal_addresses': 'family_postal_addresses',
        'family_email_addresses': 'family_email_addresses',
        'family_contact_details': 'family_contact_details',
        'has_children': 'has_children',
        'children_count': 'children_count',
        'children_names': 'children_names',
        'children_ages': 'children_ages',
        'children_genders': 'children_genders',
        'children_at_aca': 'children_at_aca',
        'child1_class': 'child1_class',
        'child2_class': 'child2_class',
        'child3_class': 'child3_class',
        'spouse_name': 'spouse_name',
        'spouse_dob': 'spouse_dob',
        'spouse_nationality': 'spouse_nationality',
        'spouse_state': 'spouse_state',
        'spouse_occupation': 'spouse_occupation',
        'spouse_place_of_work': 'spouse_place_of_work',
        'spouse_mother_tongue': 'spouse_mother_tongue',
        'spouse_qualification': 'spouse_qualification',
        'spouse_supportive': 'spouse_supportive',
        'spouse_applying_ets': 'spouse_applying_ets',
        'family_accommodation': 'family_accommodation',
        'religious_background_birth': 'religious_background_birth',
        'believers_baptism': 'believers_baptism',
        'called_to_ministry': 'called_to_ministry',
        'read_doctrinal_statement': 'read_doctrinal_statement',
        'agree_doctrinal_statement': 'agree_doctrinal_statement',
        'currently_employed': 'currently_employed',
        'active_christian_ministry': 'active_christian_ministry',
        'how_knew_seminary': 'how_knew_seminary',
        'blood_group': 'blood_group',
        'height_cm': 'height_cm',
        'weight_kg': 'weight_kg',
        'allergies': 'allergies',
        'chronic_illness': 'chronic_illness',
        'prolonged_medication': 'prolonged_medication',
        'vision_hearing_problem': 'vision_hearing_problem',
        'uses_tobacco': 'uses_tobacco',
        'uses_intoxicants': 'uses_intoxicants',
        'suffers_sleeplessness': 'suffers_sleeplessness',
        'psychiatric_care_history': 'psychiatric_care_history',
        'other_medical_problems': 'other_medical_problems',
        'self_declaration_agreed': 'self_declaration_agreed',
        # Railway / ACA ERPNext gateway (camelCase)
        'correlationId': 'website_submission_id',
        'firstName': 'first_name',
        'lastName': 'last_name',
        'middleName': 'middle_name',
        'dateOfBirth': 'date_of_birth',
        'appliedProgram': 'course',
        'appliedTerm': 'applied_term',
        'studyMode': 'study_mode',
        'addressLine1': 'postal_address',
        'whatsappNumber': 'whatsapp_number',
        'phoneLandline': 'phone_number',
        'stateProvince': 'state_name',
        'postalCode': 'zip_code',
        'hasDifferentPhysicalAddress': 'has_different_physical_address',
        'physicalAddressLine1': 'physical_address',
        'physicalCity': 'physical_city',
        'physicalPostalCode': 'physical_zip',
        'physicalCountry': 'physical_country_id',
        'emergencyContactTitle': 'emergency_title',
        'emergencyContactName': 'emergency_name',
        'emergencyContactRelationship': 'emergency_relationship',
        'emergencyContactMobile': 'emergency_mobile',
        'planToMarryDuringStudy': 'plan_married_during_study',
        'agreeInformMarital': 'agree_inform_marital_status',
        'bringFamily': 'bring_family',
        'recentSeminaryGraduate': 'graduated_seminary_last_two_years',
        'currentlyWorkingForOrg': 'working_for_organisation',
        'classXYear': 'class_x_year',
        'classXMonthYear': 'class_x_month_year',
        'diplomaAfterClassX': 'diploma_after_class_x',
        'diplomaSubject': 'diploma_subject',
        'diplomaEnrollYear': 'diploma_enroll_year',
        'diplomaCompleteMonthYear': 'diploma_complete_month_year',
        'diplomaProgramDuration': 'diploma_program_duration',
        'classXiiOrDiplomaYear': 'class_xii_diploma_year',
        'classXIIMonthYear': 'class_xii_month_year',
        'indianState': 'indian_state',
        'academicCountry': 'academic_country',
        'ugDegreeType': 'ug_degree_type',
        'ugTheoDiplomaBibleCollege': 'ug_theo_diploma_bible_college',
        'ugTheoDiplomaEnrollYear': 'ug_theo_diploma_enroll_year',
        'ugTheoDiplomaGradMonthYear': 'ug_theo_diploma_grad_month_year',
        'ugTheoDiplomaDuration': 'ug_theo_diploma_duration',
        'ugTheoDiplomaGrade': 'ug_theo_diploma_grade',
        'ugTheoBThBibleCollege': 'ug_theo_bth_bible_college',
        'ugTheoBThEnrollYear': 'ug_theo_bth_enroll_year',
        'ugTheoBThGradMonthYear': 'ug_theo_bth_grad_month_year',
        'ugTheoBThDuration': 'ug_theo_bth_duration',
        'ugTheoBThGrade': 'ug_theo_bth_grade',
        'ugNonTheoCollege': 'ug_non_theo_college',
        'ugNonTheoUniversity': 'ug_non_theo_university',
        'ugNonTheoEnrollYear': 'ug_non_theo_enroll_year',
        'ugNonTheoGradMonthYear': 'ug_non_theo_grad_month_year',
        'ugNonTheoDuration': 'ug_non_theo_duration',
        'ugNonTheoGrade': 'ug_non_theo_grade',
        'pgDegreeType': 'pg_degree_type',
        'pgTheoMDivSeminary': 'pg_theo_mdiv_seminary',
        'pgTheoMDivEnrollYear': 'pg_theo_mdiv_enroll_year',
        'pgTheoMDivGradMonthYear': 'pg_theo_mdiv_grad_month_year',
        'pgTheoMDivDuration': 'pg_theo_mdiv_duration',
        'pgTheoMDivGrade': 'pg_theo_mdiv_grade',
        'pgNonTheoMastersCollege': 'pg_non_theo_masters_college',
        'pgNonTheoMastersUniversity': 'pg_non_theo_masters_university',
        'pgNonTheoMastersEnrollYear': 'pg_non_theo_masters_enroll_year',
        'pgNonTheoMastersGradMonthYear': 'pg_non_theo_masters_grad_month_year',
        'pgNonTheoMastersDuration': 'pg_non_theo_masters_duration',
        'pgNonTheoMastersGrade': 'pg_non_theo_masters_grade',
        'pgNonTheoDoctorateCollege': 'pg_non_theo_doctorate_college',
        'pgNonTheoDoctorateUniversity': 'pg_non_theo_doctorate_university',
        'pgNonTheoDoctorateEnrollYear': 'pg_non_theo_doctorate_enroll_year',
        'pgNonTheoDoctorateGradMonthYear': 'pg_non_theo_doctorate_grad_month_year',
        'pgNonTheoDoctorateDuration': 'pg_non_theo_doctorate_duration',
        'pgNonTheoDoctorateGrade': 'pg_non_theo_doctorate_grade',
        'hasUgTheology': 'has_undergraduate_theology',
        'hasUgNonTheology': 'has_undergraduate_non_theology',
        'hasPgTheology': 'has_postgraduate_theology',
        'hasPgNonTheology': 'has_postgraduate_non_theology',
        'hasDoctoralNonTheology': 'has_doctoral_non_theology',
        'monthlyFinancialSupport': 'monthly_support_inr',
        'hasSponsor': 'has_financial_sponsor',
        'financialSupporterRelationship': 'financial_supporter_relation',
        'religionAtBirth': 'religious_background_birth',
        'readDoctrinalStatement': 'read_doctrinal_statement',
        'agreeDoctrinalStatement': 'agree_doctrinal_statement',
        'howHeardOfSeminary': 'how_knew_seminary',
        'christianMinistryExperience': 'active_christian_ministry',
        'selfDeclarationAccepted': 'self_declaration_agreed',
        'visionHearingProblem': 'vision_hearing_problem',
        'psychiatricCare': 'psychiatric_care_history',
        'sleeplessness': 'suffers_sleeplessness',
        # Personal & contact (camelCase)
        'mobileNumber': 'mobile_number',
        'maritalStatus': 'marital_status',
        'motherTongue': 'mother_tongue',
        # Church (camelCase)
        'churchName': 'church_name',
        'churchLocation': 'church_location',
        'churchDenomination': 'church_denomination',
        'churchMinistryType': 'church_ministry_type',
        'isOrdained': 'is_ordained',
        'churchFinancialSupport': 'church_financial_support',
        # Academic (camelCase)
        'applicantType': 'applicant_type',
        # Financial (camelCase)
        'financialSupporterName': 'financial_supporter_name',
        'financialSupporterEmail': 'financial_supporter_email',
        'financialSupporterPhone': 'financial_supporter_phone',
        'financialSupporterAddress': 'financial_supporter_address',
        # Family (camelCase)
        'fatherName': 'father_name',
        'fatherOccupation': 'father_occupation',
        'motherName': 'mother_name',
        'motherOccupation': 'mother_occupation',
        'parentsBornAgain': 'parents_born_again',
        'familyPostalAddresses': 'family_postal_addresses',
        'familyEmailAddresses': 'family_email_addresses',
        'familyContactDetails': 'family_contact_details',
        'hasChildren': 'has_children',
        'childrenCount': 'children_count',
        'childrenNames': 'children_names',
        'childrenAges': 'children_ages',
        'childrenGenders': 'children_genders',
        'childrenAtACA': 'children_at_aca',
        'child1Class': 'child1_class',
        'child2Class': 'child2_class',
        'child3Class': 'child3_class',
        'personalReference1': 'personal_reference_1',
        'personalReference2': 'personal_reference_2',
        'personalReference3': 'personal_reference_3',
        'spouseName': 'spouse_name',
        'spouseDob': 'spouse_dob',
        'spouseNationality': 'spouse_nationality',
        'spouseState': 'spouse_state',
        'spouseOccupation': 'spouse_occupation',
        'spousePlaceOfWork': 'spouse_place_of_work',
        'spouseMotherTongue': 'spouse_mother_tongue',
        'spouseQualification': 'spouse_qualification',
        'spouseSupportive': 'spouse_supportive',
        'spouseApplyingETS': 'spouse_applying_ets',
        'familyAccommodation': 'family_accommodation',
        # Spiritual & work (camelCase)
        'believersBaptism': 'believers_baptism',
        'calledToMinistry': 'called_to_ministry',
        'currentlyEmployed': 'currently_employed',
        # Health (camelCase)
        'bloodGroup': 'blood_group',
        'heightCm': 'height_cm',
        'weightKg': 'weight_kg',
        'chronicIllness': 'chronic_illness',
        'prolongedMedication': 'prolonged_medication',
        'usesTobacco': 'uses_tobacco',
        'usesIntoxicants': 'uses_intoxicants',
        'otherMedicalProblems': 'other_medical_problems',
        # Application fee / Razorpay (camelCase from ACA ERPNext website)
        'applicationFeePaid': 'application_fee_paid',
        'paymentSuccessful': 'payment_successful',
        'paymentProvider': 'payment_provider',
        'paymentId': 'payment_id',
        'paymentOrderId': 'payment_order_id',
        'paymentReceipt': 'payment_receipt',
        'paymentStatus': 'payment_status',
        'paymentMethod': 'payment_method',
        'paymentAmount': 'payment_amount',
        'paymentAmountPaise': 'payment_amount_paise',
        'paymentCurrency': 'payment_currency',
    }

    _DOCUMENT_FIELD_ALIASES = {
        'photo': 'photo',
        'aadhaar': 'doc_aadhaar',
        'passport': 'doc_passport',
        'passport_pages': 'doc_passport',
        'visa': 'doc_visa',
        'valid_visa': 'doc_visa',
        'change_of_name': 'doc_change_of_name',
        'marriage_certificate': 'doc_marriage_certificate',
        'church_recommendation': 'doc_church_recommendation',
        'church_recommendation_letter': 'doc_church_recommendation',
        'reference_form_1': 'doc_reference_form_1',
        'reference_form_2': 'doc_reference_form_2',
        'reference_form_3': 'doc_reference_form_3',
        'reference_form_4': 'doc_reference_form_4_employer',
        'reference_form_4_employer': 'doc_reference_form_4_employer',
        'finance_assurance': 'doc_finance_assurance',
        'financial_guarantee': 'doc_financial_guarantee',
        'conduct_seminary': 'doc_conduct_seminary',
        'conduct_employer': 'doc_conduct_employer',
        'school_admission_children': 'doc_school_admission_children',
        'personal_testimony': 'doc_personal_testimony',
        'christian_ministry_experience': 'doc_christian_ministry_experience',
        'work_experience': 'doc_work_experience',
        'fitness_certificate': 'doc_fitness_certificate',
        'chronic_illness': 'doc_chronic_illness',
        'prolonged_medication': 'doc_prolonged_medication',
        'vision_hearing': 'doc_vision_hearing',
        'psychiatric_care': 'doc_psychiatric_care',
        'class_x': 'doc_class_x',
        'class_xii_diploma': 'doc_class_xii_diploma',
        'ug_degree_1_mark_sheet': 'doc_ug_degree_1_mark_sheet',
        'ug_degree_1_certificate': 'doc_ug_degree_1_certificate',
        'ug_degree_2_mark_sheet': 'doc_ug_degree_2_mark_sheet',
        'ug_degree_2_certificate': 'doc_ug_degree_2_certificate',
        'pg_degree_1_mark_sheet': 'doc_pg_degree_1_mark_sheet',
        'pg_degree_1_certificate': 'doc_pg_degree_1_certificate',
        'pg_degree_2_mark_sheet': 'doc_pg_degree_2_mark_sheet',
        'pg_degree_2_certificate': 'doc_pg_degree_2_certificate',
        'pg_diploma_mark_sheet': 'doc_pg_diploma_mark_sheet',
        'pg_diploma_certificate': 'doc_pg_diploma_certificate',
        'other_degrees': 'doc_other_degrees',
        'yet_to_graduate': 'doc_yet_to_graduate',
        'application_fee': 'doc_application_fee',
    }

    # Website form slot names (DOCUMENT_SLOTS) → Odoo binary fields
    _GATEWAY_DOCUMENT_SLOTS = {
        'doc_photo': 'photo',
        'doc_aadhaar': 'doc_aadhaar',
        'doc_passport': 'doc_passport',
        'doc_visa': 'doc_visa',
        'doc_change_of_name': 'doc_change_of_name',
        'doc_marriage_certificate': 'doc_marriage_certificate',
        'doc_church_recommendation': 'doc_church_recommendation',
        'doc_reference_1': 'doc_reference_form_1',
        'doc_reference_2': 'doc_reference_form_2',
        'doc_reference_3': 'doc_reference_form_3',
        'doc_reference_4': 'doc_reference_form_4_employer',
        'doc_finance_assurance': 'doc_finance_assurance',
        'doc_finance_guarantee': 'doc_financial_guarantee',
        'doc_conduct_seminary': 'doc_conduct_seminary',
        'doc_conduct_employer': 'doc_conduct_employer',
        'doc_school_admission': 'doc_school_admission_children',
        'doc_personal_testimony': 'doc_personal_testimony',
        'doc_christian_ministry_experience': 'doc_christian_ministry_experience',
        'doc_work_experience': 'doc_work_experience',
        'doc_fitness_certificate': 'doc_fitness_certificate',
        'doc_chronic_illness': 'doc_chronic_illness',
        'doc_prolonged_medication': 'doc_prolonged_medication',
        'doc_vision_hearing': 'doc_vision_hearing',
        'doc_psychiatric_care': 'doc_psychiatric_care',
        'doc_class_x': 'doc_class_x',
        'doc_class_xii': 'doc_class_xii_diploma',
        'doc_ug1_marks': 'doc_ug_degree_1_mark_sheet',
        'doc_ug1_certificate': 'doc_ug_degree_1_certificate',
        'doc_ug2_marks': 'doc_ug_degree_2_mark_sheet',
        'doc_ug2_certificate': 'doc_ug_degree_2_certificate',
        'doc_pg1_marks': 'doc_pg_degree_1_mark_sheet',
        'doc_pg1_certificate': 'doc_pg_degree_1_certificate',
        'doc_pg2_marks': 'doc_pg_degree_2_mark_sheet',
        'doc_pg2_certificate': 'doc_pg_degree_2_certificate',
        'doc_pg_diploma_marks': 'doc_pg_diploma_mark_sheet',
        'doc_pg_diploma_certificate': 'doc_pg_diploma_certificate',
        'doc_other_diplomas': 'doc_other_degrees',
        'doc_yet_to_graduate': 'doc_yet_to_graduate',
        'doc_pending': 'doc_yet_to_graduate',
    }

    @api.model
    def create_from_website_payload(self, payload):
        """Create or return an admission from a website JSON payload."""
        if not isinstance(payload, dict):
            raise ValidationError(_('Payload must be a JSON object.'))

        payload = self._preprocess_gateway_payload(payload)
        correlation_id = (
            payload.get('correlationId')
            or payload.get('website_submission_id')
            or payload.get('submission_id')
        )
        submission_id = payload.get('website_submission_id') or payload.get('submission_id')
        if submission_id:
            existing = self.search([
                ('website_submission_id', '=', str(submission_id)),
            ], limit=1)
            if existing:
                return self._format_api_response(
                    existing,
                    duplicate=True,
                    correlation_id=correlation_id,
                )

        extra_notes, document_list = self._extract_gateway_extras(payload)
        vals = self._map_website_payload_to_vals(payload)
        vals['state'] = 'initial_review'
        if 'self_declaration_agreed' not in vals:
            vals['self_declaration_agreed'] = True
        if extra_notes:
            vals['notes'] = extra_notes

        missing = [
            field for field in ('course', 'applied_term', 'study_mode', 'first_name',
                                'last_name', 'whatsapp_number', 'date_of_birth', 'gender',
                                'email', 'postal_address', 'city', 'country_id')
            if not vals.get(field)
        ]
        if missing:
            raise ValidationError(
                _('Missing required fields: %s') % ', '.join(missing),
            )

        admission = self.create(vals)
        documents_attached = self._attach_gateway_documents(admission, document_list)
        admission.message_post(
            body=_('Application submitted from ETS-ACA website.'),
            message_type='notification',
        )
        response = self._format_api_response(
            admission,
            duplicate=False,
            correlation_id=correlation_id,
            documents_attached=documents_attached,
        )
        return response

    @api.model
    def _format_api_response(self, admission, duplicate=False, correlation_id=None,
                             documents_attached=0):
        """Shape response for the ACA ERPNext Railway gateway."""
        reference = admission.reference
        cid = correlation_id or admission.website_submission_id
        return {
            'ok': True,
            'duplicate': duplicate,
            'created': not duplicate,
            'id': admission.id,
            'reference': reference,
            'referenceId': reference,
            'applicationId': reference,
            'correlationId': cid,
            'state': admission.state,
            'documentsAttached': documents_attached,
        }

    @api.model
    def _preprocess_gateway_payload(self, payload):
        """Normalize ACA ERPNext gateway payload before field mapping."""
        data = dict(payload)

        if data.get('correlationId') and not data.get('submission_id'):
            data['submission_id'] = data['correlationId']

        if not data.get('whatsappNumber') and not data.get('whatsapp_number'):
            phone = data.get('phone') or data.get('phoneLandline')
            if phone:
                data['whatsappNumber'] = phone

        if not data.get('appliedTerm') and not data.get('applied_term'):
            data['appliedTerm'] = '2026-SUMMER'

        for char_field in ('classXYear', 'class_x_year', 'classXiiOrDiplomaYear',
                           'class_xii_diploma_year'):
            if char_field in data and data[char_field] is not None:
                data[char_field] = str(data[char_field])

        return data

    @api.model
    def _extract_gateway_extras(self, payload):
        """Pull unmapped gateway fields into notes and document list."""
        notes_parts = []
        note_keys = (
            'priorDegreeSummary', 'statementOfPurpose',
            'chronicIllnessDetails', 'prolongedMedicationDetails',
            'visionHearingDetails', 'psychiatricCareDetails',
            'otherMedicalDetails',
        )
        for key in note_keys:
            value = payload.get(key)
            if value:
                notes_parts.append(f'<p><strong>{key}</strong></p><p>{value}</p>')

        references = payload.get('references')
        if isinstance(references, list) and references:
            lines = []
            for ref in references:
                if isinstance(ref, dict):
                    lines.append(ref.get('referenceName') or str(ref))
                else:
                    lines.append(str(ref))
            notes_parts.append(
                '<p><strong>References</strong></p><p>'
                + '<br/>'.join(lines)
                + '</p>'
            )

        document_list = payload.get('documents')
        if isinstance(document_list, dict):
            document_list = [
                {'name': name, 'content': content}
                for name, content in document_list.items()
            ]
        elif not isinstance(document_list, list):
            document_list = []

        notes_html = ''.join(notes_parts) if notes_parts else False
        return notes_html, document_list

    @api.model
    def _parse_document_slot(self, doc):
        slot = (doc.get('slot') or '').strip()
        if slot:
            return slot
        name = (doc.get('name') or '').strip()
        if '__' in name:
            return name.split('__', 1)[0]
        return name

    @api.model
    def _attach_gateway_documents(self, admission, documents):
        """Store uploads on admission binary fields and chatter attachments."""
        attached = 0
        field_vals = {}
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            content = doc.get('content')
            display_name = doc.get('name') or 'document'
            if not content:
                continue
            try:
                b64 = self._strip_base64(content)
                raw = base64.b64decode(b64)
            except Exception:
                continue

            slot = self._parse_document_slot(doc)
            field_name = self._GATEWAY_DOCUMENT_SLOTS.get(slot)
            if field_name and field_name in self._fields and field_name not in field_vals:
                field_vals[field_name] = b64

            admission.message_post(
                body=_('Uploaded document (%s): %s') % (slot or 'file', display_name),
                attachments=[(display_name, raw)],
            )
            attached += 1

        if field_vals:
            admission.write(field_vals)

        return attached

    @api.model
    def _map_website_payload_to_vals(self, payload):
        vals = {}
        flat = dict(payload)
        flat.pop('documents', None)
        flat.pop('files', None)
        flat.pop('references', None)
        for note_key in (
            'priorDegreeSummary', 'statementOfPurpose',
            'chronicIllnessDetails', 'prolongedMedicationDetails',
            'visionHearingDetails', 'psychiatricCareDetails',
            'otherMedicalDetails',
        ):
            flat.pop(note_key, None)

        for key, value in flat.items():
            if value in (None, ''):
                continue
            odoo_field = self._PAYLOAD_FIELD_ALIASES.get(key)
            if not odoo_field:
                continue
            vals[odoo_field] = self._coerce_payload_value(odoo_field, value)

        return vals

    @api.model
    def _coerce_payload_value(self, field_name, value):
        field = self._fields[field_name]

        if field_name in ('country_id', 'nationality', 'physical_country_id', 'spouse_nationality'):
            return self._resolve_country(value)

        if field_name == 'course':
            return self._normalize_course(value)
        if field_name == 'applied_term':
            return self._normalize_applied_term(value)
        if field_name == 'study_mode':
            return self._normalize_study_mode(value)
        if field_name == 'gender':
            return self._normalize_gender(value)
        if field_name in ('date_of_birth', 'spouse_dob'):
            return self._normalize_date(value)
        if field_name == 'applicant_type':
            return self._normalize_applicant_type(value)
        if field_name in ('ug_degree_type', 'pg_degree_type'):
            return self._normalize_degree_type(value)
        if field_name in ('title', 'emergency_title'):
            return self._normalize_title(value)
        if field_name == 'has_different_physical_address':
            return self._normalize_bool(value)
        if field_name == 'self_declaration_agreed':
            return self._normalize_bool(value)
        if field_name in ('application_fee_paid', 'payment_successful'):
            return self._normalize_bool(value)
        if field_name == 'payment_amount':
            return float(value)
        if field_name == 'payment_amount_paise':
            return int(value)
        if field_name in ('payment_id', 'payment_order_id', 'payment_receipt',
                          'payment_status', 'payment_method', 'payment_provider',
                          'payment_currency'):
            return str(value).strip()
        if field_name in ('height_cm', 'weight_kg'):
            return float(value)
        if field_name == 'age':
            return int(value)
        if field_name in ('class_x_year', 'class_xii_diploma_year'):
            return str(value)

        if isinstance(field, fields.Selection):
            return self._normalize_selection(field_name, value)

        return value

    @api.model
    def _resolve_country(self, value):
        Country = self.env['res.country']
        if isinstance(value, int):
            return value
        text = str(value).strip()
        if not text:
            return False
        country = Country.search([('code', '=', text.upper())], limit=1)
        if not country:
            country = Country.search([('name', '=ilike', text)], limit=1)
        if not country:
            raise ValidationError(_('Unknown country: %s') % text)
        return country.id

    @api.model
    def _normalize_course(self, value):
        text = str(value).strip().lower()
        mapping = {
            'macs': 'macs',
            'pgdbs': 'pgdbs',
            'mabs': 'mabs',
            'mdiv': 'mdiv',
            'macc': 'macc',
            'mth': 'mth',
        }
        for key, code in mapping.items():
            if key in text:
                return code
        if 'christian studies' in text:
            return 'macs'
        if 'biblical studies' in text and 'postgraduate diploma' in text:
            return 'pgdbs'
        if 'biblical studies' in text:
            return 'mabs'
        if 'divinity' in text:
            return 'mdiv'
        if 'counselling' in text or 'counseling' in text:
            return 'macc'
        if 'theology' in text:
            return 'mth'
        raise ValidationError(_('Unknown course: %s') % value)

    @api.model
    def _normalize_applied_term(self, value):
        text = str(value).strip().lower()
        # Accept 2026-SUMMER, 2026_summer, 2026 - Summer, etc.
        text = re.sub(r'[\s_\-]+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        mapping = {
            '2026 summer': '2026_summer',
            '2026 fall': '2026_fall',
            '2026 spring': '2026_spring',
            '2027 fall': '2027_fall',
        }
        if text in mapping:
            return mapping[text]
        if '2026' in text and 'summer' in text:
            return '2026_summer'
        if '2026' in text and 'spring' in text:
            return '2026_spring'
        if '2027' in text and 'fall' in text:
            return '2027_fall'
        if '2026' in text and 'fall' in text:
            return '2026_fall'
        # All incoming ETS website applicants begin Summer 2026.
        if not text:
            return '2026_summer'
        raise ValidationError(_('Unknown applied term: %s') % value)

    @api.model
    def _normalize_study_mode(self, value):
        text = str(value).strip().lower()
        if text in ('online', 'residential'):
            return text
        raise ValidationError(_('Unknown study mode: %s') % value)

    @api.model
    def _normalize_gender(self, value):
        text = str(value).strip().lower()
        if text in ('male', 'm'):
            return 'male'
        if text in ('female', 'f'):
            return 'female'
        raise ValidationError(_('Unknown gender: %s') % value)

    @api.model
    def _normalize_applicant_type(self, value):
        text = str(value).strip().lower()
        if 'indian' in text:
            return 'indian'
        if 'international' in text:
            return 'international'
        if text in ('indian', 'international'):
            return text
        raise ValidationError(_('Unknown applicant type: %s') % value)

    @api.model
    def _normalize_degree_type(self, value):
        text = str(value).strip().lower()
        if 'both' in text:
            return 'both'
        if 'non' in text and 'theo' in text:
            return 'non_theological'
        if 'theo' in text:
            return 'theological'
        if text in ('theological', 'non_theological', 'both'):
            return text
        raise ValidationError(_('Unknown degree type: %s') % value)

    @api.model
    def _normalize_title(self, value):
        text = str(value).strip().lower().replace('.', '')
        mapping = {
            'doctor': 'doctor',
            'madam': 'madam',
            'miss': 'miss',
            'mrs': 'mrs',
            'mister': 'mister',
            'mr': 'mr',
            'professor': 'professor',
        }
        if text in mapping:
            return mapping[text]
        for key, code in mapping.items():
            if key in text:
                return code
        raise ValidationError(_('Unknown title: %s') % value)

    @api.model
    def _normalize_date(self, value):
        if isinstance(value, str):
            return fields.Date.to_date(value[:10])
        return value

    @api.model
    def _normalize_bool(self, value):
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        return text in ('1', 'true', 'yes', 'y', 'on')

    @api.model
    def _normalize_selection(self, field_name, value):
        field = self._fields[field_name]
        text = str(value).strip().lower()

        yes_no_fields = {
            'plan_married_during_study', 'agree_inform_marital_status', 'bring_family',
            'is_ordained', 'church_financial_support',
            'graduated_seminary_last_two_years', 'working_for_organisation',
            'diploma_after_class_x', 'has_undergraduate_theology',
            'has_undergraduate_non_theology', 'has_postgraduate_theology',
            'has_postgraduate_non_theology', 'has_doctoral_non_theology',
            'has_financial_sponsor', 'has_children', 'children_at_aca',
            'believers_baptism', 'read_doctrinal_statement', 'currently_employed',
            'active_christian_ministry', 'chronic_illness', 'prolonged_medication',
            'vision_hearing_problem', 'uses_tobacco', 'uses_intoxicants',
            'suffers_sleeplessness', 'psychiatric_care_history', 'other_medical_problems',
            'spouse_supportive', 'spouse_applying_ets', 'family_accommodation',
        }
        if field_name in yes_no_fields:
            if text in ('yes', 'y', 'true', '1'):
                return 'yes'
            if text in ('no', 'n', 'false', '0'):
                return 'no'

        if field_name == 'called_to_ministry':
            if 'not' in text and 'sure' in text:
                return 'not_sure'
            if text in ('yes', 'y', 'true', '1'):
                return 'yes'
            if text in ('no', 'n', 'false', '0'):
                return 'no'

        if field_name == 'agree_doctrinal_statement':
            if 'agree' in text:
                return 'yes_agree'
            if 'not' in text and 'opinion' in text:
                return 'not_formed'
            if text in ('no', 'n', 'false', '0'):
                return 'no'

        valid = {key for key, _label in field.selection}
        if text in valid:
            return text
        for key, label in field.selection:
            if str(label).strip().lower() == text:
                return key
        raise ValidationError(_('Invalid value for %s: %s') % (field_name, value))

    @api.model
    def _strip_base64(self, value):
        if not isinstance(value, str):
            return value
        if ',' in value and value.startswith('data:'):
            return value.split(',', 1)[1]
        return value
