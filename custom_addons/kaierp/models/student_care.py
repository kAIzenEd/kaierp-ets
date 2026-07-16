# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class SchoolStudentCareNote(models.Model):
    _name = 'school.student.care.note'
    _description = 'Student Care Note'
    _order = 'note_date desc, id desc'

    student_id = fields.Many2one(
        'school.student', string='Student', required=True, ondelete='cascade', index=True,
    )
    section = fields.Selection([
        ('chaplain', 'Chaplain'),
        ('field_education', 'Field Education'),
    ], string='Section', required=True, index=True)
    note_date = fields.Datetime(
        string='Date', required=True, default=fields.Datetime.now, index=True,
    )
    author_id = fields.Many2one(
        'res.users', string='Author', required=True,
        default=lambda self: self.env.user, readonly=True,
    )
    note = fields.Text(string='Note', required=True)

    def write(self, vals):
        raise UserError(_(
            'Care notes are append-only and cannot be edited. '
            'Add a new note, or ask an Administrator to delete an entry if needed.',
        ))

    def unlink(self):
        if not self.env.user.has_group('kaierp.group_school_manager'):
            raise UserError(_('Only Administrators can delete care notes.'))
        return super().unlink()


class SchoolStudentCareDocument(models.Model):
    _name = 'school.student.care.document'
    _description = 'Student Care Document'
    _order = 'upload_date desc, id desc'

    student_id = fields.Many2one(
        'school.student', string='Student', required=True, ondelete='cascade', index=True,
    )
    section = fields.Selection([
        ('chaplain', 'Chaplain'),
        ('field_education', 'Field Education'),
    ], string='Section', required=True, index=True)
    name = fields.Char(string='Title', required=True)
    description = fields.Char(string='Description')
    document_file = fields.Binary(string='File', required=True, attachment=True)
    document_filename = fields.Char(string='Filename')
    upload_date = fields.Datetime(
        string='Uploaded On', required=True, default=fields.Datetime.now, index=True,
    )
    uploaded_by_id = fields.Many2one(
        'res.users', string='Uploaded By', required=True,
        default=lambda self: self.env.user, readonly=True,
    )

    def write(self, vals):
        raise UserError(_(
            'Care documents are append-only and cannot be edited. '
            'Upload a new file, or ask an Administrator to delete an entry if needed.',
        ))

    def unlink(self):
        if not self.env.user.has_group('kaierp.group_school_manager'):
            raise UserError(_('Only Administrators can delete care documents.'))
        return super().unlink()
