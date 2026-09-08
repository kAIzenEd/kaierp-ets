# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SchoolCanvasSyncIssue(models.Model):
    _name = 'school.canvas.sync.issue'
    _description = 'Canvas Sync Issue'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    issue_type = fields.Selection([
        ('unmatched_student', 'Unmatched student'),
        ('unmatched_teacher', 'Unmatched teacher'),
        ('ambiguous_match', 'Ambiguous email match'),
        ('extra_teacher', 'Additional Canvas teacher'),
        ('skipped_course', 'Skipped course'),
        ('api_error', 'API error'),
    ], string='Type', required=True, index=True)
    state = fields.Selection([
        ('open', 'Open'),
        ('resolved', 'Resolved'),
        ('ignored', 'Ignored'),
    ], string='Status', default='open', required=True, index=True)

    canvas_user_id = fields.Char(string='Canvas User ID', index=True)
    canvas_course_id = fields.Char(string='Canvas Course ID', index=True)
    canvas_enrollment_id = fields.Char(string='Canvas Enrollment ID')
    canvas_user_name = fields.Char(string='Canvas User Name')
    canvas_login_id = fields.Char(string='Canvas Login ID')
    canvas_email = fields.Char(string='Canvas Email')
    canvas_course_name = fields.Char(string='Canvas Course')
    message = fields.Text(string='Details')

    student_id = fields.Many2one('school.student', string='Link Student', ondelete='set null')
    teacher_id = fields.Many2one('school.teacher', string='Link Teacher', ondelete='set null')
    class_id = fields.Many2one('school.class', string='Course', ondelete='set null')

    @api.depends('issue_type', 'canvas_user_name', 'canvas_course_name')
    def _compute_display_name(self):
        labels = dict(self._fields['issue_type'].selection)
        for rec in self:
            label = labels.get(rec.issue_type) or rec.issue_type or 'Issue'
            who = rec.canvas_user_name or rec.canvas_email or rec.canvas_login_id or ''
            course = rec.canvas_course_name or ''
            rec.display_name = ' — '.join(part for part in (label, who, course) if part)

    def action_ignore(self):
        self.write({'state': 'ignored'})

    def action_reopen(self):
        self.write({'state': 'open'})

    def action_link_student(self):
        self.ensure_one()
        if not self.student_id:
            raise UserError(_('Select a student to link, then try again.'))
        if not self.canvas_user_id:
            raise UserError(_('This issue has no Canvas user ID to store.'))
        self.student_id.canvas_user_id = self.canvas_user_id
        self.state = 'resolved'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Student linked'),
                'message': _(
                    '%s is now linked to Canvas user %s. Run Sync now to pull enrollments.',
                ) % (self.student_id.name, self.canvas_user_id),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_link_teacher(self):
        self.ensure_one()
        if not self.teacher_id:
            raise UserError(_('Select a teacher to link, then try again.'))
        if not self.canvas_user_id:
            raise UserError(_('This issue has no Canvas user ID to store.'))
        self.teacher_id.canvas_user_id = self.canvas_user_id
        self.state = 'resolved'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Teacher linked'),
                'message': _(
                    '%s is now linked to Canvas user %s. Run Sync now to assign classes.',
                ) % (self.teacher_id.name, self.canvas_user_id),
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def log_issue(self, issue_type, **values):
        vals = dict(values)
        vals['issue_type'] = issue_type
        vals['state'] = 'open'
        for key in ('canvas_user_id', 'canvas_course_id', 'canvas_enrollment_id'):
            if not vals.get(key):
                vals[key] = False
        domain = [
            ('issue_type', '=', issue_type),
            ('state', '=', 'open'),
            ('canvas_user_id', '=', vals.get('canvas_user_id')),
            ('canvas_course_id', '=', vals.get('canvas_course_id')),
            ('canvas_enrollment_id', '=', vals.get('canvas_enrollment_id')),
        ]
        existing = self.search(domain, limit=1)
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)
