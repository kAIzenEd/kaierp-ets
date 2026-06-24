# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SchoolFee(models.Model):
    _name = 'school.fee'
    _description = 'Student Fee'
    _inherit = ['mail.thread']
    _order = 'due_date asc'

    name = fields.Char(string='Fee Description', required=True)
    student_id = fields.Many2one(
        'school.student', string='Student', required=True, ondelete='cascade'
    )
    fee_type = fields.Selection([
        ('tuition', 'Tuition Fee'),
        ('exam', 'Exam Fee'),
        ('library', 'Library Fee'),
        ('transport', 'Transport Fee'),
        ('activity', 'Activity Fee'),
        ('other', 'Other'),
    ], string='Fee Type', required=True, default='tuition')
    academic_year = fields.Char(string='Academic Year')
    amount_due = fields.Float(string='Amount Due', required=True, digits=(16, 2))
    amount_paid = fields.Float(string='Amount Paid', digits=(16, 2), default=0.0)
    amount_balance = fields.Float(
        string='Balance', compute='_compute_balance', digits=(16, 2), store=True
    )

    # --- Fee categories ---
    school_establishment = fields.Float(string='School Establishment', digits=(16, 2), default=0.0)
    school_admission = fields.Float(string='School Admission', digits=(16, 2), default=0.0)
    academic_fee = fields.Float(string='Academic Fee', digits=(16, 2), default=0.0)
    total_school_related_fees = fields.Float(
        string='TOTAL SCHOOL-RELATED FEES', compute='_compute_fee_totals', digits=(16, 2), store=True
    )

    hostel_establishment = fields.Float(string='Hostel Establishment', digits=(16, 2), default=0.0)
    hostel_admission = fields.Float(string='Hostel Admission', digits=(16, 2), default=0.0)
    monthly_hostel_fee = fields.Float(string='Monthly Hostel Fee', digits=(16, 2), default=0.0)
    total_hostel_fees = fields.Float(
        string='TOTAL HOSTEL FEES', compute='_compute_fee_totals', digits=(16, 2), store=True
    )

    textbooks_stationery = fields.Float(string='Textbooks & Stationery', digits=(16, 2), default=0.0)
    uniform_stationery = fields.Float(string='Uniform & Additional Stationery', digits=(16, 2), default=0.0)
    afterschool_student_care = fields.Float(string='AfterSchool Student Care', digits=(16, 2), default=0.0)
    fines_other_expenses = fields.Float(string='Fines & Other Expenses', digits=(16, 2), default=0.0)
    total_other_fees = fields.Float(
        string='TOTAL OTHER FEES', compute='_compute_fee_totals', digits=(16, 2), store=True
    )

    total_fees = fields.Float(
        string='TOTAL FEES', compute='_compute_fee_totals', digits=(16, 2), store=True
    )

    # --- Concessions ---
    villager = fields.Float(string='Villager', digits=(16, 2), default=0.0)
    large_family = fields.Float(string='Large Family (free after 2nd child)', digits=(16, 2), default=0.0)
    honour_roll_t1_school = fields.Float(string='Honour Roll - Term 1 (School Fees)', digits=(16, 2), default=0.0)
    honour_roll_t2_school = fields.Float(string='Honour Roll - Term 2 (School Fees)', digits=(16, 2), default=0.0)
    honour_roll_t3_school = fields.Float(string='Honour Roll - Term 3 (School Fees)', digits=(16, 2), default=0.0)
    honour_roll_t4_school = fields.Float(string='Honour Roll - Term 4 (School Fees)', digits=(16, 2), default=0.0)
    possible_other_charity = fields.Float(string='Possible Other Charity', digits=(16, 2), default=0.0)
    lha_staff_child_school = fields.Float(string='LHA Staff Child (School)', digits=(16, 2), default=0.0)
    addl_school_charity = fields.Float(string='Add\'l School Charity', digits=(16, 2), default=0.0)
    total_school_concession = fields.Float(
        string='Total School Concession', compute='_compute_concession_totals', digits=(16, 2), store=True
    )

    honour_roll_t1_hostel = fields.Float(string='Honour Roll - Term 1 (Hostel Fees)', digits=(16, 2), default=0.0)
    honour_roll_t2_hostel = fields.Float(string='Honour Roll - Term 2 (Hostel Fees)', digits=(16, 2), default=0.0)
    honour_roll_t3_hostel = fields.Float(string='Honour Roll - Term 3 (Hostel Fees)', digits=(16, 2), default=0.0)
    honour_roll_t4_hostel = fields.Float(string='Honour Roll - Term 4 (Hostel Fees)', digits=(16, 2), default=0.0)
    lha_staff_child_hostel = fields.Float(string='LHA Staff Child (Hostel)', digits=(16, 2), default=0.0)
    st_stipend_discount = fields.Float(string='ST Stipend Discount', digits=(16, 2), default=0.0)
    addl_hostel_charity = fields.Float(string='Add\'l Hostel Charity / Concession', digits=(16, 2), default=0.0)
    total_hostel_concession = fields.Float(
        string='Total Hostel Concession', compute='_compute_concession_totals', digits=(16, 2), store=True
    )

    total_other_concessions = fields.Float(string='Total OTHER Concessions', digits=(16, 2), default=0.0)
    total_concessions = fields.Float(
        string='TOTAL Concessions', compute='_compute_concession_totals', digits=(16, 2), store=True
    )
    total_concession_pct = fields.Float(
        string='TOTAL Concession %', compute='_compute_concession_totals', digits=(16, 2), store=True
    )
    due_date = fields.Date(string='Due Date', required=True)
    payment_date = fields.Date(string='Payment Date')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived'),
    ], string='Status', default='pending', tracking=True)
    notes = fields.Text(string='Notes')

    @api.depends('amount_due', 'amount_paid')
    def _compute_balance(self):
        for rec in self:
            rec.amount_balance = rec.amount_due - rec.amount_paid

    @api.depends(
        'school_establishment', 'school_admission', 'academic_fee',
        'hostel_establishment', 'hostel_admission', 'monthly_hostel_fee',
        'textbooks_stationery', 'uniform_stationery', 'afterschool_student_care', 'fines_other_expenses'
    )
    def _compute_fee_totals(self):
        for rec in self:
            rec.total_school_related_fees = rec.school_establishment + rec.school_admission + rec.academic_fee
            rec.total_hostel_fees = rec.hostel_establishment + rec.hostel_admission + rec.monthly_hostel_fee
            rec.total_other_fees = rec.textbooks_stationery + rec.uniform_stationery + rec.afterschool_student_care + rec.fines_other_expenses
            rec.total_fees = rec.total_school_related_fees + rec.total_hostel_fees + rec.total_other_fees

    @api.depends(
        'villager', 'large_family', 'honour_roll_t1_school', 'honour_roll_t2_school',
        'honour_roll_t3_school', 'honour_roll_t4_school', 'possible_other_charity',
        'lha_staff_child_school', 'addl_school_charity',
        'honour_roll_t1_hostel', 'honour_roll_t2_hostel', 'honour_roll_t3_hostel',
        'honour_roll_t4_hostel', 'lha_staff_child_hostel', 'st_stipend_discount',
        'addl_hostel_charity', 'total_other_concessions'
    )
    def _compute_concession_totals(self):
        for rec in self:
            rec.total_school_concession = sum([
                rec.villager,
                rec.large_family,
                rec.honour_roll_t1_school,
                rec.honour_roll_t2_school,
                rec.honour_roll_t3_school,
                rec.honour_roll_t4_school,
                rec.possible_other_charity,
                rec.lha_staff_child_school,
                rec.addl_school_charity,
            ])
            rec.total_hostel_concession = sum([
                rec.honour_roll_t1_hostel,
                rec.honour_roll_t2_hostel,
                rec.honour_roll_t3_hostel,
                rec.honour_roll_t4_hostel,
                rec.lha_staff_child_hostel,
                rec.st_stipend_discount,
                rec.addl_hostel_charity,
            ])
            rec.total_concessions = rec.total_school_concession + rec.total_hostel_concession + rec.total_other_concessions
            rec.total_concession_pct = (rec.total_concessions / rec.total_fees * 100.0) if rec.total_fees else 0.0

    def action_mark_paid(self):
        self.write({
            'state': 'paid',
            'amount_paid': self.amount_due,
            'payment_date': fields.Date.today(),
        })

    def action_waive(self):
        self.write({'state': 'waived'})