# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolEnrollStudentWizard(models.TransientModel):
    _name = 'school.enroll.student.wizard'
    _description = 'Enroll Students Wizard'

    class_id = fields.Many2one(
        'school.class', string='Class', required=True, readonly=True
    )
    student_ids = fields.Many2many(
        'school.student', string='Students to Enroll',
        domain="[('state','=','active')]"
    )
    enrollment_date = fields.Date(
        string='Enrollment Date', default=fields.Date.today, required=True
    )

    available_seats = fields.Integer(
        related='class_id.available_seats', string='Available Seats', readonly=True
    )

    def action_enroll(self):
        self.ensure_one()
        if not self.student_ids:
            raise UserError(_('Please select at least one student to enroll.'))
        if len(self.student_ids) > self.class_id.available_seats:
            raise UserError(_(
                'Not enough seats. Available: %d, Trying to enroll: %d'
            ) % (self.class_id.available_seats, len(self.student_ids)))

        created = []
        skipped = []
        for student in self.student_ids:
            existing = self.env['school.enrollment'].search([
                ('student_id', '=', student.id),
                ('class_id', '=', self.class_id.id),
                ('state', 'not in', ('dropped',)),
            ])
            if existing:
                skipped.append(student.name)
                continue
            self.env['school.enrollment'].create({
                'student_id': student.id,
                'class_id': self.class_id.id,
                'enrollment_date': self.enrollment_date,
                'state': 'enrolled',
            })
            created.append(student.name)

        msg = _('%d student(s) enrolled successfully.') % len(created)
        if skipped:
            msg += _('\n%d already enrolled (skipped): %s') % (
                len(skipped), ', '.join(skipped)
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Enrollment Complete'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            },
        }