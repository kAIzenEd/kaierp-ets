# -*- coding: utf-8 -*-
from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SchoolRegistrar(models.Model):
    _name = 'school.registrar'
    _description = 'Registrar'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    registrar_id = fields.Char(
        string='Registrar ID', copy=False, default=lambda self: _('New'),
    )
    photo = fields.Binary(string='Photo', attachment=True)
    gender = fields.Selection([
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other'),
    ], required=True)

    email = fields.Char(string='Email', required=True, tracking=True)
    phone = fields.Char(string='Phone')
    department = fields.Char(string='Department', default='Admissions')
    join_date = fields.Date(string='Join Date', default=fields.Date.today)

    state = fields.Selection([
        ('active', 'Active'), ('on_leave', 'On Leave'), ('inactive', 'Inactive'),
    ], default='active', tracking=True)

    user_id = fields.Many2one('res.users', string='Login User', copy=False)
    admission_count = fields.Integer(
        compute='_compute_admission_count', string='Applications',
    )
    notes = fields.Html(string='Notes')

    @api.depends()
    def _compute_admission_count(self):
        count = self.env['school.admission'].search_count([])
        for rec in self:
            rec.admission_count = count

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('registrar_id', _('New')) == _('New'):
                vals['registrar_id'] = self.env['ir.sequence'].next_by_code(
                    'school.registrar',
                ) or _('New')
        return super().create(vals_list)

    def action_create_user(self):
        """Create an internal Odoo login with Registrar access."""
        self.ensure_one()
        if self.user_id:
            raise UserError(_('This registrar already has a login user.'))
        if not self.email:
            raise ValidationError(_('Email is required to create a login.'))
        if self.state != 'active':
            raise ValidationError(_('Only active registrars can receive a login.'))

        existing = self.env['res.users'].sudo().search([
            ('login', '=', self.email),
        ], limit=1)
        if existing:
            raise ValidationError(
                _('A user with login "%s" already exists.') % self.email,
            )

        user = self.env['res.users'].sudo().create({
            'name': self.name,
            'login': self.email,
            'email': self.email,
            'notification_type': 'inbox',
            'group_ids': [
                Command.set([
                    self.env.ref('base.group_user').id,
                    self.env.ref('kaierp.group_school_registrar').id,
                ]),
            ],
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

    def action_open_admissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Admissions'),
            'res_model': 'school.admission',
            'view_mode': 'kanban,list,form',
        }
