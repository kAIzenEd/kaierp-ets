# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SchoolFee(models.Model):
    _name = 'school.fee'
    _description = 'Student Fee'
    _inherit = ['mail.thread']
    _order = 'due_date asc, id asc'

    name = fields.Char(string='Description', required=True)
    student_id = fields.Many2one(
        'school.student', string='Student', required=True, ondelete='cascade',
    )
    admission_id = fields.Many2one(
        'school.admission', string='Application', ondelete='set null',
    )
    partner_id = fields.Many2one(
        'res.partner', string='Invoice Contact',
        related='student_id.partner_id', store=True, readonly=False,
    )
    product_id = fields.Many2one(
        'product.product', string='Fee Product', required=True,
        domain=[('product_tmpl_id.is_ets_fee', '=', True)],
    )
    billing_unit = fields.Selection(
        related='product_id.product_tmpl_id.billing_unit', readonly=True,
    )
    is_refundable = fields.Boolean(
        related='product_id.product_tmpl_id.is_refundable', readonly=True,
    )
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    unit_price = fields.Float(string='Unit Price', digits=(16, 2), required=True)
    academic_year = fields.Char(string='Academic Year')
    amount_due = fields.Float(
        string='Amount Due', compute='_compute_amounts', store=True, digits=(16, 2),
    )
    amount_paid = fields.Float(string='Amount Paid', digits=(16, 2), default=0.0)
    amount_balance = fields.Float(
        string='Balance', compute='_compute_amounts', store=True, digits=(16, 2),
    )
    due_date = fields.Date(string='Due Date', required=True)
    payment_date = fields.Date(string='Payment Date')
    invoice_id = fields.Many2one(
        'account.move', string='Invoice', copy=False, readonly=True,
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived'),
        ('invoiced', 'Invoiced'),
    ], string='Status', default='pending', tracking=True)
    notes = fields.Text(string='Notes')

    @api.depends('quantity', 'unit_price', 'amount_paid')
    def _compute_amounts(self):
        for rec in self:
            rec.amount_due = rec.quantity * rec.unit_price
            rec.amount_balance = rec.amount_due - rec.amount_paid

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        tmpl = self.product_id.product_tmpl_id
        self.name = self.product_id.display_name
        self.unit_price = self.product_id.list_price
        self.quantity = tmpl.default_quantity or 1.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_id') and not vals.get('name'):
                product = self.env['product.product'].browse(vals['product_id'])
                vals['name'] = product.display_name
            if vals.get('product_id') and not vals.get('unit_price'):
                product = self.env['product.product'].browse(vals['product_id'])
                vals['unit_price'] = product.list_price
        return super().create(vals_list)

    def _get_invoice_partner(self):
        self.ensure_one()
        partner = self.student_id.partner_id
        if not partner:
            raise UserError(_(
                'Student %s has no billing contact. Link or create a contact first.',
            ) % self.student_id.name)
        return partner

    def _prepare_invoice_line_vals(self):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'name': self.name,
            'quantity': self.quantity,
            'price_unit': self.unit_price,
        }

    def action_create_invoice(self):
        """Create one customer invoice for the selected fee lines."""
        fees = self.filtered(lambda f: not f.invoice_id)
        if not fees:
            raise UserError(_('All selected fees are already linked to an invoice.'))

        students = fees.mapped('student_id')
        if len(students) > 1:
            raise UserError(_('Select fees for a single student to create one invoice.'))

        student = students[0]
        partner = fees[0]._get_invoice_partner()
        line_vals = [fee._prepare_invoice_line_vals() for fee in fees]
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, line) for line in line_vals],
            'ref': student.student_id or student.name,
        })
        fees.write({
            'invoice_id': invoice.id,
            'state': 'invoiced',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('No invoice linked to this fee.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
        }

    def action_mark_paid(self):
        self.write({
            'state': 'paid',
            'amount_paid': self.amount_due,
            'payment_date': fields.Date.today(),
        })

    def action_waive(self):
        self.write({'state': 'waived'})

    @api.model
    def create_from_product(self, student, product, quantity=None, unit_price=None,
                              admission=None, due_date=None, academic_year=None):
        """Helper used by wizards and admission payment hooks."""
        tmpl = product.product_tmpl_id
        return self.create({
            'student_id': student.id,
            'admission_id': admission.id if admission else False,
            'product_id': product.id,
            'name': product.display_name,
            'quantity': quantity if quantity is not None else tmpl.default_quantity or 1.0,
            'unit_price': unit_price if unit_price is not None else product.list_price,
            'due_date': due_date or fields.Date.today(),
            'academic_year': academic_year or student.academic_year,
        })
