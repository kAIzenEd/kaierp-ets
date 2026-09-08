# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SchoolChangeProgramWizard(models.TransientModel):
    _name = 'school.change.program.wizard'
    _description = 'Change Student Program'

    student_id = fields.Many2one(
        'school.student', string='Student', required=True, readonly=True,
    )
    person_key = fields.Char(related='student_id.person_key', string='ETS ID', readonly=True)
    intake_year = fields.Integer(related='student_id.intake_year', string='Intake Year', readonly=True)
    current_course = fields.Selection(related='student_id.course', string='Current Program', readonly=True)
    current_student_number = fields.Char(
        related='student_id.student_id', string='Current Student ID', readonly=True,
    )
    new_course = fields.Selection(
        selection=[
            ('macs', 'Master of Arts in Christian Studies (MACS)'),
            ('pgdbs', 'Postgraduate Diploma in Biblical Studies (PGDBS)'),
            ('mabs', 'Master of Arts in Biblical Studies (MABS)'),
            ('mdiv', 'Master of Divinity (MDIV)'),
            ('macc', 'Master of Arts in Christian Counselling (MACC)'),
            ('mth', 'Master of Theology (MTH)'),
            ('dmin', 'Doctor of Ministry (D.Min)'),
            ('bth', 'Bachelor of Theology (B.Th)'),
        ],
        string='New Program',
        required=True,
    )
    preview_student_number = fields.Char(
        string='Resulting Student ID', compute='_compute_preview_student_number',
    )
    notes = fields.Char(string='Notes')

    @api.depends('student_id', 'new_course', 'intake_year')
    def _compute_preview_student_number(self):
        Admission = self.env['school.admission']
        History = self.env['school.student.number.history']
        for wiz in self:
            if not wiz.student_id or not wiz.new_course or not wiz.intake_year:
                wiz.preview_student_number = False
                continue
            if wiz.new_course == wiz.current_course:
                wiz.preview_student_number = wiz.current_student_number
                continue
            prior = History.search([
                ('student_id', '=', wiz.student_id.id),
                ('program_course', '=', wiz.new_course),
            ], order='assigned_date desc, id desc', limit=1)
            if prior:
                wiz.preview_student_number = prior.student_number
            else:
                code = Admission.COURSE_REG_CODES.get(
                    wiz.new_course, (wiz.new_course or '').upper(),
                )
                prefix = f'{Admission._year_prefix(wiz.intake_year)}{code}'
                max_seq = 0
                for number in Admission._used_registration_numbers(prefix):
                    suffix = number[len(prefix):]
                    if suffix.isdigit():
                        max_seq = max(max_seq, int(suffix))
                wiz.preview_student_number = f'{prefix}{max_seq + 1:03d}'

    def action_confirm(self):
        self.ensure_one()
        if not self.student_id._can_change_program():
            raise UserError(_(
                'Only Administrator, Registrar, or Academic Dean can change a student’s program.',
            ))
        if self.new_course == self.current_course:
            raise ValidationError(_('Choose a different program.'))
        self.student_id.action_change_program(self.new_course, notes=self.notes)
        return {'type': 'ir.actions.act_window_close'}
