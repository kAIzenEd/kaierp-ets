# -*- coding: utf-8 -*-
import re
from datetime import date, datetime

from odoo import api, fields, models, _


class SchoolCanvasTerm(models.Model):
    _name = 'school.canvas.term'
    _description = 'Canvas Enrollment Term'
    _order = 'start_date desc, name'

    name = fields.Char(string='Canvas Term Name', required=True)
    canvas_term_id = fields.Char(string='Canvas Term ID', required=True, index=True, copy=False)
    sis_term_id = fields.Char(string='SIS Term ID')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    workflow_state = fields.Char(string='Canvas Status')
    academic_year = fields.Char(
        string='Odoo Academic Year',
        help='Mapped onto school.class, e.g. 2026-2027.',
    )
    semester = fields.Selection([
        ('summer', 'Summer Semester'),
        ('fall', 'Fall Semester'),
        ('spring', 'Spring Semester'),
    ], string='Odoo Semester')
    last_sync_at = fields.Datetime(string='Last Synced')
    class_count = fields.Integer(string='# Courses', compute='_compute_class_count')

    _canvas_term_id_uniq = models.Constraint(
        'unique(canvas_term_id)',
        'Canvas term ID must be unique.',
    )

    @api.depends('canvas_term_id')
    def _compute_class_count(self):
        Class = self.env['school.class']
        for rec in self:
            rec.class_count = Class.search_count([
                ('canvas_term_id', '=', rec.canvas_term_id),
            ]) if rec.canvas_term_id else 0

    @api.model
    def guess_mapping(self, name, start_date=None):
        name_l = (name or '').lower()
        year = None
        match = re.search(r'(20\d{2})', name or '')
        if match:
            year = int(match.group(1))
        elif start_date:
            year = start_date.year

        if 'spring' in name_l:
            semester = 'spring'
            academic_year = f'{year - 1}-{year}' if year else ''
        elif 'summer' in name_l:
            semester = 'summer'
            academic_year = f'{year}-{year + 1}' if year else ''
        else:
            semester = 'fall'
            academic_year = f'{year}-{year + 1}' if year else ''
        return academic_year, semester

    @api.model
    def parse_canvas_date(self, value):
        if not value:
            return False
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        raw = str(value).replace('Z', '+00:00')
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            try:
                parsed = datetime.strptime(raw[:10], '%Y-%m-%d')
            except ValueError:
                return False
        return parsed.date()
