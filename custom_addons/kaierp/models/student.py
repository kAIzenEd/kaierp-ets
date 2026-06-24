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

    # ── Identity ──────────────────────────────────────────────
    name = fields.Char(string='Full Name', compute='_compute_name', store=True, tracking=True)
    student_id = fields.Char(
        string='Student ID', copy=False, tracking=True,
        help='Unique identifier for student. Set during import or manually in UI. Cannot be changed after creation.'
    )
    class_id = fields.Many2one('school.class', string='Academic Class', required=False)
    # grade_label = fields.Char(string='Class / Grade', tracking=True)
    roll_number = fields.Char(string='Roll Number')
    first_name = fields.Char(string='First Name', tracking=True)
    last_name = fields.Char(string='Last Name', tracking=True)
    student_type = fields.Selection([
        ('day_scholar', 'Day Scholar'),
        ('boarding', 'Boarding'),
        ('hostel', 'Hostel'),
        ('other', 'Other'),
    ], string='Student Type')
    id_status = fields.Selection([
        ('AADHAAR', 'Need AADHAAR'),
        ('PEN', 'Need PEN'),
        ('APAAR', 'Need APAAR'),
        ('ready', 'IDs Ready'),
    ], string='ID Status')
    aadhaar_number = fields.Char(string='AADHAAR Number')
    central_pen = fields.Char(string='Student Central PEN')
    aapaar_id = fields.Char(string='APAAR ID #')
    enrollment_year = fields.Char(string='Enrollment Year')
    previous_school = fields.Char(string='Previous School')
    photo = fields.Binary(string='Photo', attachment=True)
    photo_filename = fields.Char(string='Photo Filename')

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender', required=True, tracking=True)

    date_of_birth = fields.Date(string='Date of Birth', required=True, tracking=True)
    dob_udise_aadhaar = fields.Date(string='DOB as per UDISE+ & AADHAAR')
    birthday = fields.Char(string='Birthday (dd/mm/yyyy)', compute='_compute_birthday', store=False)
    age = fields.Integer(string='Age (Rounded)', compute='_compute_age', store=False)
    age_exact = fields.Char(string='Age (Exact)', compute='_compute_age_exact', store=False)
    birth_month = fields.Char(string='Birth Month', compute='_compute_birth_date_parts', store=False)
    birth_day = fields.Char(string='Birth Day', compute='_compute_birth_date_parts', store=False)
    nationality = fields.Many2one('res.country', string='Nationality')
    blood_group = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ], string='Blood Group')
    house = fields.Char(string='House')
    siblings_at_htrs = fields.Integer(string='Siblings at HTRS')
    family_id = fields.Char(string='Family ID')
    caste = fields.Selection([
        ('sc', 'SC'), ('st', 'ST'), ('obc', 'OBC'),
        ('oec', 'OEC'), ('general', 'General'),
    ], string='Caste')
    tribe = fields.Char(string='Tribe')
    mother_tongue = fields.Char(string='Mother Tongue')
    religious_community = fields.Char(string='Religious Community')
    apl_bpl = fields.Selection([
        ('apl', 'APL'), ('bpl', 'BPL'), ('ant', 'Antodaya'),('nrc', 'Not in ration'),
    ], string='APL / BPL')
    village_of_family = fields.Char(string='Village of Family')

    # ── Contact ───────────────────────────────────────────────
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    permanent_state_id = fields.Many2one('res.country.state', string='Permanent Address (State)')
    zip = fields.Char(string='ZIP')

    # ── Guardian ──────────────────────────────────────────────
    guardian_name = fields.Char(string='Guardian Name')
    guardian_relation = fields.Char(string='Relationship to Student')
    guardian_phone = fields.Char(string='Guardian Phone')
    guardian_email = fields.Char(string='Guardian Email')
    guardian_occupation = fields.Char(string='Guardian Occupation')
    guardian_whatsapp = fields.Boolean(string='Guardian On WhatsApp')

    father_name = fields.Char(string="Father's Name")
    father_mobile = fields.Char(string="Father's Mobile Number")
    father_whatsapp = fields.Boolean(string='Father On WhatsApp?')
    father_occupation = fields.Char(string="Father's Occupation")
    father_education = fields.Char(string="Father's Education Level")

    mother_name = fields.Char(string="Mother's Name")
    mother_mobile = fields.Char(string="Mother's Mobile Number")
    mother_whatsapp = fields.Boolean(string='Mother On WhatsApp?')
    mother_occupation = fields.Char(string="Mother's Occupation")
    mother_education = fields.Char(string="Mother's Education Level")

    family_income = fields.Float(string='Yearly Family Income', digits=(16, 2))

    other_contact_name = fields.Char(string='Other Contact Name')
    other_contact_relation = fields.Char(string='Other Contact Relationship')
    other_contact_mobile = fields.Char(string='Other Contact Mobile Number')
    other_contact_whatsapp = fields.Boolean(string='OC On WhatsApp')
    other_contact_school_whatsapp_group = fields.Boolean(string='In SCHOOL WhatsApp Group')
    other_contact_hostel_whatsapp_group = fields.Boolean(string='In HOSTEL WhatsApp Group')
    other_contact_class_whatsapp_group = fields.Boolean(string='In CLASS WhatsApp Group')

    guardian_school_whatsapp_group = fields.Boolean(string='In SCHOOL WhatsApp Group')
    guardian_hostel_whatsapp_group = fields.Boolean(string='In HOSTEL WhatsApp Group')
    guardian_class_whatsapp_group = fields.Boolean(string='In CLASS WhatsApp Group')
    
    father_school_whatsapp_group = fields.Boolean(string='In SCHOOL WhatsApp Group')
    father_hostel_whatsapp_group = fields.Boolean(string='In HOSTEL WhatsApp Group')
    father_class_whatsapp_group = fields.Boolean(string='In CLASS WhatsApp Group')
    
    mother_school_whatsapp_group = fields.Boolean(string='In SCHOOL WhatsApp Group')
    mother_hostel_whatsapp_group = fields.Boolean(string='In HOSTEL WhatsApp Group')
    mother_class_whatsapp_group = fields.Boolean(string='In CLASS WhatsApp Group')

    # ── Academic ──────────────────────────────────────────────
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

    # ── Medical ───────────────────────────────────────────────
    medical_conditions = fields.Text(string='Medical Conditions')
    allergies = fields.Text(string='Allergies')
    doctor_name = fields.Char(string='Doctor Name')
    doctor_phone = fields.Char(string='Doctor Phone')

    # ── Notes ─────────────────────────────────────────────────
    notes = fields.Html(string='Notes')

    # # ── Related res.partner (for mail/calendar integration) ───
    # partner_id = fields.Many2one('res.partner', string='Related Contact', copy=False)

    # ─── Computes ─────────────────────────────────────────────
    @api.depends('first_name', 'last_name')
    def _compute_name(self):
        for rec in self:
            rec.name = ' '.join(filter(None, [rec.first_name, rec.last_name])).strip()

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year - (
                    (today.month, today.day) < (
                        rec.date_of_birth.month, rec.date_of_birth.day
                    )
                )
            else:
                rec.age = 0

    @api.depends('date_of_birth')
    def _compute_birthday(self):
        for rec in self:
            rec.birthday = rec.date_of_birth.strftime('%d/%m/%Y') if rec.date_of_birth else ''

    @api.depends('date_of_birth')
    def _compute_age_exact(self):
        for rec in self:
            if rec.date_of_birth:
                today = date.today()
                dob = rec.date_of_birth
                years = today.year - dob.year - (
                    (today.month, today.day) < (dob.month, dob.day)
                )
                months = today.month - dob.month - (today.day < dob.day)
                if months < 0:
                    months += 12
                rec.age_exact = f"{years} years {months} months"
            else:
                rec.age_exact = ''

    @api.depends('date_of_birth')
    def _compute_birth_date_parts(self):
        for rec in self:
            if rec.date_of_birth:
                rec.birth_month = rec.date_of_birth.strftime('%B')
                rec.birth_day = str(rec.date_of_birth.day)
            else:
                rec.birth_month = ''
                rec.birth_day = ''

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
            # Compute full name from first and last name
            full_name = ' '.join(
                [vals.get('first_name', ''), vals.get('last_name', '')]
            ).strip()
            if full_name:
                vals['name'] = full_name
            else:
                vals['name'] = _('New')
        return super().create(vals_list)

    def write(self, vals):
        # Prevent editing student_id after record creation (keep it as immutable unique key)
        if 'student_id' in vals:
            for rec in self:
                if rec.student_id and rec.student_id != vals['student_id']:
                    raise ValidationError(
                        _('Student ID cannot be changed after creation. '
                          'Current: %s | Attempted: %s') % (rec.student_id, vals['student_id'])
                    )
        
        if 'first_name' in vals or 'last_name' in vals:
            for rec in self:
                first_name = vals.get('first_name', rec.first_name)
                last_name = vals.get('last_name', rec.last_name)
                if not first_name and not last_name:
                    continue
                vals['name'] = ' '.join(filter(None, [first_name, last_name])).strip()
        return super().write(vals)

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
        """Open calendar to schedule meeting with student/guardian."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Meeting'),
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_ids': [(4, self.partner_id.id)] if self.partner_id else [],
                'default_name': _('Meeting with %s') % self.name,
            },
        }