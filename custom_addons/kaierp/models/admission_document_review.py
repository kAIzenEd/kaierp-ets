# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SchoolAdmissionDocumentReview(models.Model):
    _name = 'school.admission.document.review'
    _description = 'Admission Document Review'
    _order = 'sequence, id'

    admission_id = fields.Many2one(
        'school.admission', string='Application', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    document_code = fields.Char(string='Document Code', required=True)
    document_label = fields.Char(string='Document', required=True)
    is_verified = fields.Boolean(
        string='Verified', default=False,
        help='Check when this document has been reviewed and is acceptable (or not required).',
    )
    has_issue = fields.Boolean(
        string='Issue', default=False,
        help='Check when something is missing or needs correction from the applicant.',
    )
    review_notes = fields.Char(string='Notes')
    has_file = fields.Boolean(string='Uploaded', compute='_compute_has_file')

    @api.onchange('is_verified')
    def _onchange_is_verified(self):
        if self.is_verified:
            self.has_issue = False

    @api.onchange('has_issue')
    def _onchange_has_issue(self):
        if self.has_issue:
            self.is_verified = False

    @api.depends('admission_id', 'document_code')
    def _compute_has_file(self):
        for line in self:
            admission = line.admission_id
            line.has_file = bool(
                admission
                and line.document_code
                and line.document_code in admission._fields
                and admission[line.document_code]
            )
