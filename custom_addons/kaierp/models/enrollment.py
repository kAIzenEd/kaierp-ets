# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class SchoolEnrollment(models.Model):
    _name = 'school.enrollment'
    _description = 'Class Enrollment'
    _inherit = ['mail.thread']
    _rec_name = 'display_name_full'
    _order = 'enrollment_date desc'

    display_name_full = fields.Char(
        string='Reference', compute='_compute_display_name_full', store=True
    )
    student_id = fields.Many2one(
        'school.student', string='Student', required=True,
        ondelete='cascade', tracking=True
    )
    class_id = fields.Many2one(
        'school.class', string='Class', required=True,
        ondelete='cascade', tracking=True
    )
    enrollment_date = fields.Date(
        string='Enrollment Date', default=fields.Date.today, tracking=True
    )
    state = fields.Selection([
        ('enrolled', 'Enrolled'),
        ('dropped', 'Dropped'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('waitlisted', 'Waitlisted'),
    ], string='Status', default='enrolled', tracking=True)

    grade_id = fields.Many2one(
        'school.grade', string='Final Grade',
        domain="[('student_id','=',student_id),('class_id','=',class_id)]"
    )
    notes = fields.Text(string='Notes')

    # Related fields for convenience
    teacher_id = fields.Many2one(
        related='class_id.teacher_id', string='Teacher', store=True
    )
    academic_year = fields.Char(
        related='class_id.academic_year', string='Academic Year', store=True
    )

    @api.depends('student_id.name', 'class_id.name')
    def _compute_display_name_full(self):
        for rec in self:
            s = rec.student_id.name or ''
            c = rec.class_id.name or ''
            rec.display_name_full = f'{s} → {c}' if s and c else s or c

    @api.constrains('student_id', 'class_id')
    def _check_duplicate(self):
        for rec in self:
            existing = self.search([
                ('student_id', '=', rec.student_id.id),
                ('class_id', '=', rec.class_id.id),
                ('state', 'not in', ('dropped',)),
                ('id', '!=', rec.id),
            ])
            if existing:
                raise ValidationError(_(
                    '%s is already enrolled in %s.'
                ) % (rec.student_id.name, rec.class_id.name))

    @api.constrains('class_id')
    def _check_capacity(self):
        for rec in self:
            if rec.class_id.available_seats == 0 and rec.state == 'enrolled':
                raise UserError(_(
                    'Class "%s" is full. No available seats.'
                ) % rec.class_id.name)

    def action_drop(self):
        self.write({'state': 'dropped'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_waitlist(self):
        self.write({'state': 'waitlisted'})