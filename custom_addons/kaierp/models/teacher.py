# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SchoolTeacher(models.Model):
    _name = 'school.teacher'
    _description = 'Teacher / Staff'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    employee_id = fields.Char(string='Employee ID', copy=False,
                               default=lambda self: _('New'))
    photo = fields.Binary(string='Photo', attachment=True)
    gender = fields.Selection([
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other')
    ], required=True)

    email = fields.Char(string='Email', required=True, tracking=True)
    phone = fields.Char(string='Phone')

    department = fields.Char(string='Department')
    specialization = fields.Char(string='Specialization')
    qualification = fields.Char(string='Qualification')
    join_date = fields.Date(string='Join Date', default=fields.Date.today)

    state = fields.Selection([
        ('active', 'Active'), ('on_leave', 'On Leave'), ('inactive', 'Inactive')
    ], default='active', tracking=True)

    class_ids = fields.One2many('school.class', 'teacher_id', string='Classes')
    class_count = fields.Integer(compute='_compute_class_count', string='# Classes')

    user_id = fields.Many2one('res.users', string='Related User')
    notes = fields.Html(string='Notes')

    @api.depends('class_ids')
    def _compute_class_count(self):
        for rec in self:
            rec.class_count = len(rec.class_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id', _('New')) == _('New'):
                vals['employee_id'] = self.env['ir.sequence'].next_by_code(
                    'school.teacher') or _('New')
        return super().create(vals_list)