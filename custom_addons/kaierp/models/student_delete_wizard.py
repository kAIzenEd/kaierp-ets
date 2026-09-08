# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SchoolDeleteStudentWizard(models.TransientModel):
    """Confirmation dialog before permanently deleting student records."""

    _name = 'school.delete.student.wizard'
    _description = 'Confirm Student Delete'

    student_ids = fields.Many2many(
        'school.student',
        'school_delete_student_wizard_rel',
        'wizard_id',
        'student_id',
        string='Students',
        readonly=True,
    )
    student_count = fields.Integer(compute='_compute_message')
    message = fields.Text(compute='_compute_message')

    @api.depends('student_ids')
    def _compute_message(self):
        for wiz in self:
            count = len(wiz.student_ids)
            wiz.student_count = count
            if count == 1:
                wiz.message = _(
                    'Are you sure you want to delete this Student? '
                    'The record will be permanently gone.',
                )
            else:
                wiz.message = _(
                    'Are you sure you want to delete these Students? '
                    'The records will be permanently gone.',
                )

    def action_confirm_delete(self):
        self.ensure_one()
        if not self.student_ids:
            raise UserError(_('No student selected.'))
        self.student_ids.unlink()
        return {'type': 'ir.actions.act_window_close'}
