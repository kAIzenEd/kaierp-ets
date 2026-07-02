# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SchoolAssignFeeWizard(models.TransientModel):
    _name = 'school.assign.fee.wizard'
    _description = 'Assign Fees to Student'

    student_id = fields.Many2one('school.student', string='Student', required=True)
    academic_year = fields.Char(string='Academic Year')
    due_date = fields.Date(string='Due Date', required=True, default=fields.Date.today)
    line_ids = fields.One2many(
        'school.assign.fee.wizard.line', 'wizard_id', string='Fees',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        student = self.env['school.student'].browse(
            self.env.context.get('active_id'),
        ) if self.env.context.get('active_model') == 'school.student' else False
        if student:
            res['student_id'] = student.id
            res['academic_year'] = student.academic_year
        return res

    def action_load_standard_fees(self):
        """Pre-fill all ETS fee products (except application fee)."""
        self.ensure_one()
        products = self.env['product.product'].search([
            ('product_tmpl_id.is_ets_fee', '=', True),
            ('product_tmpl_id.is_application_fee', '=', False),
        ], order='product_tmpl_id.default_code')
        lines = [(5, 0, 0)]
        for product in products:
            tmpl = product.product_tmpl_id
            lines.append((0, 0, {
                'product_id': product.id,
                'quantity': tmpl.default_quantity or 1.0,
                'unit_price': product.list_price,
                'selected': tmpl.ets_fee_code in (
                    'admission_fee', 'tuition', 'library_user_fee',
                    'technology_fee', 'sports_fee',
                ),
            }))
        self.line_ids = lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_assign_fees(self):
        self.ensure_one()
        selected = self.line_ids.filtered('selected')
        if not selected:
            raise UserError(_('Select at least one fee to assign.'))
        Fee = self.env['school.fee']
        for line in selected:
            Fee.create_from_product(
                self.student_id,
                line.product_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                due_date=self.due_date,
                academic_year=self.academic_year,
            )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Student Fees'),
            'res_model': 'school.fee',
            'view_mode': 'list,form',
            'domain': [('student_id', '=', self.student_id.id)],
        }


class SchoolAssignFeeWizardLine(models.TransientModel):
    _name = 'school.assign.fee.wizard.line'
    _description = 'Assign Fee Wizard Line'

    wizard_id = fields.Many2one('school.assign.fee.wizard', required=True, ondelete='cascade')
    selected = fields.Boolean(string='Assign', default=True)
    product_id = fields.Many2one(
        'product.product', string='Fee', required=True,
        domain=[('product_tmpl_id.is_ets_fee', '=', True)],
    )
    billing_unit = fields.Selection(
        related='product_id.product_tmpl_id.billing_unit', readonly=True,
    )
    is_refundable = fields.Boolean(
        related='product_id.product_tmpl_id.is_refundable', readonly=True,
    )
    quantity = fields.Float(string='Quantity', default=1.0)
    unit_price = fields.Float(string='Unit Price', digits=(16, 2))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        tmpl = self.product_id.product_tmpl_id
        self.unit_price = self.product_id.list_price
        self.quantity = tmpl.default_quantity or 1.0
