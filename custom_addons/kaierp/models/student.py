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
    applied_term = fields.Selection([
        ('2026_fall', '2026 - Fall'),
        ('2026_spring', '2026 - Spring'),
        ('2027_fall', '2027 - Fall'),
    ], string='Applied Term', tracking=True)
    study_mode = fields.Selection([
        ('online', 'Online'),
        ('residential', 'Residential'),
    ], string='Study Mode', tracking=True)

    # ── Personal information (mirrors admission) ────────────
    title = fields.Selection([
        ('doctor', 'Doctor'),
        ('madam', 'Madam'),
        ('miss', 'Miss'),
        ('mister', 'Mister'),
        ('mr', 'Mr'),
        ('professor', 'Professor'),
    ], string='Title')
    first_name = fields.Char(string='First Name', tracking=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name', tracking=True)
    whatsapp_number = fields.Char(string='WhatsApp Number')
    date_of_birth = fields.Date(string='Date of Birth', required=True, tracking=True)
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
    email = fields.Char(string='Email', tracking=True)
    mobile_number = fields.Char(string='Mobile Number')
    phone_number = fields.Char(string='Phone Number')
    postal_address = fields.Text(string='Postal Address')
    state_name = fields.Char(string='State')
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
    applicant_type = fields.Selection([
        ('international', 'International Applicants'),
        ('indian', 'Indian Applicants'),
    ], string='Applicant Type')
    marksheet_name = fields.Char(string='Name (as on Class X Mark-sheet)')
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
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
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
        return super().create(vals_list)

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
        Partner = self.env['res.partner'].sudo()
        for student in self:
            if student.partner_id:
                continue
            if student.admission_id and student.admission_id.partner_id:
                student.partner_id = student.admission_id.partner_id
                continue
            if not student.email:
                continue
            partner = Partner.search([('email', '=ilike', student.email)], limit=1)
            partner_vals = {
                'name': student.name or student.email,
                'email': student.email,
                'phone': student.mobile_number or student.whatsapp_number or student.phone_number,
            }
            if partner:
                partner.write({k: v for k, v in partner_vals.items() if v})
            else:
                partner = Partner.create({**partner_vals, 'type': 'contact'})
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

    def action_print_transcript(self):
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