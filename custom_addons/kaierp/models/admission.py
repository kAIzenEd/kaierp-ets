# -*- coding: utf-8 -*-
import base64
import secrets
from datetime import timedelta

from markupsafe import Markup, escape

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SchoolAdmission(models.Model):
    _name = 'school.admission'
    _description = 'Admission Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'application_date desc'

    # Document slots tracked for registrar review (code, label)
    ADMISSION_DOCUMENT_SLOTS = [
        ('photo', 'Photo'),
        ('doc_aadhaar', 'Aadhaar'),
        ('doc_passport', 'Passport Pages'),
        ('doc_visa', 'Valid Visa'),
        ('doc_change_of_name', 'Change of Name Affidavit'),
        ('doc_marriage_certificate', 'Marriage Certificate'),
        ('doc_church_recommendation', 'Church Recommendation Letter'),
        ('doc_reference_form_1', 'Reference Form 1'),
        ('doc_reference_form_2', 'Reference Form 2'),
        ('doc_reference_form_3', 'Reference Form 3'),
        ('doc_reference_form_4_employer', 'Reference Form 4 (Employer)'),
        ('doc_finance_assurance', 'Finance Assurance Form'),
        ('doc_financial_guarantee', 'Financial Guarantee Letter'),
        ('doc_conduct_seminary', 'Conduct Certificate (Seminary)'),
        ('doc_conduct_employer', 'Conduct Certificate (Employer)'),
        ('doc_school_admission_children', 'School Admission (Children)'),
        ('doc_personal_testimony', 'Personal Testimony'),
        ('doc_christian_ministry_experience', 'Christian Ministry Experience'),
        ('doc_work_experience', 'Work Experience'),
        ('doc_fitness_certificate', 'Fitness Certificate'),
        ('doc_chronic_illness', 'Chronic Illness Documentation'),
        ('doc_prolonged_medication', 'Prolonged Medication Documentation'),
        ('doc_vision_hearing', 'Vision/Hearing Impairment Documents'),
        ('doc_psychiatric_care', 'Psychiatric Care Documentation'),
        ('doc_class_x', 'Class X'),
        ('doc_class_xii_diploma', 'Class XII / Diploma'),
        ('doc_ug_degree_1_mark_sheet', 'UG Degree 1 Mark Sheet'),
        ('doc_ug_degree_1_certificate', 'UG Degree 1 Certificate'),
        ('doc_ug_degree_2_mark_sheet', 'UG Degree 2 Mark Sheet'),
        ('doc_ug_degree_2_certificate', 'UG Degree 2 Certificate'),
        ('doc_pg_degree_1_mark_sheet', 'PG Degree 1 Mark Sheet'),
        ('doc_pg_degree_1_certificate', 'PG Degree 1 Certificate'),
        ('doc_pg_degree_2_mark_sheet', 'PG Degree 2 Mark Sheet'),
        ('doc_pg_degree_2_certificate', 'PG Degree 2 Certificate'),
        ('doc_pg_diploma_mark_sheet', 'PG Diploma Mark Sheet'),
        ('doc_pg_diploma_certificate', 'PG Diploma Certificate'),
        ('doc_other_degrees', 'Other Diplomas/Degrees'),
        ('doc_yet_to_graduate', 'Yet-to-Graduate Pending Documents'),
    ]

    # ── Reference & integration ─────────────────────────────────
    reference = fields.Char(
        string='Application #', readonly=True, copy=False,
        default=lambda self: _('New'),
    )
    website_submission_id = fields.Char(
        string='Website Submission ID', copy=False, index=True,
        help='External reference from the ETS-ACA website form submission.',
    )
    application_date = fields.Date(
        string='Application Date', default=fields.Date.today, tracking=True,
    )
    registration_number = fields.Char(
        string='Registration #', copy=False, index=True, readonly=True,
        help='ETS registration number assigned when the application is received (e.g. 2026MDIV001).',
    )

    # ── Academic choice ───────────────────────────────────────
    course = fields.Selection([
        ('macs', 'Master of Arts in Christian Studies (MACS)'),
        ('pgdbs', 'Postgraduate Diploma in Biblical Studies (PGDBS)'),
        ('mabs', 'Master of Arts in Biblical Studies (MABS)'),
        ('mdiv', 'Master of Divinity (MDIV)'),
        ('macc', 'Master of Arts in Christian Counselling (MACC)'),
        ('mth', 'Master of Theology (MTH)'),
    ], string='Course', required=True, tracking=True)
    study_mode = fields.Selection([
        ('online', 'Online'),
        ('residential', 'Residential'),
    ], string='Study Mode', required=True, tracking=True)

    # ── Personal information ──────────────────────────────────
    title = fields.Selection([
        ('doctor', 'Doctor'),
        ('madam', 'Madam'),
        ('miss', 'Miss'),
        ('mrs', 'Mrs.'),
        ('mister', 'Mister'),
        ('mr', 'Mr'),
        ('professor', 'Professor'),
    ], string='Title')
    first_name = fields.Char(string='First Name', required=True, tracking=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name', required=True, tracking=True)
    name = fields.Char(
        string='Applicant Name', compute='_compute_name', store=True, readonly=True,
        tracking=True,
    )
    whatsapp_number = fields.Char(string='WhatsApp Number', required=True)
    date_of_birth = fields.Date(string='Date of Birth', required=True, tracking=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], required=True, tracking=True)
    nationality = fields.Many2one('res.country', string='Nationality')
    age = fields.Integer(string='Age')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('separated', 'Separated'),
        ('widowed', 'Widowed'),
    ], string='Marital Status')
    mother_tongue = fields.Char(string='Mother Tongue')
    plan_married_during_study = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string='Plan to Marry During Study Period?')
    agree_inform_marital_status = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='Agree to Inform ETS of Marital Status Changes?',
    )
    bring_family = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='Plan to Bring Family if Admitted?',
    )

    # ── Contact information ───────────────────────────────────
    email = fields.Char(string='Email', required=True, tracking=True)
    mobile_number = fields.Char(string='Mobile Number')
    phone_number = fields.Char(string='Phone Number')
    postal_address = fields.Text(string='Postal Address', required=True)
    state_name = fields.Char(string='State')
    zip_code = fields.Char(string='Zip / Postal Code')
    city = fields.Char(string='City', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    has_different_physical_address = fields.Boolean(string='Different Physical Address')
    physical_address = fields.Text(string='Physical Address')
    physical_city = fields.Char(string='Physical City')
    physical_zip = fields.Char(string='Physical Zip / Postal Code')
    physical_country_id = fields.Many2one('res.country', string='Physical Country')

    # ── Emergency contact ─────────────────────────────────────
    emergency_title = fields.Selection([
        ('doctor', 'Doctor'),
        ('madam', 'Madam'),
        ('miss', 'Miss'),
        ('mrs', 'Mrs.'),
        ('mister', 'Mister'),
        ('mr', 'Mr'),
        ('professor', 'Professor'),
    ], string='Emergency Contact Title')
    emergency_name = fields.Char(string='Emergency Contact Name')
    emergency_relationship = fields.Selection([
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('brother', 'Brother'),
        ('sister', 'Sister'),
        ('wife', 'Wife'),
        ('husband', 'Husband'),
        ('son', 'Son'),
        ('daughter', 'Daughter'),
        ('friend', 'Friend'),
        ('other', 'Other'),
    ], string='Emergency Contact Relationship')
    emergency_mobile = fields.Char(string='Emergency Contact Mobile')

    # ── Church background ─────────────────────────────────────
    church_name = fields.Char(string='Local Church Name')
    church_location = fields.Char(string='Church Location')
    church_denomination = fields.Selection([
        ('baptist', 'Baptist'),
        ('brethren', 'Brethren'),
        ('pentecostal', 'Pentecostal'),
        ('charismatic', 'Charismatic'),
        ('methodist', 'Methodist'),
        ('presbyterian', 'Presbyterian'),
        ('roman_catholic', 'Roman Catholic'),
        ('eastern_orthodox', 'Eastern Orthodox'),
        ('independent', 'Independent'),
        ('other', 'Other'),
    ], string='Church Denomination')
    church_ministry_type = fields.Text(string='Church Ministry Involvement')
    is_ordained = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Ordained?')
    church_financial_support = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Church Financial Support?',
    )
    graduated_seminary_last_two_years = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Seminary Graduate (Last 2 Years)?',
    )
    working_for_organisation = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Working for an Organisation?',
    )

    # ── References ────────────────────────────────────────────
    personal_reference_1 = fields.Text(string='Personal Reference 1')
    personal_reference_2 = fields.Text(string='Personal Reference 2')
    personal_reference_3 = fields.Text(string='Personal Reference 3')

    # ── Academic / professional qualification ─────────────────
    class_x_month_year = fields.Char(string='Class X Month & Year of Completion')
    class_x_year = fields.Char(string='Class X (Year of Completion)')
    diploma_after_class_x = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='Diploma After Class X Instead of Class XII?',
    )
    diploma_subject = fields.Char(string='Diploma Course Name')
    diploma_enroll_year = fields.Char(string='Diploma Year of Enrolment')
    diploma_complete_month_year = fields.Char(string='Diploma Month & Year of Completion')
    diploma_program_duration = fields.Char(string='Diploma Program Duration')
    class_xii_month_year = fields.Char(string='Class XII Month & Year of Completion')
    class_xii_diploma_year = fields.Char(string='Diploma / Class XII (Year of Completion)')
    ug_degree_type = fields.Selection([
        ('theological', 'Theological Degree'),
        ('non_theological', 'Non-theological Degree'),
        ('both', 'Both Degrees'),
    ], string='Type of Undergraduate Degree')
    ug_theo_diploma_bible_college = fields.Char(string='UG Theo Diploma — Bible College')
    ug_theo_diploma_enroll_year = fields.Char(string='UG Theo Diploma — Year of Enrolment')
    ug_theo_diploma_grad_month_year = fields.Char(string='UG Theo Diploma — Month & Year of Graduation')
    ug_theo_diploma_duration = fields.Char(string='UG Theo Diploma — Duration of Study')
    ug_theo_diploma_grade = fields.Char(string='UG Theo Diploma — Grade / GPA')
    ug_theo_bth_bible_college = fields.Char(string='B Th — Bible College')
    ug_theo_bth_enroll_year = fields.Char(string='B Th — Year of Enrolment')
    ug_theo_bth_grad_month_year = fields.Char(string='B Th — Month & Year of Graduation')
    ug_theo_bth_duration = fields.Char(string='B Th — Duration of Study')
    ug_theo_bth_grade = fields.Char(string='B Th — Grade / GPA')
    ug_non_theo_college = fields.Char(string='UG Non-Theo — College')
    ug_non_theo_university = fields.Char(string='UG Non-Theo — University')
    ug_non_theo_enroll_year = fields.Char(string='UG Non-Theo — Year of Enrolment')
    ug_non_theo_grad_month_year = fields.Char(string='UG Non-Theo — Month & Year of Graduation')
    ug_non_theo_duration = fields.Char(string='UG Non-Theo — Duration of Study')
    ug_non_theo_grade = fields.Char(string='UG Non-Theo — Grade / Class / GPA')
    pg_degree_type = fields.Selection([
        ('theological', 'Theological Degree'),
        ('non_theological', 'Non-theological Degree'),
        ('both', 'Both Degrees'),
    ], string='Type of Postgraduate Degree')
    pg_theo_mdiv_seminary = fields.Char(string='MDiv — Seminary')
    pg_theo_mdiv_enroll_year = fields.Char(string='MDiv — Year of Enrolment')
    pg_theo_mdiv_grad_month_year = fields.Char(string='MDiv — Month & Year of Graduation')
    pg_theo_mdiv_duration = fields.Char(string='MDiv — Duration of Study')
    pg_theo_mdiv_grade = fields.Char(string='MDiv — Grade / GPA')
    pg_non_theo_masters_college = fields.Char(string='PG Masters — College')
    pg_non_theo_masters_university = fields.Char(string='PG Masters — University')
    pg_non_theo_masters_enroll_year = fields.Char(string='PG Masters — Year of Enrolment')
    pg_non_theo_masters_grad_month_year = fields.Char(string='PG Masters — Month & Year of Graduation')
    pg_non_theo_masters_duration = fields.Char(string='PG Masters — Duration of Study')
    pg_non_theo_masters_grade = fields.Char(string='PG Masters — Grade / Class / GPA')
    pg_non_theo_doctorate_college = fields.Char(string='PG Doctorate — College')
    pg_non_theo_doctorate_university = fields.Char(string='PG Doctorate — University')
    pg_non_theo_doctorate_enroll_year = fields.Char(string='PG Doctorate — Year of Enrolment')
    pg_non_theo_doctorate_grad_month_year = fields.Char(string='PG Doctorate — Month & Year of Graduation')
    pg_non_theo_doctorate_duration = fields.Char(string='PG Doctorate — Duration of Study')
    pg_non_theo_doctorate_grade = fields.Char(string='PG Doctorate — Grade / Class / GPA')
    has_undergraduate_theology = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Undergraduate Degree in Theology?',
    )
    has_undergraduate_non_theology = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Undergraduate Non-Theological Degree?',
    )
    has_postgraduate_theology = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Post-graduate Degree in Theology?',
    )
    has_postgraduate_non_theology = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Non-theological Post-graduate Degree?',
    )
    has_doctoral_non_theology = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Non-theological Doctoral Degree?',
    )

    # ── Financial information ─────────────────────────────────
    monthly_support_inr = fields.Char(string='Monthly Support (INR)')
    monthly_support_usd = fields.Char(string='Monthly Support (USD)')
    has_financial_sponsor = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Financial Sponsor?',
    )
    financial_supporter_role = fields.Text(string='Who Will Support You Financially?')
    financial_supporter_name = fields.Char(string='Financial Supporter Name')
    financial_supporter_relation = fields.Char(string='Financial Supporter Relationship')
    financial_supporter_email = fields.Char(string='Financial Supporter Email')
    financial_supporter_phone = fields.Char(string='Financial Supporter Phone')
    financial_supporter_address = fields.Text(string='Financial Supporter Address')

    # ── Family ────────────────────────────────────────────────
    father_name = fields.Char(string="Father's Name")
    father_occupation = fields.Char(string="Father's Occupation")
    mother_name = fields.Char(string="Mother's Name")
    mother_occupation = fields.Char(string="Mother's Occupation")
    parents_born_again = fields.Text(string="Parents 'Born Again'?")
    parents_believers = fields.Text(string='Parents Believers in Jesus Christ?')
    family_postal_addresses = fields.Text(string='Family Postal Address(es)')
    family_email_addresses = fields.Text(string='Family Email Addresses')
    family_contact_details = fields.Text(string='Family Contact Details')

    # ── Spouse ────────────────────────────────────────────────
    spouse_name = fields.Char(string='Spouse Name')
    spouse_dob = fields.Date(string='Spouse Date of Birth')
    spouse_nationality = fields.Many2one('res.country', string='Spouse Nationality')
    spouse_state = fields.Char(string='Spouse State')
    spouse_occupation = fields.Char(string='Spouse Occupation')
    spouse_place_of_work = fields.Char(string='Spouse Place of Work')
    spouse_mother_tongue = fields.Char(string='Spouse Mother Tongue')
    spouse_qualification = fields.Char(string='Spouse Academic / Professional Qualification')
    spouse_supportive = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Spouse Supportive of Theological Study?',
    )
    spouse_applying_ets = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Spouse Applying to ETS?',
    )
    family_accommodation = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Requires Family Accommodation at ETS?',
    )

    # ── Children ──────────────────────────────────────────────
    has_children = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Has Children?')
    children_count = fields.Char(string='Number of Children')
    children_names = fields.Char(string='Children Name/s')
    children_ages = fields.Char(string='Children Age/s')
    children_genders = fields.Char(string='Children Gender/s')
    children_at_aca = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='Children Admission at Asian Christian High School?',
    )
    child1_class = fields.Char(string='1st Child Class')
    child2_class = fields.Char(string='2nd Child Class')
    child3_class = fields.Char(string='3rd Child Class')

    # ── Spiritual identity ────────────────────────────────────
    religious_background_birth = fields.Selection([
        ('christianity', 'Christianity'),
        ('hinduism', 'Hinduism'),
        ('islam', 'Islam'),
        ('buddhism', 'Buddhism'),
        ('jainism', 'Jainism'),
        ('other', 'Other'),
    ], string='Religious Background at Birth')
    believers_baptism = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string="Believer's Baptism (by Immersion)?",
    )
    called_to_ministry = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('not_sure', 'Not Sure'),
    ], string='Called to Christian Ministry?')
    read_doctrinal_statement = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Read ETS Doctrinal Statement?',
    )
    agree_doctrinal_statement = fields.Selection([
        ('yes_agree', 'Yes, I agree'),
        ('not_formed', 'Not formed an opinion in a few areas'),
        ('no', 'No'),
    ], string='Agree with ETS Doctrinal Statement?')

    # ── Work experience ───────────────────────────────────────
    currently_employed = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Currently Employed?',
    )
    active_christian_ministry = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Active Christian Ministry Participation?',
    )
    how_knew_seminary = fields.Text(string='How Did You Learn About ETS?')

    # ── Health information ────────────────────────────────────
    blood_group = fields.Selection([
        ('A', 'A'), ('A+', 'A+'), ('A-', 'A-'),
        ('B', 'B'), ('B+', 'B+'), ('B-', 'B-'),
        ('AB', 'AB'), ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O', 'O'), ('O+', 'O+'), ('O-', 'O-'),
    ], string='Blood Group')
    height_cm = fields.Float(string='Height (cm)', digits=(6, 1))
    weight_kg = fields.Float(string='Weight (kg)', digits=(6, 1))
    allergies = fields.Text(string='Allergies')
    chronic_illness = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Chronic Illness?')
    prolonged_medication = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Prolonged Medication?',
    )
    vision_hearing_problem = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Vision or Hearing Problem?',
    )
    uses_tobacco = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Uses Tobacco?')
    uses_intoxicants = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Uses Intoxicants or Narcotics?',
    )
    suffers_sleeplessness = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Suffers from Sleeplessness?',
    )
    psychiatric_care_history = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Psychiatric Care History?',
    )
    other_medical_problems = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Other Medical Problems?',
    )

    # ── Document uploads ──────────────────────────────────────
    photo = fields.Binary(string='Photo', attachment=True)
    doc_aadhaar = fields.Binary(string='Aadhaar', attachment=True)
    doc_passport = fields.Binary(string='Passport Pages', attachment=True)
    doc_visa = fields.Binary(string='Valid Visa', attachment=True)
    doc_change_of_name = fields.Binary(string='Change of Name Affidavit', attachment=True)
    doc_marriage_certificate = fields.Binary(string='Marriage Certificate', attachment=True)
    doc_church_recommendation = fields.Binary(string='Church Recommendation Letter', attachment=True)
    doc_reference_form_1 = fields.Binary(string='Reference Form 1', attachment=True)
    doc_reference_form_2 = fields.Binary(string='Reference Form 2', attachment=True)
    doc_reference_form_3 = fields.Binary(string='Reference Form 3', attachment=True)
    doc_reference_form_4_employer = fields.Binary(string='Reference Form 4 (Employer)', attachment=True)
    doc_finance_assurance = fields.Binary(string='Finance Assurance Form', attachment=True)
    doc_financial_guarantee = fields.Binary(string='Financial Guarantee Letter', attachment=True)
    doc_conduct_seminary = fields.Binary(string='Conduct Certificate (Seminary)', attachment=True)
    doc_conduct_employer = fields.Binary(string='Conduct Certificate (Employer)', attachment=True)
    doc_school_admission_children = fields.Binary(string='School Admission (Children)', attachment=True)
    doc_personal_testimony = fields.Binary(string='Personal Testimony', attachment=True)
    doc_christian_ministry_experience = fields.Binary(string='Christian Ministry Experience', attachment=True)
    doc_work_experience = fields.Binary(string='Work Experience', attachment=True)
    doc_fitness_certificate = fields.Binary(string='Fitness Certificate', attachment=True)
    doc_chronic_illness = fields.Binary(string='Chronic Illness Documentation', attachment=True)
    doc_prolonged_medication = fields.Binary(string='Prolonged Medication Documentation', attachment=True)
    doc_vision_hearing = fields.Binary(string='Vision/Hearing Impairment Documents', attachment=True)
    doc_psychiatric_care = fields.Binary(string='Psychiatric Care Documentation', attachment=True)
    doc_class_x = fields.Binary(string='Class X', attachment=True)
    doc_class_xii_diploma = fields.Binary(string='Class XII / Diploma', attachment=True)
    doc_ug_degree_1_mark_sheet = fields.Binary(string='UG Degree 1 Mark Sheet', attachment=True)
    doc_ug_degree_1_certificate = fields.Binary(string='UG Degree 1 Certificate', attachment=True)
    doc_ug_degree_2_mark_sheet = fields.Binary(string='UG Degree 2 Mark Sheet', attachment=True)
    doc_ug_degree_2_certificate = fields.Binary(string='UG Degree 2 Certificate', attachment=True)
    doc_pg_degree_1_mark_sheet = fields.Binary(string='PG Degree 1 Mark Sheet', attachment=True)
    doc_pg_degree_1_certificate = fields.Binary(string='PG Degree 1 Certificate', attachment=True)
    doc_pg_degree_2_mark_sheet = fields.Binary(string='PG Degree 2 Mark Sheet', attachment=True)
    doc_pg_degree_2_certificate = fields.Binary(string='PG Degree 2 Certificate', attachment=True)
    doc_pg_diploma_mark_sheet = fields.Binary(string='PG Diploma Mark Sheet', attachment=True)
    doc_pg_diploma_certificate = fields.Binary(string='PG Diploma Certificate', attachment=True)
    doc_other_degrees = fields.Binary(string='Other Diplomas/Degrees', attachment=True)
    doc_yet_to_graduate = fields.Binary(string='Yet-to-Graduate Pending Documents', attachment=True)
    doc_application_fee = fields.Binary(string='Application Fee / Bank Transaction', attachment=True)

    # ── Online application fee (Razorpay) ───────────────────────
    application_fee_paid = fields.Boolean(
        string='Application Fee Paid', default=False, tracking=True,
    )
    payment_successful = fields.Boolean(
        string='Payment Successful', default=False, tracking=True,
    )
    payment_provider = fields.Char(string='Payment Provider')
    payment_id = fields.Char(
        string='Razorpay Payment ID', copy=False, index=True,
        help='Search this ID in the Razorpay Dashboard under Transactions.',
    )
    payment_order_id = fields.Char(
        string='Razorpay Order ID', copy=False, index=True,
    )
    payment_receipt = fields.Char(
        string='Payment Receipt / Reference', copy=False,
    )
    payment_status = fields.Char(string='Payment Status')
    payment_method = fields.Char(string='Payment Method')
    payment_amount = fields.Float(string='Payment Amount (INR)', digits=(12, 2))
    payment_amount_paise = fields.Integer(string='Payment Amount (paise)')
    payment_currency = fields.Char(string='Payment Currency', default='INR')
    application_fee_invoice_id = fields.Many2one(
        'account.move', string='Application Fee Invoice', copy=False, readonly=True,
    )

    # ── Self declaration ──────────────────────────────────────
    self_declaration_agreed = fields.Boolean(string='Self Declaration Agreed')

    # ── Document review (registrar checklist) ─────────────────
    document_review_ids = fields.One2many(
        'school.admission.document.review', 'admission_id',
        string='Document Reviews', copy=False,
    )
    documents_with_issues = fields.Integer(
        compute='_compute_document_review_counts', string='Documents With Issues',
    )
    documents_pending_review = fields.Integer(
        compute='_compute_document_review_counts', string='Documents Pending Review',
    )
    document_upload_token = fields.Char(
        string='Document Upload Token', copy=False, index=True, readonly=True,
    )
    document_upload_token_expiry = fields.Datetime(
        string='Upload Link Expires', copy=False, readonly=True,
    )
    document_upload_url = fields.Char(
        string='Document Upload Link',
        compute='_compute_document_upload_url',
    )

    # ── Interview / evaluation (internal) ─────────────────────
    interview_date = fields.Datetime(string='Interview Date', tracking=True)
    interviewer_id = fields.Many2one('res.users', string='Interviewer')
    interview_notes = fields.Html(string='Interview Notes')
    interview_pass = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Interview Result', default='pending', tracking=True)

    # ── Entrance exam ─────────────────────────────────────────
    exam_result_file = fields.Binary(string='Exam Results', attachment=True)
    exam_result_filename = fields.Char(string='Exam Results Filename')
    exam_pass = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Exam Result', default='pending', tracking=True)

    # ── Exam visit accommodation (optional, paid before arrival) ──
    EXAM_ACCOMMODATION_RATE_INR = 500.0
    EXAM_ACCOMMODATION_MAX_NIGHTS = 3

    partner_id = fields.Many2one(
        'res.partner', string='Applicant Contact', copy=False, readonly=True,
    )
    needs_exam_accommodation = fields.Boolean(
        string='Needs Exam Visit Accommodation',
        tracking=True,
        help='Check if the applicant needs on-campus accommodation when coming for the exam.',
    )
    exam_accommodation_nights = fields.Selection([
        ('1', '1 night'),
        ('2', '2 nights'),
        ('3', '3 nights'),
    ], string='Accommodation Nights', tracking=True)
    exam_accommodation_amount = fields.Float(
        string='Accommodation Amount (INR)',
        compute='_compute_exam_accommodation_amount',
        store=True,
        digits=(12, 2),
    )
    exam_accommodation_payment_link_id = fields.Char(
        string='Accommodation Payment Link ID', copy=False, readonly=True,
    )
    exam_accommodation_payment_link_url = fields.Char(
        string='Accommodation Payment Link', copy=False, readonly=True,
    )
    exam_accommodation_paid = fields.Boolean(
        string='Accommodation Fee Paid', default=False, tracking=True, copy=False,
    )
    exam_accommodation_payment_id = fields.Char(
        string='Accommodation Razorpay Payment ID', copy=False, readonly=True,
    )
    exam_accommodation_payment_status = fields.Char(
        string='Accommodation Payment Status', copy=False, readonly=True,
    )
    exam_accommodation_invoice_id = fields.Many2one(
        'account.move', string='Accommodation Fee Invoice', copy=False, readonly=True,
    )

    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Important'), ('2', 'Urgent')],
        string='Priority', default='0', tracking=True,
    )

    # ── Workflow ──────────────────────────────────────────────
    state = fields.Selection([
        ('initial_review', 'Initial Review'),
        ('pending_applicant', 'Pending Applicant Response'),
        ('pending_exam_interview', 'Pending Exam & Interview'),
        ('admission_denied', 'Admission Denied'),
        ('accepted', 'Accepted'),
    ], string='Status', default='initial_review', tracking=True)
    decision_date = fields.Date(string='Decision Date', tracking=True)
    rejection_reason = fields.Text(string='Rejection Reason')
    student_id = fields.Many2one(
        'school.student', string='Created Student', readonly=True, copy=False,
    )
    whatsapp_message_ids = fields.One2many(
        'school.whatsapp.message', 'admission_id', string='WhatsApp Messages',
    )
    notes = fields.Html(string='Internal Notes')
    color = fields.Integer(string='Color Index', compute='_compute_color')

    @api.depends('needs_exam_accommodation', 'exam_accommodation_nights')
    def _compute_exam_accommodation_amount(self):
        for rec in self:
            if rec.needs_exam_accommodation and rec.exam_accommodation_nights:
                nights = int(rec.exam_accommodation_nights)
                rec.exam_accommodation_amount = nights * self.EXAM_ACCOMMODATION_RATE_INR
            else:
                rec.exam_accommodation_amount = 0.0

    @api.constrains('needs_exam_accommodation', 'exam_accommodation_nights')
    def _check_exam_accommodation_nights(self):
        for rec in self:
            if rec.needs_exam_accommodation and not rec.exam_accommodation_nights:
                raise ValidationError(_(
                    'Select the number of accommodation nights (1–3) for %s.',
                ) % rec.name)
            if rec.exam_accommodation_nights:
                nights = int(rec.exam_accommodation_nights)
                if nights < 1 or nights > self.EXAM_ACCOMMODATION_MAX_NIGHTS:
                    raise ValidationError(_(
                        'Exam accommodation is limited to %s nights maximum.',
                    ) % self.EXAM_ACCOMMODATION_MAX_NIGHTS)

    @api.depends('first_name', 'middle_name', 'last_name')
    def _compute_name(self):
        for rec in self:
            parts = [p for p in (rec.first_name, rec.middle_name, rec.last_name) if p]
            rec.name = ' '.join(parts)

    @api.depends('document_review_ids.is_verified', 'document_review_ids.has_issue')
    def _compute_document_review_counts(self):
        for rec in self:
            rec.documents_with_issues = len(
                rec.document_review_ids.filtered('has_issue'),
            )
            rec.documents_pending_review = len(
                rec.document_review_ids.filtered(
                    lambda d: not d.is_verified and not d.has_issue,
                ),
            )

    @api.depends('document_upload_token')
    def _compute_document_upload_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        for rec in self:
            if rec.document_upload_token and base:
                rec.document_upload_url = '%s/admission/upload/%s' % (
                    base, rec.document_upload_token,
                )
            else:
                rec.document_upload_url = False

    @api.depends('state')
    def _compute_color(self):
        color_map = {
            'initial_review': 3,
            'pending_applicant': 6,
            'pending_exam_interview': 4,
            'admission_denied': 1,
            'accepted': 10,
        }
        for rec in self:
            rec.color = color_map.get(rec.state, 0)

    def _ensure_document_reviews(self):
        Review = self.env['school.admission.document.review']
        for admission in self:
            existing = set(admission.document_review_ids.mapped('document_code'))
            to_create = [
                {
                    'admission_id': admission.id,
                    'sequence': (idx + 1) * 10,
                    'document_code': code,
                    'document_label': label,
                }
                for idx, (code, label) in enumerate(admission.ADMISSION_DOCUMENT_SLOTS)
                if code not in existing
            ]
            if to_create:
                Review.create(to_create)

    def format_selection(self, field_name):
        """Return the human-readable label for a selection field (for email templates)."""
        self.ensure_one()
        field = self._fields[field_name]
        labels = dict(field._description_selection(self.env))
        return labels.get(self[field_name], self[field_name] or '')

    COURSE_REG_CODES = {
        'macs': 'MACS',
        'pgdbs': 'PGDBS',
        'mabs': 'MABS',
        'mdiv': 'MDIV',
        'macc': 'MACC',
        'mth': 'MTH',
    }

    @api.model
    def _registration_year_from_vals(self, vals, record=None):
        record = record or self
        app_date = vals.get('application_date')
        if app_date:
            if isinstance(app_date, str):
                return int(app_date[:4])
            return app_date.year
        if record.application_date:
            return record.application_date.year
        return fields.Date.today().year

    @api.model
    def _next_registration_number(self, course, year, counters):
        code = self.COURSE_REG_CODES.get(course, (course or '').upper())
        prefix = f'{year}{code}'
        if prefix not in counters:
            existing = self.search([('registration_number', '=like', f'{prefix}%')])
            max_seq = 0
            for rec in existing:
                suffix = (rec.registration_number or '')[len(prefix):]
                if suffix.isdigit():
                    max_seq = max(max_seq, int(suffix))
            counters[prefix] = max_seq
        counters[prefix] += 1
        return f'{prefix}{counters[prefix]:03d}'

    def _assign_registration_number(self):
        for rec in self:
            if rec.registration_number or not rec.course:
                continue
            year = rec._registration_year_from_vals({}, record=rec)
            rec.registration_number = rec._next_registration_number(
                rec.course, year, {},
            )
        self._ensure_applicant_partner()

    def _ensure_applicant_partner(self):
        """Create or link a billing contact for this applicant."""
        Partner = self.env['res.partner']
        for admission in self:
            if not admission.email:
                continue
            partner = Partner.find_or_create_school_billing_partner(
                record_ref=admission.registration_number,
                name=admission.name or admission.email,
                email=admission.email,
                phone=(
                    admission.mobile_number
                    or admission.whatsapp_number
                    or admission.phone_number
                ),
                current_partner=admission.partner_id,
            )
            admission.partner_id = partner.id

    def _application_fee_is_paid(self):
        self.ensure_one()
        return bool(self.application_fee_paid or self.payment_successful)

    def _get_application_fee_product(self):
        product = self.env.ref('kaierp.product_application_fee', raise_if_not_found=False)
        if product:
            return product.product_variant_id
        return self.env['product.product'].search([
            ('product_tmpl_id.ets_fee_code', '=', 'application_fee'),
        ], limit=1)

    def _post_invoice_and_register_payment(self, invoice):
        """Post a customer invoice and register full payment in Accounting."""
        invoice = invoice.sudo()
        if invoice.payment_state == 'paid':
            return
        if invoice.state == 'draft':
            invoice.action_post()
        if invoice.payment_state == 'paid':
            return
        wizard = self.env['account.payment.register'].sudo().with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create({})
        wizard.action_create_payments()

    def _register_application_fee_accounting_if_paid(self):
        paid = self.filtered(
            lambda a: a._application_fee_is_paid() and not a.application_fee_invoice_id,
        )
        paid.sudo()._register_application_fee_accounting()

    def _register_application_fee_accounting(self):
        """Create a posted customer invoice and payment for the application fee."""
        Move = self.env['account.move'].sudo()
        for admission in self:
            if admission.application_fee_invoice_id or not admission._application_fee_is_paid():
                continue
            admission.sudo()._ensure_applicant_partner()
            if not admission.partner_id:
                continue
            product = admission._get_application_fee_product()
            if not product:
                continue
            amount = admission.payment_amount or product.list_price
            invoice = Move.create({
                'move_type': 'out_invoice',
                'partner_id': admission.partner_id.id,
                'invoice_date': admission.application_date or fields.Date.today(),
                'ref': '%s application fee' % (
                    admission.registration_number or admission.reference,
                ),
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': product.display_name,
                    'quantity': 1,
                    'price_unit': amount,
                })],
            })
            if admission.payment_id:
                invoice.payment_reference = admission.payment_id
            elif admission.payment_receipt:
                invoice.payment_reference = admission.payment_receipt
            admission.sudo().write({'application_fee_invoice_id': invoice.id})
            admission._post_invoice_and_register_payment(invoice)
            admission.sudo().message_post(
                body=_('Application fee invoice %s created and marked paid (₹%s).') % (
                    invoice.name, amount,
                ),
            )

    def action_view_application_fee_invoice(self):
        self.ensure_one()
        if not self.application_fee_invoice_id:
            raise ValidationError(_('No application fee invoice linked to this application.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Application Fee Invoice'),
            'res_model': 'account.move',
            'res_id': self.application_fee_invoice_id.id,
            'view_mode': 'form',
        }

    def _get_exam_accommodation_product(self):
        product = self.env.ref('kaierp.product_exam_accommodation', raise_if_not_found=False)
        if product:
            return product.product_variant_id
        return self.env['product.product'].search([
            ('product_tmpl_id.ets_fee_code', '=', 'exam_accommodation'),
        ], limit=1)

    def action_send_exam_accommodation_payment_link(self):
        """Create a Razorpay Payment Link and email it to the applicant."""
        self.ensure_one()
        if not self.needs_exam_accommodation:
            raise ValidationError(_('Enable "Needs Exam Visit Accommodation" first.'))
        if not self.exam_accommodation_nights:
            raise ValidationError(_('Select how many nights (1–3) are required.'))
        if self.exam_accommodation_paid:
            raise ValidationError(_('Accommodation fee is already marked as paid.'))
        if not self.email:
            raise ValidationError(_('This application has no email address.'))

        Razorpay = self.env['school.razorpay.payment']
        nights = int(self.exam_accommodation_nights)
        amount = self.exam_accommodation_amount
        description = _('Exam visit accommodation — %s night(s)') % nights
        reference_id = '%s-exam-acc-%s' % (
            (self.registration_number or self.reference or str(self.id)).replace('/', '-'),
            nights,
        )

        result = Razorpay.create_payment_link(
            self, amount, description, reference_id,
        )
        self.write({
            'exam_accommodation_payment_link_id': result.get('id', ''),
            'exam_accommodation_payment_link_url': result.get('short_url', ''),
            'exam_accommodation_payment_status': result.get('status', 'created'),
        })

        template = self.env.ref(
            'kaierp.email_template_exam_accommodation_payment',
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)
        else:
            self.message_post(
                body=_(
                    'Exam accommodation payment link sent manually: %s',
                ) % self.exam_accommodation_payment_link_url,
            )

        self.message_post(
            body=_(
                'Exam accommodation payment link created (%s night(s), ₹%s): %s',
            ) % (nights, amount, self.exam_accommodation_payment_link_url),
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payment link sent'),
                'message': _('An email with the Razorpay payment link was sent to %s.') % self.email,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_sync_exam_accommodation_payment(self):
        """Check Razorpay for payment link status and update this application."""
        self.ensure_one()
        if not self.exam_accommodation_payment_link_id:
            raise ValidationError(_('Send a payment link first.'))
        if self.exam_accommodation_paid:
            raise ValidationError(_('Accommodation fee is already marked as paid.'))

        Razorpay = self.env['school.razorpay.payment']
        status = Razorpay.sync_exam_accommodation_payment(self)
        if status == 'paid':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Payment received'),
                    'message': _('Razorpay confirms payment. Accommodation fee marked as paid.'),
                    'type': 'success',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payment pending'),
                'message': _('Razorpay status: %s') % (status or _('unknown')),
                'type': 'warning',
                'sticky': False,
            },
        }

    def action_mark_exam_accommodation_paid(self):
        """Mark accommodation as paid manually (e.g. bank transfer with receipt)."""
        self.ensure_one()
        if not self.needs_exam_accommodation:
            raise ValidationError(_('This applicant does not need exam accommodation.'))
        if self.exam_accommodation_paid:
            raise ValidationError(_('Accommodation fee is already marked as paid.'))
        self._register_exam_accommodation_payment(
            payment_link={'status': 'paid'},
            payment={},
            manual=True,
        )

    def _register_exam_accommodation_payment(self, payment_link, payment, manual=False):
        """Record accommodation payment and create invoice."""
        for admission in self:
            if admission.exam_accommodation_paid:
                continue
            vals = {
                'exam_accommodation_paid': True,
                'exam_accommodation_payment_status': payment_link.get('status', 'paid'),
            }
            if payment_link.get('id'):
                vals['exam_accommodation_payment_link_id'] = payment_link['id']
            if payment:
                vals['exam_accommodation_payment_id'] = payment.get('id', '')
            admission.write(vals)
            admission._register_exam_accommodation_invoice(manual=manual)
            amount_inr = admission.exam_accommodation_amount
            if payment.get('amount'):
                amount_inr = payment['amount'] / 100.0
            admission.message_post(
                body=_('Exam visit accommodation fee marked as paid (₹%s).') % amount_inr,
            )

    def _register_exam_accommodation_invoice(self, manual=False):
        Move = self.env['account.move'].sudo()
        for admission in self:
            if admission.exam_accommodation_invoice_id or not admission.exam_accommodation_paid:
                continue
            admission._ensure_applicant_partner()
            if not admission.partner_id:
                continue
            product = admission._get_exam_accommodation_product()
            if not product:
                continue
            nights = int(admission.exam_accommodation_nights or 1)
            invoice = Move.create({
                'move_type': 'out_invoice',
                'partner_id': admission.partner_id.id,
                'invoice_date': fields.Date.today(),
                'ref': '%s exam accommodation' % (
                    admission.registration_number or admission.reference,
                ),
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': '%s (%s night(s))' % (product.display_name, nights),
                    'quantity': nights,
                    'price_unit': self.EXAM_ACCOMMODATION_RATE_INR,
                })],
            })
            if admission.exam_accommodation_payment_id:
                invoice.payment_reference = admission.exam_accommodation_payment_id
            admission.exam_accommodation_invoice_id = invoice.id
            admission._post_invoice_and_register_payment(invoice)
            admission.message_post(
                body=_('Exam accommodation invoice %s created%s.') % (
                    invoice.name,
                    _(' (manual)') if manual else '',
                ),
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'school.admission',
                ) or _('New')
        records = super().create(vals_list)
        records._assign_registration_number()
        records._ensure_document_reviews()
        records._register_application_fee_accounting_if_paid()
        records._send_new_admission_emails()
        records._send_whatsapp_application_received()
        return records

    def write(self, vals):
        track_state = 'state' in vals
        old_states = {rec.id: rec.state for rec in self} if track_state else {}
        payment_trigger = any(
            key in vals for key in (
                'application_fee_paid', 'payment_successful',
                'payment_amount', 'payment_id', 'payment_receipt',
            )
        )
        result = super().write(vals)
        if payment_trigger:
            self._register_application_fee_accounting_if_paid()
        if track_state:
            for rec in self:
                previous = old_states.get(rec.id)
                if previous and previous != rec.state:
                    rec._send_whatsapp_on_state_change(previous, rec.state)
        return result

    def _send_new_admission_emails(self):
        self._notify_registrar_new_admission()
        self._notify_applicant_application_received()
        self._notify_registrars_inbox()

    def _get_registrar_users(self):
        """Return active internal users who should receive admission alerts."""
        registrar_users = self.env['school.registrar'].search([
            ('state', '=', 'active'),
            ('user_id', '!=', False),
        ]).mapped('user_id').filtered('active')

        if not registrar_users:
            group = self.env.ref('kaierp.group_school_registrar', raise_if_not_found=False)
            if group:
                registrar_users = self.env['res.users'].search([
                    ('group_ids', 'in', group.id),
                    ('active', '=', True),
                    ('share', '=', False),
                ])
        return registrar_users

    def _notify_registrars_inbox(self):
        """Send in-app Odoo inbox notifications to registrar users."""
        registrar_users = self._get_registrar_users()
        if not registrar_users:
            return

        partner_ids = registrar_users.mapped('partner_id').ids
        for admission in self:
            body = Markup(_(
                'New admission application <strong>%(ref)s</strong> from '
                '<strong>%(name)s</strong> — %(course)s.',
                ref=admission.reference,
                name=admission.name,
                course=admission.format_selection('course'),
            ))
            admission.message_subscribe(partner_ids=partner_ids)
            message = admission.message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                partner_ids=partner_ids,
            )
            # User preference may be "email" — force inbox so it appears in Odoo.
            self.env['mail.notification'].sudo().search([
                ('mail_message_id', '=', message.id),
            ]).unlink()
            recipients_data = [{
                'active': True,
                'email_normalized': user.partner_id.email_normalized,
                'id': user.partner_id.id,
                'uid': user.id,
                'notif': 'inbox',
                'is_follower': True,
                'lang': user.lang or self.env.lang,
                'name': user.partner_id.name,
                'groups': user.group_ids.ids,
                'share': False,
                'type': 'user',
                'ushare': False,
            } for user in registrar_users]
            admission._notify_thread_by_inbox(message, recipients_data)

    def _notify_registrar_new_admission(self):
        registrar_email = self.env['ir.config_parameter'].sudo().get_param(
            'kaierp.admission_registrar_email',
        )
        if not registrar_email:
            return
        template = self.env.ref(
            'kaierp.email_template_admission_new_registrar', raise_if_not_found=False,
        )
        if not template:
            return
        for admission in self:
            template.send_mail(
                admission.id,
                force_send=True,
                email_values={'email_to': registrar_email},
            )

    def _notify_applicant_application_received(self):
        template = self.env.ref(
            'kaierp.email_template_admission_received_applicant', raise_if_not_found=False,
        )
        if not template:
            return
        for admission in self:
            if not admission.email:
                continue
            template.send_mail(admission.id, force_send=True)

    def _send_whatsapp_application_received(self):
        self._send_whatsapp_notification('received')

    def _send_whatsapp_on_state_change(self, old_state, new_state):
        template_key_map = {
            'pending_applicant': 'pending_applicant',
            'pending_exam_interview': 'exam_interview',
            'accepted': 'accepted',
            'admission_denied': 'denied',
        }
        key = template_key_map.get(new_state)
        if key:
            self._send_whatsapp_notification(key)

    def _send_whatsapp_notification(self, event_key):
        """Send a WhatsApp template for the given admission event."""
        Whatsapp = self.env['school.whatsapp.message']
        if not Whatsapp.is_enabled():
            return

        config_keys = {
            'received': 'kaierp.whatsapp_template_received',
            'pending_applicant': 'kaierp.whatsapp_template_pending_applicant',
            'exam_interview': 'kaierp.whatsapp_template_exam_interview',
            'accepted': 'kaierp.whatsapp_template_accepted',
            'denied': 'kaierp.whatsapp_template_denied',
        }
        param_key = config_keys.get(event_key)
        if not param_key:
            return

        template_name = self.env['ir.config_parameter'].sudo().get_param(param_key, '').strip()
        if not template_name:
            return

        for admission in self:
            if not admission.whatsapp_number:
                continue
            params_map = {
                'received': [
                    admission.name,
                    admission.reference,
                    admission.format_selection('course'),
                ],
                'pending_applicant': [admission.name, admission.reference],
                'exam_interview': [admission.name, admission.reference],
                'accepted': [admission.name, admission.format_selection('course')],
                'denied': [admission.name, admission.reference],
            }
            Whatsapp.send_template(
                admission.whatsapp_number,
                template_name,
                body_parameters=params_map.get(event_key, []),
                admission=admission,
            )

    def action_view_student(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Student Profile'),
            'res_model': 'school.student',
            'res_id': self.student_id.id,
            'view_mode': 'form',
        }

    def action_whatsapp_open_conversation(self):
        """Open the WhatsApp conversation thread for this applicant."""
        self.ensure_one()
        phone = self.whatsapp_number
        if not phone and self.whatsapp_message_ids:
            phone = self.whatsapp_message_ids[0].phone
        if not phone:
            raise ValidationError(_('This application has no WhatsApp number.'))
        Whatsapp = self.env['school.whatsapp.message']
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Conversation'),
            'res_model': 'school.whatsapp.reply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_admission_id': self.id,
                'default_phone': Whatsapp.normalize_phone(
                    phone, country=self.country_id,
                ) or phone,
            },
        }

    def action_verify_all_documents(self):
        self.ensure_one()
        self.document_review_ids.write({'is_verified': True, 'has_issue': False})

    def _document_upload_token_validity_days(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'kaierp.document_upload_token_days', '14',
        )
        try:
            days = int(raw)
        except (TypeError, ValueError):
            days = 14
        return max(1, min(days, 90))

    def _generate_document_upload_token(self):
        """Create or refresh a public upload token for this application."""
        self.ensure_one()
        days = self._document_upload_token_validity_days()
        self.write({
            'document_upload_token': secrets.token_urlsafe(32),
            'document_upload_token_expiry': fields.Datetime.now() + timedelta(days=days),
        })
        return self.document_upload_url

    def _invalidate_document_upload_token(self):
        self.write({
            'document_upload_token': False,
            'document_upload_token_expiry': False,
        })

    def _get_documents_needing_upload(self):
        self.ensure_one()
        return self.document_review_ids.filtered('has_issue')

    @api.model
    def _find_by_document_upload_token(self, token):
        """Return the admission for a valid public upload token, or empty recordset."""
        token = (token or '').strip()
        if not token:
            return self.browse()
        admission = self.sudo().search([
            ('document_upload_token', '=', token),
        ], limit=1)
        if not admission:
            return self.browse()
        if admission.state != 'pending_applicant':
            return self.browse()
        expiry = admission.document_upload_token_expiry
        if expiry and expiry < fields.Datetime.now():
            return self.browse()
        return admission

    def _send_document_upload_request_email(self):
        template = self.env.ref(
            'kaierp.email_template_admission_document_upload',
            raise_if_not_found=False,
        )
        if not template:
            return
        for admission in self:
            if not admission.email:
                continue
            template.send_mail(admission.id, force_send=True)

    def _notify_registrars_document_resubmitted(self, uploaded_labels):
        """Inbox note for registrar users when applicant uploads documents."""
        self.ensure_one()
        registrar_users = self._get_registrar_users()
        labels = ', '.join(uploaded_labels) if uploaded_labels else _('documents')
        body = Markup(_(
            'Applicant uploaded replacement file(s) via the secure link: '
            '<strong>%(labels)s</strong>. Please re-verify on the Documents tab.',
            labels=escape(labels),
        ))
        partner_ids = registrar_users.mapped('partner_id').ids if registrar_users else []
        message = self.message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
            partner_ids=partner_ids or None,
        )
        if partner_ids and message:
            self.env['mail.notification'].sudo().search([
                ('mail_message_id', '=', message.id),
            ]).unlink()
            recipients_data = [{
                'active': True,
                'email_normalized': user.partner_id.email_normalized,
                'id': user.partner_id.id,
                'uid': user.id,
                'notif': 'inbox',
                'is_follower': True,
                'lang': user.lang or self.env.lang,
                'name': user.partner_id.name,
                'groups': user.group_ids.ids,
                'share': False,
                'type': 'user',
                'ushare': False,
            } for user in registrar_users]
            self._notify_thread_by_inbox(message, recipients_data)

    def apply_public_document_uploads(self, uploads):
        """
        Apply files from the public upload page.

        :param uploads: list of dicts with keys:
            document_code, filename, content (bytes)
        :return: list of document labels successfully stored
        """
        self.ensure_one()
        if self.state != 'pending_applicant':
            raise ValidationError(_('This upload link is no longer active.'))
        expiry = self.document_upload_token_expiry
        if expiry and expiry < fields.Datetime.now():
            raise ValidationError(_('This upload link has expired.'))

        issue_lines = {
            line.document_code: line
            for line in self._get_documents_needing_upload()
        }
        if not issue_lines:
            raise ValidationError(_('There are no documents waiting for upload.'))

        max_bytes = 10 * 1024 * 1024  # 10 MB per file
        field_vals = {}
        uploaded_labels = []
        chatter_attachments = []

        for item in uploads:
            code = (item.get('document_code') or '').strip()
            content = item.get('content') or b''
            filename = (item.get('filename') or 'document').strip() or 'document'
            if code not in issue_lines or not content:
                continue
            if code not in self._fields:
                continue
            if len(content) > max_bytes:
                raise ValidationError(_(
                    'File "%(name)s" is too large (max 10 MB).',
                    name=filename,
                ))
            field_vals[code] = base64.b64encode(content)
            label = issue_lines[code].document_label or code
            uploaded_labels.append(label)
            chatter_attachments.append((filename, content))

        if not field_vals:
            raise ValidationError(_('Please choose at least one file to upload.'))

        self.write(field_vals)
        for code in field_vals:
            line = issue_lines[code]
            note = (line.review_notes or '').strip()
            resubmit_note = _('Resubmitted by applicant via upload link.')
            line.write({
                'has_issue': False,
                'is_verified': False,
                'review_notes': ('%s %s' % (note, resubmit_note)).strip() if note else resubmit_note,
            })

        self.message_post(
            body=Markup(_(
                'Applicant submitted document(s) via secure upload link: %s',
            ) % escape(', '.join(uploaded_labels))),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
            attachments=chatter_attachments,
        )
        self._notify_registrars_document_resubmitted(uploaded_labels)
        return uploaded_labels

    def action_request_applicant_response(self):
        self._check_state('initial_review')
        if not self.document_review_ids.filtered('has_issue'):
            raise ValidationError(_(
                'Check "Issue" on at least one document before requesting a response.',
            ))
        if not self.email:
            raise ValidationError(_(
                'This application has no email address. Add one before sending the upload link.',
            ))
        self._generate_document_upload_token()
        self.write({'state': 'pending_applicant'})
        self._send_document_upload_request_email()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Upload link sent'),
                'message': _(
                    'An email with a secure document upload link was sent to %s.',
                ) % self.email,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_resend_document_upload_link(self):
        """Refresh the token and email the applicant again."""
        self.ensure_one()
        self._check_state('pending_applicant')
        if not self.document_review_ids.filtered('has_issue'):
            raise ValidationError(_(
                'There are no documents marked with Issue. Mark issues before resending the link.',
            ))
        if not self.email:
            raise ValidationError(_('This application has no email address.'))
        self._generate_document_upload_token()
        self._send_document_upload_request_email()
        self.message_post(
            body=_('Document upload link resent to %s.') % self.email,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Upload link resent'),
                'message': _('A new secure upload link was emailed to %s.') % self.email,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_resume_initial_review(self):
        self._check_state('pending_applicant')
        self._invalidate_document_upload_token()
        self.write({'state': 'initial_review'})

    def action_move_to_exam_interview(self):
        self._check_state('initial_review', 'pending_applicant')
        unverified = self.document_review_ids.filtered(
            lambda d: not d.is_verified and not d.has_issue,
        )
        if unverified:
            raise ValidationError(_(
                'Verify every document (checkmark) or mark an issue before proceeding.',
            ))
        if self.document_review_ids.filtered('has_issue'):
            raise ValidationError(_(
                'Resolve document issues or request applicant response before proceeding.',
            ))
        self._invalidate_document_upload_token()
        self.write({'state': 'pending_exam_interview'})

    def action_schedule_interview(self):
        self._check_state('pending_exam_interview')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Interview'),
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': _('Interview — %s') % self.name,
                'default_description': _('Admission interview for applicant %s') % self.reference,
            },
        }

    def action_deny_admission(self):
        self._check_state('pending_exam_interview')
        if self.exam_pass != 'fail' and self.interview_pass != 'fail':
            raise ValidationError(_(
                'Mark the exam or interview as Fail before denying admission.',
            ))
        self.write({
            'state': 'admission_denied',
            'decision_date': fields.Date.today(),
            'document_upload_token': False,
            'document_upload_token_expiry': False,
        })

    # Fields copied from admission → student (excludes exam accommodation & workflow).
    _ADMISSION_TO_STUDENT_FIELDS = (
        'title', 'first_name', 'middle_name', 'last_name',
        'course', 'study_mode',
        'whatsapp_number', 'date_of_birth', 'gender', 'nationality', 'age',
        'marital_status', 'plan_married_during_study',
        'email', 'mobile_number', 'phone_number',
        'postal_address', 'state_name', 'zip_code', 'city', 'country_id',
        'has_different_physical_address', 'physical_address',
        'emergency_title', 'emergency_name', 'emergency_relationship', 'emergency_mobile',
        'church_name', 'church_location', 'church_denomination', 'church_ministry_type',
        'is_ordained', 'church_financial_support', 'graduated_seminary_last_two_years',
        'working_for_organisation',
        'personal_reference_1', 'personal_reference_2', 'personal_reference_3',
        'class_x_year', 'diploma_after_class_x', 'class_xii_diploma_year',
        'has_undergraduate_theology', 'has_undergraduate_non_theology',
        'has_postgraduate_theology', 'has_postgraduate_non_theology',
        'has_doctoral_non_theology',
        'monthly_support_inr', 'monthly_support_usd', 'has_financial_sponsor',
        'financial_supporter_role', 'financial_supporter_name', 'financial_supporter_relation',
        'financial_supporter_email', 'financial_supporter_phone', 'financial_supporter_address',
        'father_name', 'father_occupation', 'mother_name', 'mother_occupation',
        'parents_born_again', 'parents_believers',
        'family_postal_addresses', 'family_email_addresses', 'family_contact_details',
        'has_children',
        'religious_background_birth', 'believers_baptism', 'called_to_ministry',
        'read_doctrinal_statement', 'agree_doctrinal_statement',
        'currently_employed', 'active_christian_ministry', 'how_knew_seminary',
        'blood_group', 'height_cm', 'weight_kg', 'allergies',
        'chronic_illness', 'prolonged_medication', 'vision_hearing_problem',
        'uses_tobacco', 'uses_intoxicants', 'suffers_sleeplessness',
        'psychiatric_care_history', 'other_medical_problems',
        'photo',
    )

    def _safe_student_selection(self, field_name, value):
        """Return a selection value only if it exists on school.student."""
        if not value:
            return value
        field = self.env['school.student']._fields.get(field_name)
        if field and field.type == 'selection':
            valid = dict(field._description_selection(self.env))
            return value if value in valid else False
        return value

    def _get_student_copy_vals(self, include_student_meta=False):
        """Map mirrored admission fields onto school.student values."""
        self.ensure_one()
        Student = self.env['school.student']
        vals = {}
        for fname in self._ADMISSION_TO_STUDENT_FIELDS:
            if fname not in Student._fields:
                continue
            student_field = Student._fields[fname]
            value = self[fname]
            if student_field.type == 'many2one':
                vals[fname] = value.id if value else False
            elif student_field.type == 'selection':
                vals[fname] = self._safe_student_selection(fname, value)
            else:
                vals[fname] = value

        if include_student_meta:
            academic_year = (
                str(self.application_date.year)
                if self.application_date
                else str(fields.Date.today().year)
            )
            vals.update({
                'admission_id': self.id,
                'academic_year': academic_year,
                'admission_date': fields.Date.today(),
                'state': 'active',
            })
            if self.registration_number:
                vals['student_id'] = self.registration_number
            if self.partner_id:
                vals['partner_id'] = self.partner_id.id
        return vals

    def _prepare_student_vals(self):
        """Map admission fields to the current school.student schema."""
        self.ensure_one()
        return self._get_student_copy_vals(include_student_meta=True)

    def action_accept_and_create_student(self):
        """Accept applicant and create the student profile in one step."""
        self.ensure_one()
        self._check_state('pending_exam_interview')
        if self.exam_pass != 'pass' or self.interview_pass != 'pass':
            raise ValidationError(_(
                'Both exam and interview must be marked Pass before acceptance.',
            ))
        if self.student_id:
            raise ValidationError(_('A student record already exists for this applicant.'))
        if not self.registration_number:
            self._assign_registration_number()

        student = self.env['school.student'].create(self._prepare_student_vals())

        self.write({
            'student_id': student.id,
            'state': 'accepted',
            'decision_date': fields.Date.today(),
            'document_upload_token': False,
            'document_upload_token_expiry': False,
        })

        student.message_post(
            body=_('Student created from admission application %s') % self.reference,
        )

        template = self.env.ref(
            'kaierp.email_template_admission_approved', raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Student Profile'),
            'res_model': 'school.student',
            'res_id': student.id,
            'view_mode': 'form',
        }

    def _check_state(self, *allowed_states):
        self.ensure_one()
        if self.state not in allowed_states:
            labels = ', '.join(
                dict(self._fields['state'].selection).get(s, s) for s in allowed_states
            )
            raise ValidationError(_(
                'This action is only available when the application is in: %s',
            ) % labels)
