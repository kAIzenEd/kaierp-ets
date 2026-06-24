# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolBulkGradeWizard(models.TransientModel):
    _name = 'school.bulk.grade.wizard'
    _description = 'Bulk Grade Entry Wizard'

    class_id = fields.Many2one('school.class', string='Class', required=True)
    assessment_type = fields.Selection([
        ('quiz', 'Quiz'), ('assignment', 'Assignment'),
        ('midterm', 'Midterm Exam'), ('final', 'Final Exam'),
        ('project', 'Project'), ('final_grade', 'Final Course Grade'),
    ], string='Assessment Type', required=True)
    date = fields.Date(string='Date', default=fields.Date.today, required=True)
    max_score = fields.Float(string='Max Score', default=100.0, required=True)
    publish_immediately = fields.Boolean(string='Publish to Students')

    line_ids = fields.One2many(
        'school.bulk.grade.wizard.line', 'wizard_id', string='Student Grades'
    )

    @api.onchange('class_id')
    def _onchange_class(self):
        if self.class_id:
            lines = []
            for enrollment in self.class_id.enrollment_ids.filtered(
                lambda e: e.state == 'enrolled'
            ):
                lines.append((0, 0, {
                    'student_id': enrollment.student_id.id,
                    'score': 0.0,
                }))
            self.line_ids = lines

    def action_save_grades(self):
        self.ensure_one()
        for line in self.line_ids:
            self.env['school.grade'].create({
                'student_id': line.student_id.id,
                'class_id': self.class_id.id,
                'assessment_type': self.assessment_type,
                'date': self.date,
                'max_score': self.max_score,
                'score': line.score,
                'is_published': self.publish_immediately,
                'remarks': line.remarks,
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Grades Saved'),
                'message': _('%d grade records created.') % len(self.line_ids),
                'type': 'success',
            },
        }


class SchoolBulkGradeWizardLine(models.TransientModel):
    _name = 'school.bulk.grade.wizard.line'
    _description = 'Bulk Grade Line'

    wizard_id = fields.Many2one('school.bulk.grade.wizard', ondelete='cascade')
    student_id = fields.Many2one('school.student', string='Student', readonly=True)
    score = fields.Float(string='Score', default=0.0)
    remarks = fields.Char(string='Remarks')