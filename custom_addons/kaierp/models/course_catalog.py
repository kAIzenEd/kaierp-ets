# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SchoolCourseCatalog(models.Model):
    _name = 'school.course.catalog'
    _description = 'Course Catalog'
    _order = 'code asc'
    _rec_name = 'display_name'

    code = fields.Char(
        string='Course Code', required=True, index=True, copy=False,
        help='Durable catalog code (e.g. NT101), independent of semester offerings.',
    )
    name = fields.Char(string='Course Title', required=True)
    display_name = fields.Char(
        string='Display Name', compute='_compute_display_name', store=True,
    )
    credit_hours = fields.Integer(string='Credit Hours', default=3)
    area = fields.Selection([
        ('biblical', 'Biblical Studies'),
        ('theology', 'Theology'),
        ('history', 'Church History'),
        ('practical', 'Practical Theology'),
        ('languages', 'Biblical Languages'),
        ('counselling', 'Counselling'),
        ('elective', 'Elective / Other'),
    ], string='Area', default='biblical', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    requirement_ids = fields.One2many(
        'school.program.requirement', 'catalog_id', string='Program Requirements',
    )
    program_count = fields.Integer(
        string='# Programs', compute='_compute_program_count',
    )
    class_ids = fields.One2many(
        'school.class', 'catalog_id', string='Course Offerings',
    )

    _code_uniq = models.Constraint(
        'unique(code)',
        'Course catalog code must be unique.',
    )

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            if rec.code and rec.name:
                rec.display_name = f'[{rec.code}] {rec.name}'
            else:
                rec.display_name = rec.code or rec.name or ''

    @api.depends('requirement_ids')
    def _compute_program_count(self):
        for rec in self:
            rec.program_count = len(rec.requirement_ids)

    @api.constrains('credit_hours')
    def _check_credits(self):
        for rec in self:
            if rec.credit_hours < 0:
                raise ValidationError(_('Credit hours cannot be negative.'))

    @api.model
    def get_explorer_catalog_list(self):
        """Lightweight list for the Course mode picker."""
        courses = self.search([('active', '=', True)], order='code asc')
        return [{
            'id': c.id,
            'code': c.code,
            'name': c.name,
            'credit_hours': c.credit_hours,
            'area': c.area,
            'area_label': dict(c._fields['area'].selection).get(c.area, ''),
            'program_count': len(c.requirement_ids),
        } for c in courses]
