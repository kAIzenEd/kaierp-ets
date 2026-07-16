# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class SchoolClass(models.Model):
    _name = 'school.class'
    # _description = 'Class'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name_full'
    _order = 'academic_year desc, name asc'

    name = fields.Char(string='Class Name', required=True, tracking=True)
    code = fields.Char(string='Class Code', required=True, copy=False, tracking=True)
    display_name_full = fields.Char(
        string='Full Name', compute='_compute_display_name_full', store=True
    )

    # subject = fields.Char(string='Subject', required=True)
    # description = fields.Html(string='Description')
    academic_year = fields.Char(
        string='Academic Year', required=True, tracking=True,
        default=lambda self: self._default_academic_year()
    )
    semester = fields.Selection([
        ('summer', 'Summer Semester'),
        ('fall', 'Fall Semester'),
        ('spring', 'Spring Semester'),
    ], string='Semester', required=True, default='fall')

    teacher_id = fields.Many2one(
        'school.teacher', string='Teacher', tracking=True
    )
    room = fields.Char(string='Room')
    schedule = fields.Char(string='Schedule', help='e.g. Mon/Wed/Fri 09:00–10:00')
    credit_hours = fields.Integer(string='Credit Hours', default=3)
    max_students = fields.Integer(string='Max Students', default=30)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open for Enrollment'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    enrollment_ids = fields.One2many(
        'school.enrollment', 'class_id', string='Enrolled Students'
    )
    enrolled_count = fields.Integer(
        string='Enrolled', compute='_compute_enrolled_count', store=True, compute_sudo=True
    )
    available_seats = fields.Integer(
        string='Available Seats', compute='_compute_enrolled_count', store=True, compute_sudo=True
    )

    grade_ids = fields.One2many('school.grade', 'class_id', string='Grades')
    attendance_ids = fields.One2many(
            'school.attendance', 'class_id', string='Attendance Records'
        )
    attendance_record_count = fields.Integer(
        string='# Attendance Rows',
        compute='_compute_attendance_record_count',
    )
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    syllabus = fields.Html(string='Syllabus')
    prerequisites = fields.Many2many(
        'school.class', 'school_class_prereq_rel',
        'class_id', 'prereq_id', string='Prerequisites'
    )

    # Calendar event link
    calendar_event_ids = fields.Many2many(
        'calendar.event', string='Calendar Events'
    )

    @api.model
    def _default_academic_year(self):
        from datetime import date
        y = date.today().year
        return f'{y}-{y + 1}'

    @api.depends('code', 'name', 'academic_year')
    def _compute_display_name_full(self):
        for rec in self:
            rec.display_name_full = f'[{rec.code}] {rec.name} ({rec.academic_year})'

    @api.depends('enrollment_ids', 'enrollment_ids.state')
    def _compute_enrolled_count(self):
        for rec in self:
            active = rec.enrollment_ids.filtered(
                lambda e: e.state in ('enrolled', 'completed')
            )
            rec.enrolled_count = len(active)
            rec.available_seats = max(0, rec.max_students - rec.enrolled_count)

    @api.depends('attendance_ids')
    def _compute_attendance_record_count(self):
        for rec in self:
            rec.attendance_record_count = len(rec.attendance_ids)
    
    @api.constrains('max_students')
    def _check_max(self):
        for rec in self:
            if rec.max_students < 1:
                raise ValidationError(_('Max students must be at least 1.'))

    def action_open_enrollment(self):
        self.write({'state': 'open'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_enroll_students(self):
        """Launch the enrollment wizard."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enroll Students'),
            'res_model': 'school.enroll.student.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_class_id': self.id},
        }

    def action_view_grades(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Grades — %s') % self.name,
            'res_model': 'school.grade',
            'view_mode': 'list,form',
            'domain': [('class_id', '=', self.id)],
            'context': {'default_class_id': self.id},
        }

    def action_view_attendance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attendance — %s') % self.name,
            'res_model': 'school.attendance',
            'view_mode': 'list,form',
            'domain': [('class_id', '=', self.id)],
            'context': {'default_class_id': self.id},
        }
    
    def _get_enrollments_for_attendance(self):
        """Active enrollments that should appear on an attendance sheet."""
        self.ensure_one()
        return self.enrollment_ids.filtered(
            lambda e: e.state in ('enrolled', 'completed') and e.student_id
        )
    
    def _ensure_attendance_sheet(self, attendance_date=None):
        """Create one ``school.attendance`` row per enrolled student for *attendance_date* (if missing)."""
        self.ensure_one()
        attendance_date = attendance_date or fields.Date.context_today(self)
        enrollments = self._get_enrollments_for_attendance()
        if not enrollments:
            raise UserError(_(
                'There are no students with status **Enrolled** or **Completed** in class "%(class_name)s".\n\n'
                'Add enrollments on the **Enrolled Students** tab, '
                'then take attendance again.',
                class_name=self.name,
            ))
        
        Attendance = self.env['school.attendance']
        existing = Attendance.search([
            ('class_id', '=', self.id),
            ('date', '=', attendance_date),
            ('student_id', 'in', enrollments.student_id.ids),
        ])
        existing_students = existing.mapped('student_id')
        to_create = []
        for enrollment in enrollments:
            if enrollment.student_id not in existing_students:
                to_create.append({
                    'student_id': enrollment.student_id.id,
                    'class_id': self.id,
                    'date': attendance_date,
                    'state': 'present',
                })
        if to_create:
            Attendance.create(to_create)
        return Attendance.search([
            ('class_id', '=', self.id),
            ('date', '=', attendance_date),
            ('student_id', 'in', enrollments.student_id.ids),
        ], order='student_id')

    def _action_open_attendance_list(self, attendance_date=None):
        """Open an editable list of attendance rows for this class and date."""
        self.ensure_one()
        attendance_date = attendance_date or fields.Date.context_today(self)
        records = self._ensure_attendance_sheet(attendance_date)
        list_view = self.env.ref('kaierp.view_school_attendance_take_list', raise_if_not_found=False)
        views = [(list_view.id, 'list')] if list_view else [(False, 'list')]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attendance — %s (%s)') % (self.name, attendance_date),
            'res_model': 'school.attendance',
            'view_mode': 'list',
            'views': views,
            'domain': [('id', 'in', records.ids)],
            'context': {
                'default_class_id': self.id,
                'default_date': attendance_date,
                'attendance_class_id': self.id,
                'attendance_date': attendance_date,
            },
            'target': 'new',
        }


    def action_add_to_calendar(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Class to Calendar'),
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': self.display_name_full,
                'default_start': self.start_date,
                'default_stop': self.end_date,
            },
        }

    def action_take_attendance(self):
        """Today's attendance sheet — one row per enrolled student, edit status in the list."""
        self.ensure_one()
        return self._action_open_attendance_list()
    
    def action_pick_attendance_date(self):
        """Choose another date, then open the same editable attendance sheet."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attendance date — %s') % self.name,
            'res_model': 'school.take.attendance.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_class_id': self.id,
                'default_date': fields.Date.context_today(self),
            },
        }