# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class SchoolStudent(models.Model):
    _name = 'school.student'
    _description = 'Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name asc'

    # ── Identity (student-specific) ───────────────────────────
    name = fields.Char(string='Full Name', compute='_compute_name', store=True, tracking=True)
    student_id = fields.Char(
        string='Student ID', copy=False, tracking=True,
        help='Assigned from the admission registration number when the applicant is accepted.',
    )
    ata_number = fields.Char(
        string='ATA Number', tracking=True,
        help='Manual reference number. Not linked to other records.',
    )
    admission_id = fields.Many2one(
        'school.admission', string='Source Application', copy=False, readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Billing Contact', copy=False, tracking=True,
        help='Contact used for invoices and payments.',
    )
    class_id = fields.Many2one('school.class', string='Academic Class')
    roll_number = fields.Char(string='Roll Number')
    photo = fields.Binary(string='Photo', attachment=True)
    photo_filename = fields.Char(string='Photo Filename')

    # ── Academic choice (mirrors admission) ───────────────────
    course = fields.Selection([
        ('macs', 'Master of Arts in Christian Studies (MACS)'),
        ('pgdbs', 'Postgraduate Diploma in Biblical Studies (PGDBS)'),
        ('mabs', 'Master of Arts in Biblical Studies (MABS)'),
        ('mdiv', 'Master of Divinity (MDIV)'),
        ('macc', 'Master of Arts in Christian Counselling (MACC)'),
        ('mth', 'Master of Theology (MTH)'),
    ], string='Course', tracking=True)
    study_mode = fields.Selection([
        ('online', 'Online'),
        ('residential', 'Residential'),
    ], string='Study Mode', tracking=True)
    year_of_study = fields.Char(
        string='Year of Study',
        help='e.g. 1st Year, 2nd Year',
        tracking=True,
    )
    ets_campus_location = fields.Char(
        string='Location in ETS Campus',
        tracking=True,
    )
    family_quarters = fields.Char(
        string='Family Quarters',
        help='Family quarters assignment or reference, if applicable.',
        tracking=True,
    )
    current_residence = fields.Char(
        string='Current Residence',
        tracking=True,
    )

    # ── Personal information (mirrors admission) ────────────
    title = fields.Selection([
        ('doctor', 'Doctor'),
        ('madam', 'Madam'),
        ('miss', 'Miss'),
        ('mrs', 'Mrs.'),
        ('mister', 'Mister'),
        ('mr', 'Mr'),
        ('professor', 'Professor'),
    ], string='Title')
    first_name = fields.Char(string='First Name', tracking=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name', tracking=True)
    whatsapp_number = fields.Char(string='WhatsApp Number')
    date_of_birth = fields.Date(string='Date of Birth', required=True, tracking=True)
    birth_day = fields.Integer(
        string='Day of Birth', compute='_compute_birth_parts', store=True, readonly=True,
    )
    birth_month = fields.Integer(
        string='Month of Birth', compute='_compute_birth_parts', store=True, readonly=True,
    )
    birth_year = fields.Integer(
        string='Year of Birth', compute='_compute_birth_parts', store=True, readonly=True,
    )
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', required=True, tracking=True)
    nationality = fields.Many2one('res.country', string='Nationality')
    age = fields.Integer(string='Age')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('separated', 'Separated'),
        ('widowed', 'Widowed'),
    ], string='Marital Status')
    plan_married_during_study = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string='Plan to Marry During Study Period?')

    # ── Contact information (mirrors admission) ───────────────
    email = fields.Char(string='Personal Email Address', tracking=True)
    ets_email = fields.Char(string='ETS Email Address', tracking=True)
    mobile_number = fields.Char(string='Mobile Number')
    phone_number = fields.Char(string='Personal Phone Number')
    postal_address = fields.Text(string='Permanent Address')
    state_name = fields.Char(string='State / UT')
    zip_code = fields.Char(string='Zip / Postal Code')
    city = fields.Char(string='City')
    country_id = fields.Many2one('res.country', string='Country')
    has_different_physical_address = fields.Boolean(string='Different Physical Address')
    physical_address = fields.Text(string='Physical Address')

    # ── Emergency contact (mirrors admission) ─────────────────
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
    emergency_mobile = fields.Char(string='Emergency Contact Phone Number')
    emergency_email = fields.Char(string='Emergency Contact Email')

    # ── Church background (mirrors admission) ─────────────────
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

    # ── References (mirrors admission) ────────────────────────
    personal_reference_1 = fields.Text(string='Personal Reference 1')
    personal_reference_2 = fields.Text(string='Personal Reference 2')
    personal_reference_3 = fields.Text(string='Personal Reference 3')

    # ── Academic / professional qualification (mirrors admission)
    class_x_year = fields.Char(string='Class X (Year of Completion)')
    diploma_after_class_x = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='Diploma After Class X Instead of Class XII?',
    )
    class_xii_diploma_year = fields.Char(string='Diploma / Class XII (Year of Completion)')
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

    # ── Financial information (mirrors admission) ─────────────
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

    # ── Family (mirrors admission) ────────────────────────────
    father_name = fields.Char(string="Father's Name")
    father_occupation = fields.Char(string="Father's Occupation")
    mother_name = fields.Char(string="Mother's Name")
    mother_occupation = fields.Char(string="Mother's Occupation")
    parents_born_again = fields.Text(string="Parents 'Born Again'?")
    parents_believers = fields.Text(string='Parents Believers in Jesus Christ?')
    family_postal_addresses = fields.Text(string='Family Postal Address(es)')
    family_email_addresses = fields.Text(string='Family Email Addresses')
    family_contact_details = fields.Text(string='Family Contact Details')
    has_children = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Has Children?')

    # ── Spiritual identity (mirrors admission) ────────────────
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

    # ── Work experience (mirrors admission) ───────────────────
    currently_employed = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Currently Employed?',
    )
    active_christian_ministry = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string='Active Christian Ministry Participation?',
    )
    how_knew_seminary = fields.Text(string='How Did You Learn About ETS?')

    # ── Health information (mirrors admission) ────────────────
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

    # ── Student academic status ───────────────────────────────
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('graduated', 'Graduated'),
        ('expelled', 'Expelled'),
        ('transferred', 'Transferred'),
    ], string='Status', default='active', tracking=True)

    admission_date = fields.Date(string='Admission Date', default=fields.Date.today)
    graduation_date = fields.Date(string='Expected Graduation')
    academic_year = fields.Char(string='Academic Year')

    enrollment_ids = fields.One2many(
        'school.enrollment', 'student_id', string='Enrollments'
    )
    enrollment_count = fields.Integer(
        string='Classes', compute='_compute_enrollment_count'
    )

    grade_ids = fields.One2many('school.grade', 'student_id', string='Grades')
    grade_count = fields.Integer(string='# Grades', compute='_compute_grade_count')

    gpa = fields.Float(string='GPA', compute='_compute_gpa', digits=(5, 2), store=True)

    attendance_ids = fields.One2many(
        'school.attendance', 'student_id', string='Attendance'
    )
    attendance_percentage = fields.Float(
        string='Attendance %', compute='_compute_attendance', digits=(5, 2)
    )

    fee_ids = fields.One2many('school.fee', 'student_id', string='Fees')
    total_fees_due = fields.Float(
        string='Total Due', compute='_compute_fees', digits=(16, 2)
    )

    # ── Notes ─────────────────────────────────────────────────
    notes = fields.Html(string='Notes')

    # ── Chaplain / Field Education (care log) ──────────────────
    chaplain_note_ids = fields.One2many(
        'school.student.care.note', 'student_id', string='Chaplain Notes',
        domain=[('section', '=', 'chaplain')],
        context={'default_section': 'chaplain'},
    )
    chaplain_document_ids = fields.One2many(
        'school.student.care.document', 'student_id', string='Chaplain Documents',
        domain=[('section', '=', 'chaplain')],
        context={'default_section': 'chaplain'},
    )
    field_education_note_ids = fields.One2many(
        'school.student.care.note', 'student_id', string='Field Education Notes',
        domain=[('section', '=', 'field_education')],
        context={'default_section': 'field_education'},
    )
    field_education_document_ids = fields.One2many(
        'school.student.care.document', 'student_id', string='Field Education Documents',
        domain=[('section', '=', 'field_education')],
        context={'default_section': 'field_education'},
    )

    def _action_add_care_note(self, section, title):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'school.student.care.note',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_id': self.id,
                'default_section': section,
            },
        }

    def _action_add_care_document(self, section, title):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'school.student.care.document',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_id': self.id,
                'default_section': section,
            },
        }

    def action_add_chaplain_note(self):
        return self._action_add_care_note('chaplain', _('Add Chaplain Note'))

    def action_add_chaplain_document(self):
        return self._action_add_care_document('chaplain', _('Add Chaplain Document'))

    def action_add_field_education_note(self):
        return self._action_add_care_note('field_education', _('Add Field Education Note'))

    def action_add_field_education_document(self):
        return self._action_add_care_document(
            'field_education', _('Add Field Education Document'),
        )

    # ─── Computes ─────────────────────────────────────────────
    @api.depends('first_name', 'middle_name', 'last_name')
    def _compute_name(self):
        for rec in self:
            rec.name = ' '.join(
                filter(None, [rec.first_name, rec.middle_name, rec.last_name]),
            ).strip()

    @api.depends('enrollment_ids')
    def _compute_enrollment_count(self):
        for rec in self:
            rec.enrollment_count = len(rec.enrollment_ids)

    @api.depends('grade_ids')
    def _compute_grade_count(self):
        for rec in self:
            rec.grade_count = len(rec.grade_ids)

    @api.depends('grade_ids.gpa_points')
    def _compute_gpa(self):
        for rec in self:
            grades = rec.grade_ids.filtered(lambda g: g.gpa_points > 0)
            rec.gpa = sum(grades.mapped('gpa_points')) / len(grades) if grades else 0.0

    @api.depends('attendance_ids')
    def _compute_attendance(self):
        for rec in self:
            total = len(rec.attendance_ids)
            present = len(rec.attendance_ids.filtered(lambda a: a.state == 'present'))
            rec.attendance_percentage = (present / total * 100) if total else 0.0

    @api.depends('fee_ids.amount_due', 'fee_ids.amount_paid')
    def _compute_fees(self):
        for rec in self:
            rec.total_fees_due = sum(
                rec.fee_ids.mapped(lambda f: f.amount_due - f.amount_paid)
            )

    # ─── ORM ──────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        """Create student records.
        
        Student ID is accepted as-is from import or user input.
        No auto-generation or modification of student_id.
        """
        for vals in vals_list:
            full_name = ' '.join(filter(None, [
                vals.get('first_name', ''),
                vals.get('middle_name', ''),
                vals.get('last_name', ''),
            ])).strip()
            vals['name'] = full_name or _('New')
        students = super().create(vals_list)
        students._ensure_partner()
        return students

    def write(self, vals):
        if 'student_id' in vals:
            for rec in self:
                if rec.student_id and rec.student_id != vals['student_id']:
                    raise ValidationError(
                        _('Student ID cannot be changed after creation. '
                          'Current: %s | Attempted: %s') % (rec.student_id, vals['student_id'])
                    )
        return super().write(vals)

    def _ensure_partner(self):
        """Ensure each student has a billing contact for invoicing."""
        Partner = self.env['res.partner']
        for student in self:
            record_ref = student.student_id
            if not record_ref and student.admission_id:
                record_ref = student.admission_id.registration_number
            if not student.email:
                continue
            if student.admission_id:
                student.admission_id._ensure_applicant_partner()
            partner = Partner.find_or_create_school_billing_partner(
                record_ref=record_ref,
                name=student.name or student.email,
                email=student.email,
                phone=(
                    student.mobile_number
                    or student.whatsapp_number
                    or student.phone_number
                ),
                current_partner=student.partner_id,
            )
            student.partner_id = partner.id

    def action_assign_fees(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Fees'),
            'res_model': 'school.assign.fee.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_student_id': self.id},
        }

    def action_create_combined_invoice(self):
        """Create one customer invoice for all uninvoiced fees on this student."""
        self.ensure_one()
        self._ensure_partner()
        pending_fees = self.fee_ids.filtered(lambda f: not f.invoice_id)
        if not pending_fees:
            raise ValidationError(_(
                'There are no pending fees to invoice for %s.',
            ) % self.name)
        return pending_fees.action_create_invoice()

    def action_view_admission(self):
        self.ensure_one()
        if not self.admission_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Admission Application'),
            'res_model': 'school.admission',
            'res_id': self.admission_id.id,
            'view_mode': 'form',
        }

    def action_view_fees(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Student Fees'),
            'res_model': 'school.fee',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

    @api.depends('date_of_birth')
    def _compute_birth_parts(self):
        for rec in self:
            if rec.date_of_birth:
                rec.birth_day = rec.date_of_birth.day
                rec.birth_month = rec.date_of_birth.month
                rec.birth_year = rec.date_of_birth.year
            else:
                rec.birth_day = 0
                rec.birth_month = 0
                rec.birth_year = 0

    @api.constrains('date_of_birth')
    def _check_dob(self):
        for rec in self:
            if rec.date_of_birth and rec.date_of_birth > date.today():
                raise ValidationError(_('Date of birth cannot be in the future.'))

    def action_set_active(self):
        self.write({'state': 'active'})

    def action_set_graduated(self):
        self.write({'state': 'graduated', 'graduation_date': fields.Date.today()})

    def action_view_enrollments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enrollments'),
            'res_model': 'school.enrollment',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

    def action_view_grades(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Grades'),
            'res_model': 'school.grade',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id},
        }

    # ── Transcript helpers (ETS layout & grading) ─────────────
    # Percentage bands from official ETS transcript legend.
    ETS_GRADE_SCALE = [
        # (min %, letter, grade points per credit hour)
        (98, 'A+', 4.0),
        (94, 'A', 3.75),
        (90, 'A-', 3.5),
        (86, 'B+', 3.25),
        (83, 'B', 3.0),
        (80, 'B-', 2.75),
        (77, 'C+', 2.5),
        (74, 'C', 2.25),
        (70, 'C-', 2.0),
        (0, 'F', 0.0),
    ]
    ETS_LETTER_POINTS = {
        'A+': 4.0, 'A': 3.75, 'A-': 3.5,
        'B+': 3.25, 'B': 3.0, 'B-': 2.75,
        'C+': 2.5, 'C': 2.25, 'C-': 2.0,
        'F': 0.0,
    }
    ETS_YEAR_LABELS = (
        'FIRST YEAR', 'SECOND YEAR', 'THIRD YEAR',
        'FOURTH YEAR', 'FIFTH YEAR', 'SIXTH YEAR',
    )
    ETS_SEMESTER_ORDER = ('summer', 'fall', 'spring')

    def _ets_grade_from_percentage(self, percentage):
        """Map percentage → ETS letter + points-per-credit."""
        pct = percentage or 0.0
        for threshold, letter, points in self.ETS_GRADE_SCALE:
            if pct >= threshold:
                return letter, points
        return 'F', 0.0

    def _ets_letter_from_gpa(self, gpa):
        """Nearest ETS letter for a cumulative GPA (4.0 scale)."""
        if gpa is None or gpa <= 0:
            return ''
        return min(
            self.ETS_LETTER_POINTS.items(),
            key=lambda item: abs(item[1] - gpa),
        )[0]

    def _format_transcript_date(self, value):
        if not value:
            return ''
        return value.strftime('%d %B %Y').lstrip('0')

    def get_transcript_data(self):
        """Structured payload for the ETS-style official transcript PDF."""
        self.ensure_one()
        company = self.env.company
        course_label = ''
        if self.course:
            course_label = dict(self._fields['course'].selection).get(self.course, '')
            if '(' in course_label:
                course_label = course_label.split('(')[0].strip()

        finals = self.grade_ids.filtered(lambda g: g.assessment_type == 'final_grade')

        # year -> semester_key -> rows
        year_map = {}
        for grade in finals.sorted(
            key=lambda g: (
                g.academic_year or '',
                g.class_id.semester or '',
                g.class_id.code or '',
                g.id,
            )
        ):
            year = (grade.academic_year or '').strip() or _('Unspecified Year')
            sem_key = grade.class_id.semester or ''
            sem_label = ''
            if sem_key and grade.class_id._fields.get('semester'):
                sem_label = dict(grade.class_id._fields['semester'].selection).get(
                    sem_key, sem_key,
                )
            letter, points_per_credit = self._ets_grade_from_percentage(grade.percentage)
            credits = grade.class_id.credit_hours or 0
            quality_points = round(points_per_credit * credits, 2)
            year_bucket = year_map.setdefault(year, {})
            sem_bucket = year_bucket.setdefault(sem_key, {
                'semester_key': sem_key,
                'semester_label': (sem_label or _('Semester')).upper(),
                'rows': [],
            })
            sem_bucket['rows'].append({
                'code': grade.class_id.code or '',
                'title': grade.class_id.name or '',
                'credits': credits,
                'letter': letter,
                'points_per_credit': points_per_credit,
                'quality_points': quality_points,
                'is_fail': letter == 'F',
            })

        def _sem_sort_key(sem_key):
            try:
                return self.ETS_SEMESTER_ORDER.index(sem_key)
            except ValueError:
                return 99

        years = []
        sorted_year_keys = sorted(year_map.keys())
        for idx, year_key in enumerate(sorted_year_keys):
            semesters = []
            year_credits = 0.0
            year_quality = 0.0
            for sem_key in sorted(year_map[year_key].keys(), key=_sem_sort_key):
                block = year_map[year_key][sem_key]
                sem_credits = sum(r['credits'] for r in block['rows'])
                sem_quality = sum(r['quality_points'] for r in block['rows'])
                block['credits'] = sem_credits
                block['quality_points'] = sem_quality
                year_credits += sem_credits
                year_quality += sem_quality
                semesters.append(block)
            label = (
                self.ETS_YEAR_LABELS[idx]
                if idx < len(self.ETS_YEAR_LABELS)
                else _('YEAR %s') % (idx + 1)
            )
            years.append({
                'academic_year': year_key,
                'label': label,
                'semesters': semesters,
                'credits': year_credits,
                'quality_points': round(year_quality, 2),
            })

        all_rows = [
            r
            for year in years
            for sem in year['semesters']
            for r in sem['rows']
        ]
        total_credits = sum(r['credits'] for r in all_rows)
        total_quality = round(sum(r['quality_points'] for r in all_rows), 2)
        gpa = (total_quality / total_credits) if total_credits else 0.0

        company_address = ', '.join(
            part for part in [
                company.street or '',
                company.street2 or '',
                company.city or '',
                company.state_id.name if company.state_id else '',
                company.zip or '',
                company.country_id.name if company.country_id else '',
            ] if part
        )

        registrar = self.env['school.registrar'].sudo().search([
            ('state', '=', 'active'),
        ], limit=1)
        registrar_name = registrar.name if registrar else ''
        registrar_name = self.env['ir.config_parameter'].sudo().get_param(
            'kaierp.transcript_registrar_name', registrar_name,
        ) or registrar_name

        parent_org = self.env['ir.config_parameter'].sudo().get_param(
            'kaierp.transcript_parent_org',
            'Asian Christian Academy of India',
        )
        major = self.env['ir.config_parameter'].sudo().get_param(
            'kaierp.transcript_default_major', '',
        )

        enrolled_on = self.admission_date
        graduated_on = self.graduation_date if self.state == 'graduated' else False

        return {
            'student_name': self.name or '',
            'reg_no': self.student_id or self.roll_number or '',
            'ata_reg_no': self.ata_number or '',
            'dob': self._format_transcript_date(self.date_of_birth),
            'enrolled_on': self._format_transcript_date(enrolled_on),
            'graduated_on': self._format_transcript_date(graduated_on),
            'degree': course_label,
            'major': major,
            'institution_name': company.name or 'Evangelical Theological Seminary',
            'parent_org': parent_org,
            'institution_address': company_address or 'Jeemangalam, Bagalur, Hosur, Tamilnadu - 635103',
            'institution_email': company.email or 'ets@acaindia.org',
            'years': years,
            'total_credits': total_credits,
            'total_quality_points': total_quality,
            'gpa': gpa,
            'gpa_display': '%.2f' % gpa if total_credits else '',
            'average_course_grade': self._ets_letter_from_gpa(gpa) if total_credits else '',
            'registrar_name': registrar_name,
            'has_grades': bool(all_rows),
            'grading_legend': [
                ('A+', '100,99,98'),
                ('A', '97,96,95,94'),
                ('A-', '93,92,91,90'),
                ('B+', '89,88,87,86'),
                ('B', '85,84,83'),
                ('B-', '82,81,80'),
                ('C+', '79,78,77'),
                ('C', '76,75,74'),
                ('C-', '73,72,71,70'),
                ('F', '0–69'),
            ],
        }

    def action_print_transcript(self):
        """Generate the official academic transcript PDF (secretary / managers)."""
        return self.env.ref(
            'kaierp.action_report_transcript'
        ).report_action(self)

    def action_schedule_meeting(self):
        """Open calendar to schedule a meeting with the student."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Meeting'),
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': _('Meeting with %s') % self.name,
            },
        }