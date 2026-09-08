# -*- coding: utf-8 -*-
import logging
import secrets
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

REFERENCE_TYPE_BY_SLOT = {
    1: 'elder_pastor',
    2: 'mentor',
    3: 'seminary_professor',
    4: 'employer',
}

ANSWER_FIELDS = (
    'referee_name', 'relationship', 'address', 'phone', 'email',
    'known_how_long', 'character_integrity', 'commitment', 'strengths',
    'growth_areas', 'reservations', 'signature_name', 'signature_date',
)


class SchoolAdmissionReferenceRequest(models.Model):
    _name = 'school.admission.reference.request'
    _description = 'Admission Online Reference Request'
    _inherit = ['mail.thread']
    _order = 'admission_id, slot, id'
    _rec_name = 'display_name'

    admission_id = fields.Many2one(
        'school.admission', string='Application', required=True,
        ondelete='cascade', index=True,
    )
    slot = fields.Integer(string='Slot', required=True, index=True)
    reference_type = fields.Selection([
        ('elder_pastor', 'Elder / Pastor'),
        ('mentor', 'Mentor'),
        ('seminary_professor', 'Seminary Professor'),
        ('employer', 'Employer'),
    ], string='Reference Type', required=True)
    email = fields.Char(string='Referee Email', required=True, index=True)
    name_hint = fields.Char(
        string='Name Hint',
        help='Free-text reference details provided by the applicant.',
    )
    token = fields.Char(string='Token', required=True, index=True, copy=False)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('submitted', 'Submitted'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', required=True, tracking=True, index=True)
    sent_at = fields.Datetime(string='Sent At')
    expires_at = fields.Datetime(string='Expires At', required=True, index=True)
    submitted_at = fields.Datetime(string='Submitted At')

    # Submitted answers (online form)
    referee_name = fields.Char(string='Referee Name')
    relationship = fields.Char(string='Relationship')
    address = fields.Text(string='Address')
    phone = fields.Char(string='Phone')
    # Submitted contact email (may differ from invitation email)
    answer_email = fields.Char(string='Submitted Email')
    known_how_long = fields.Char(string='Known How Long')
    character_integrity = fields.Text(string='Character / Integrity')
    commitment = fields.Text(string='Commitment / Faith Community / Work')
    strengths = fields.Text(string='Strengths')
    growth_areas = fields.Text(string='Growth Areas')
    reservations = fields.Text(string='Reservations')
    signature_name = fields.Char(string='Signature Name')
    signature_date = fields.Date(string='Signature Date')

    form_url = fields.Char(string='Online Form URL', compute='_compute_form_url')
    display_name = fields.Char(compute='_compute_display_name', store=True)
    is_expired = fields.Boolean(compute='_compute_is_expired')

    _token_uniq = models.Constraint(
        'unique(token)',
        'Reference form token must be unique.',
    )
    _admission_slot_uniq = models.Constraint(
        'unique(admission_id, slot)',
        'Only one reference request per application slot is allowed.',
    )

    @api.depends('slot', 'reference_type', 'email', 'state')
    def _compute_display_name(self):
        type_labels = dict(self._fields['reference_type'].selection)
        for rec in self:
            rec.display_name = _('R%(slot)s — %(type)s (%(email)s) [%(state)s]',
                                  slot=rec.slot,
                                  type=type_labels.get(rec.reference_type, rec.reference_type),
                                  email=rec.email or '',
                                  state=rec.state)

    @api.depends('token')
    def _compute_form_url(self):
        base = self._public_admissions_base_url()
        for rec in self:
            rec.form_url = '%s/references/%s' % (base, rec.token) if rec.token else False

    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_expired = bool(
                rec.expires_at and rec.expires_at < now and rec.state != 'submitted'
            )

    @api.model
    def _public_admissions_base_url(self):
        ICP = self.env['ir.config_parameter'].sudo()
        base = (ICP.get_param('kaierp.public_admissions_base_url') or '').strip().rstrip('/')
        if not base:
            base = 'https://apply.ets-india.org'
        return base

    @api.model
    def _generate_token(self):
        return secrets.token_urlsafe(32)

    @api.model
    def _default_expiry(self):
        return fields.Datetime.now() + timedelta(days=30)

    def _refresh_expiry_state(self):
        """Mark timed-out open requests as expired."""
        now = fields.Datetime.now()
        stale = self.filtered(
            lambda r: r.state in ('pending', 'sent')
            and r.expires_at
            and r.expires_at < now
        )
        if stale:
            stale.write({'state': 'expired'})

    @api.model
    def _find_by_token(self, token):
        token = (token or '').strip()
        if not token:
            return self.browse()
        req = self.sudo().search([('token', '=', token)], limit=1)
        if req:
            req._refresh_expiry_state()
            req = self.sudo().browse(req.id)
        return req

    def _applicant_first_name(self):
        self.ensure_one()
        full = (self.admission_id.full_name or self.admission_id.name or '').strip()
        return full.split()[0] if full else ''

    def _api_public_payload(self):
        self.ensure_one()
        self._refresh_expiry_state()
        return {
            'ok': True,
            'status': self.state,
            'referenceType': self.reference_type,
            'slot': self.slot,
            'applicantDisplayName': self._applicant_first_name(),
            'applicationId': self.admission_id.reference or '',
            'refereeEmail': self.email or '',
            'refereeName': self.referee_name or self.name_hint or '',
            'expiresAt': self.expires_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            if self.expires_at else None,
        }

    def action_send_email(self):
        """Email the online form link to the referee (no PDF attachment)."""
        template = self.env.ref(
            'kaierp.email_template_admission_reference_online',
            raise_if_not_found=False,
        )
        for req in self:
            if not req.email:
                continue
            if req.state == 'cancelled':
                continue
            if req.state == 'submitted':
                continue
            now = fields.Datetime.now()
            vals = {
                'state': 'sent',
                'sent_at': now,
            }
            if not req.expires_at or req.expires_at < now:
                vals['expires_at'] = self._default_expiry()
            req.write(vals)
            if template:
                template.with_context(skip_reference_reply_ingest=True).send_mail(
                    req.id,
                    force_send=True,
                    email_values=self.env['school.admission']._admission_mail_email_values({
                        'email_to': req.email,
                        'reply_to': 'ets@acaindia.org',
                    }),
                )
            else:
                _logger.warning('Online reference email template missing.')
            req.admission_id.message_post(
                body=_(
                    'Online reference form link emailed to %(email)s (slot R%(slot)s).',
                    email=req.email,
                    slot=req.slot,
                ),
                message_type='notification',
            )
        return True

    def action_resend(self):
        """Staff: issue a fresh token, extend expiry 30 days, and re-email."""
        for req in self:
            if req.state == 'submitted':
                raise UserError(_(
                    'Reference R%s is already submitted and cannot be resent.',
                ) % req.slot)
            req.write({
                'token': self._generate_token(),
                'state': 'sent',
                'expires_at': self._default_expiry(),
                'sent_at': fields.Datetime.now(),
            })
            req.action_send_email()
        return True

    def action_extend_expiry(self):
        """Staff: keep token, push expiry out 30 days from now."""
        for req in self:
            if req.state == 'submitted':
                continue
            vals = {'expires_at': self._default_expiry()}
            if req.state == 'expired':
                vals['state'] = 'sent'
            req.write(vals)
        return True

    def action_cancel(self):
        self.filtered(lambda r: r.state != 'submitted').write({'state': 'cancelled'})
        return True

    def submit_answers(self, answers):
        """Store online form answers; reject duplicate / expired / cancelled."""
        self.ensure_one()
        self._refresh_expiry_state()
        if self.state == 'submitted':
            raise ValidationError(_('This reference form was already submitted.'))
        if self.state == 'cancelled':
            raise ValidationError(_('This reference form link has been cancelled.'))
        if self.state == 'expired' or (
            self.expires_at and self.expires_at < fields.Datetime.now()
        ):
            if self.state != 'expired':
                self.state = 'expired'
            raise ValidationError(_('This reference form link has expired.'))

        answers = answers or {}
        mapping = {
            'refereeName': 'referee_name',
            'relationship': 'relationship',
            'address': 'address',
            'phone': 'phone',
            'email': 'answer_email',
            'knownHowLong': 'known_how_long',
            'characterIntegrity': 'character_integrity',
            'commitment': 'commitment',
            'strengths': 'strengths',
            'growthAreas': 'growth_areas',
            'reservations': 'reservations',
            'signatureName': 'signature_name',
            'signatureDate': 'signature_date',
        }
        vals = {}
        for api_key, field_name in mapping.items():
            if api_key not in answers:
                continue
            value = answers.get(api_key)
            if field_name == 'signature_date' and value:
                vals[field_name] = value
            else:
                vals[field_name] = value if value is not None else False
        vals.update({
            'state': 'submitted',
            'submitted_at': fields.Datetime.now(),
        })
        self.write(vals)
        self.admission_id.message_post(
            body=_(
                'Online reference submitted for slot R%(slot)s by %(name)s.',
                slot=self.slot,
                name=self.referee_name or self.email,
            ),
            message_type='notification',
        )
        return True

    @api.model
    def create_for_admission(self, admission):
        """Create (or refresh) reference requests for each filled referee email."""
        created = self.browse()
        for slot, ref_type in REFERENCE_TYPE_BY_SLOT.items():
            email = (admission['personal_reference_%s_email' % slot] or '').strip()
            if not email:
                continue
            name_hint = (admission['personal_reference_%s' % slot] or '').strip()
            existing = self.search([
                ('admission_id', '=', admission.id),
                ('slot', '=', slot),
            ], limit=1)
            if existing:
                if existing.state == 'submitted':
                    continue
                existing.write({
                    'email': email,
                    'name_hint': name_hint,
                    'reference_type': ref_type,
                })
                if existing.state in ('pending', 'expired', 'cancelled'):
                    existing.write({
                        'token': self._generate_token(),
                        'expires_at': self._default_expiry(),
                        'state': 'pending',
                    })
                created |= existing
                continue
            created |= self.create({
                'admission_id': admission.id,
                'slot': slot,
                'reference_type': ref_type,
                'email': email,
                'name_hint': name_hint,
                'token': self._generate_token(),
                'expires_at': self._default_expiry(),
                'state': 'pending',
            })
        return created
