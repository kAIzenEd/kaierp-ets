# -*- coding: utf-8 -*-
from odoo import Command, models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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

    def action_create_user(self):
        """Create an internal login with Faculty access (Registrar-managed)."""
        self.ensure_one()
        if not self.env.user.has_group('kaierp.group_school_registrar') and not self.env.user.has_group(
            'kaierp.group_school_manager'
        ):
            raise UserError(_('Only Registrars can create faculty logins.'))
        if self.user_id:
            raise UserError(_('This teacher already has a login user.'))
        if not self.email:
            raise ValidationError(_('Email is required to create a login.'))
        if self.state != 'active':
            raise ValidationError(_('Only active teachers can receive a login.'))

        existing = self.env['res.users'].sudo().search([('login', '=', self.email)], limit=1)
        if existing:
            raise ValidationError(_('A user with login "%s" already exists.') % self.email)

        user = self.env['res.users'].sudo().create({
            'name': self.name,
            'login': self.email,
            'email': self.email,
            'notification_type': 'inbox',
            'group_ids': [Command.set([
                self.env.ref('base.group_user').id,
                self.env.ref('kaierp.group_school_teacher').id,
            ])],
        })
        self.user_id = user.id
        user.action_reset_password()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Login created'),
                'message': _(
                    'An invitation email was sent to %s so they can set their password.',
                ) % self.email,
                'type': 'success',
                'sticky': False,
            },
        }
