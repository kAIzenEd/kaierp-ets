# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SchoolAttendance(models.Model):
    _name = 'school.attendance'
    _description = 'Attendance Record'
    _order = 'date desc, student_id'
    _rec_name = 'display_name'

    student_id = fields.Many2one(
        'school.student', string='Student', required=True, ondelete='cascade', index=True,
    )
    class_id = fields.Many2one(
        'school.class', string='Class', required=True, ondelete='cascade', index=True,
    )
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, index=True)
    state = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ], string='Status', default='present', required=True)
    note = fields.Char(string='Note')
    teacher_id = fields.Many2one(
        related='class_id.teacher_id', string='Teacher', store=True, readonly=True,
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)
    _sql_constraints = [
        (
            'class_student_date_uniq',
            'unique(class_id, student_id, date)',
            'Attendance for this student in this class on this date already exists.',
        ),
    ]

    @api.depends('student_id', 'class_id', 'date', 'state')
    def _compute_display_name(self):
        state_labels = dict(self._fields['state'].selection)
        for rec in self:
            student = rec.student_id.name or _('Student')
            class_name = rec.class_id.name or _('Class')
            day = rec.date or ''
            status = state_labels.get(rec.state, rec.state or '')
            rec.display_name = f'{student} — {class_name} ({day}) [{status}]'
    
    @api.model
    def _session_domain_from_context(self):
        """Domain for the class/date attendance session opened from a class."""
        class_id = (
            self.env.context.get('attendance_class_id')
            or self.env.context.get('default_class_id')
        )
        att_date = (
            self.env.context.get('attendance_date')
            or self.env.context.get('default_date')
        )
        if not class_id or not att_date:
            raise UserError(_('Open attendance from a class to use bulk actions.'))
        return [('class_id', '=', class_id), ('date', '=', att_date)]

    def action_session_mark_all_present(self):
        records = self.search(self._session_domain_from_context())
        records.write({'state': 'present'})
        return True
    
    def action_session_mark_all_absent(self):
        records = self.search(self._session_domain_from_context())
        records.write({'state': 'absent'})
        return True

    def action_session_mark_all_late(self):
        records = self.search(self._session_domain_from_context())
        records.write({'state': 'late'})
        return True

    def action_session_mark_all_excused(self):
        records = self.search(self._session_domain_from_context())
        records.write({'state': 'excused'})
        return True
