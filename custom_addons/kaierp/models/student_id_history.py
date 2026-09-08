# -*- coding: utf-8 -*-
from odoo import fields, models


class SchoolStudentNumberHistory(models.Model):
    """Past and current Student IDs held by a person (program changes)."""

    _name = 'school.student.number.history'
    _description = 'Student ID History'
    _order = 'assigned_date desc, id desc'

    student_id = fields.Many2one(
        'school.student', string='Student', required=True, ondelete='cascade', index=True,
    )
    program_course = fields.Selection(
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
        string='Program',
        required=True,
        index=True,
    )
    student_number = fields.Char(
        string='Student ID', required=True, index=True,
        help='Official ID for this program (e.g. 27MTH001).',
    )
    intake_year = fields.Integer(string='Intake Year', required=True)
    assigned_date = fields.Date(string='Assigned On', required=True, default=fields.Date.today)
    ended_date = fields.Date(
        string='Ended On',
        help='Set when the student leaves this program ID (program change).',
    )
    is_current = fields.Boolean(string='Current', default=True, index=True)
    notes = fields.Char(string='Notes')
