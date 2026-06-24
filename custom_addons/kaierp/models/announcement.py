# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SchoolAnnouncement(models.Model):
    _name = 'school.announcement'
    _description = 'School Announcement'
    _inherit = ['mail.thread']
    _order = 'date_publish desc'

    name = fields.Char(string='Title', required=True, tracking=True)
    body = fields.Html(string='Content', required=True)
    date_publish = fields.Datetime(
        string='Publish Date', default=fields.Datetime.now, required=True
    )
    date_expire = fields.Datetime(string='Expiry Date')
    audience = fields.Selection([
        ('all', 'Everyone'),
        ('students', 'Students Only'),
        ('teachers', 'Teachers Only'),
        ('parents', 'Parents Only'),
    ], string='Audience', default='all', required=True)
    priority = fields.Selection([
        ('0', 'Normal'), ('1', 'Important'), ('2', 'Urgent')
    ], default='0', string='Priority')
    is_active = fields.Boolean(string='Active', default=True)
    author_id = fields.Many2one(
        'res.users', string='Author', default=lambda self: self.env.user
    )
    attachment_ids = fields.Many2many(
        'ir.attachment', string='Attachments'
    )