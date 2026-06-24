# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SchoolGrade(models.Model):
    _name = 'school.grade'
    _description = 'Grade / Assessment'
    _inherit = ['mail.thread']
    _rec_name = 'display_name_full'
    _order = 'date desc'

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
    teacher_id = fields.Many2one(
        related='class_id.teacher_id', string='Teacher', store=True
    )
    academic_year = fields.Char(
        related='class_id.academic_year', string='Academic Year', store=True
    )

    assessment_type = fields.Selection([
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('midterm', 'Midterm Exam'),
        ('final', 'Final Exam'),
        ('project', 'Project'),
        ('participation', 'Participation'),
        ('lab', 'Lab Work'),
        ('final_grade', 'Final Course Grade'),
    ], string='Assessment Type', required=True, default='assignment', tracking=True)

    date = fields.Date(string='Date', default=fields.Date.today, required=True)
    max_score = fields.Float(string='Max Score', default=100.0, required=True)
    score = fields.Float(string='Score Obtained', required=True, tracking=True)
    percentage = fields.Float(
        string='Percentage', compute='_compute_percentage', store=True, digits=(5, 2)
    )
    letter_grade = fields.Char(
        string='Letter Grade', compute='_compute_letter_grade', store=True
    )
    gpa_points = fields.Float(
        string='GPA Points', compute='_compute_gpa_points', store=True, digits=(5, 2)
    )
    weight = fields.Float(
        string='Weight (%)', default=100.0,
        help='Weight of this grade toward the final grade.'
    )

    remarks = fields.Text(string='Teacher Remarks')
    is_published = fields.Boolean(
        string='Published to Student', default=False, tracking=True
    )

    # ── GPA Scale (US standard 4.0) ───────────────────────────
    GPA_SCALE = [
        (93, 4.0, 'A'),  (90, 3.7, 'A-'),
        (87, 3.3, 'B+'), (83, 3.0, 'B'),   (80, 2.7, 'B-'),
        (77, 2.3, 'C+'), (73, 2.0, 'C'),   (70, 1.7, 'C-'),
        (67, 1.3, 'D+'), (63, 1.0, 'D'),   (60, 0.7, 'D-'),
        (0,  0.0, 'F'),
    ]

    @api.depends('score', 'max_score')
    def _compute_percentage(self):
        for rec in self:
            rec.percentage = (rec.score / rec.max_score * 100) if rec.max_score else 0.0

    @api.depends('percentage')
    def _compute_letter_grade(self):
        for rec in self:
            p = rec.percentage
            for threshold, _, letter in self.GPA_SCALE:
                if p >= threshold:
                    rec.letter_grade = letter
                    break
            else:
                rec.letter_grade = 'F'

    @api.depends('percentage')
    def _compute_gpa_points(self):
        for rec in self:
            p = rec.percentage
            for threshold, points, _ in self.GPA_SCALE:
                if p >= threshold:
                    rec.gpa_points = points
                    break
            else:
                rec.gpa_points = 0.0

    @api.depends('student_id.name', 'class_id.name', 'assessment_type')
    def _compute_display_name_full(self):
        for rec in self:
            t = dict(rec._fields['assessment_type'].selection).get(
                rec.assessment_type, ''
            )
            rec.display_name_full = f'{rec.student_id.name} | {rec.class_id.name} | {t}'

    @api.constrains('score', 'max_score')
    def _check_score(self):
        for rec in self:
            if rec.score < 0:
                raise ValidationError(_('Score cannot be negative.'))
            if rec.score > rec.max_score:
                raise ValidationError(_(
                    'Score (%s) cannot exceed max score (%s).'
                ) % (rec.score, rec.max_score))

    def action_publish(self):
        self.write({'is_published': True})

    def action_unpublish(self):
        self.write({'is_published': False})


class SchoolTranscript(models.Model):
    """Virtual model that aggregates grades per student for transcript view."""
    _name = 'school.transcript'
    _description = 'Student Transcript'
    _auto = False   # SQL view
    _rec_name = 'student_id'

    student_id = fields.Many2one('school.student', string='Student', readonly=True)
    class_id = fields.Many2one('school.class', string='Class', readonly=True)
    academic_year = fields.Char(string='Academic Year', readonly=True)
    # subject = fields.Char(string='Subject', readonly=True)
    credit_hours = fields.Integer(string='Credits', readonly=True)
    letter_grade = fields.Char(string='Grade', readonly=True)
    gpa_points = fields.Float(string='GPA Points', readonly=True)
    weighted_points = fields.Float(string='Weighted Points', readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW school_transcript AS (
                SELECT
                    g.id,
                    g.student_id,
                    g.class_id,
                    c.academic_year,
                    c.credit_hours,
                    g.letter_grade,
                    g.gpa_points,
                    (g.gpa_points * c.credit_hours) AS weighted_points
                FROM school_grade g
                JOIN school_class c ON c.id = g.class_id
                WHERE g.assessment_type = 'final_grade'
            )
        """)