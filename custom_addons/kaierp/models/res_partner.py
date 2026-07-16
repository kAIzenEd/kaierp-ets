# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    school_record_ref = fields.Char(
        string='Student / Registration ID',
        index=True,
        copy=False,
        help='Unique ETS registration or student ID used to link billing contacts.',
    )

    _school_record_ref_unique = models.Constraint(
        'unique (school_record_ref)',
        'A billing contact already exists for this Student / Registration ID.',
    )

    @api.constrains('school_record_ref')
    def _check_school_record_ref(self):
        for partner in self:
            ref = (partner.school_record_ref or '').strip()
            if ref and partner.search_count([
                ('school_record_ref', '=', ref),
                ('id', '!=', partner.id),
            ]):
                raise ValidationError(_(
                    'Student / Registration ID "%s" is already assigned to another contact.',
                ) % ref)

    @api.model
    def _update_school_billing_partner(self, partner, name, email, phone, record_ref):
        vals = {}
        if name and partner.name != name:
            vals['name'] = name
        if email and partner.email != email:
            vals['email'] = email
        if phone and partner.phone != phone:
            vals['phone'] = phone
        if record_ref and not partner.school_record_ref:
            vals['school_record_ref'] = record_ref
        if vals:
            partner.write(vals)

    @api.model
    def find_or_create_school_billing_partner(
        self, record_ref, name, email, phone=False, current_partner=False,
    ):
        """Find or create a billing contact keyed by registration/student ID."""
        Partner = self.sudo()
        name = (name or email or '').strip()
        record_ref = (record_ref or '').strip() or False

        if current_partner and current_partner.name == name:
            if not record_ref or current_partner.school_record_ref == record_ref:
                self._update_school_billing_partner(
                    current_partner, name, email, phone, record_ref,
                )
                return current_partner

        if record_ref:
            partner = Partner.search([('school_record_ref', '=', record_ref)], limit=1)
            if partner:
                self._update_school_billing_partner(
                    partner, name, email, phone, record_ref,
                )
                return partner

        if email:
            domain = [('email', '=ilike', email), ('name', '=', name)]
            if record_ref:
                domain.append(('school_record_ref', 'in', [False, record_ref]))
            else:
                domain.append(('school_record_ref', '=', False))
            partner = Partner.search(domain, limit=1)
            if partner:
                self._update_school_billing_partner(
                    partner, name, email, phone, record_ref,
                )
                return partner

        return Partner.create({
            'name': name,
            'email': email,
            'phone': phone or False,
            'type': 'contact',
            'school_record_ref': record_ref,
        })
