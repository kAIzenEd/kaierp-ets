# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    admission_webhook_secret = fields.Char(
        string='Admission Webhook Secret',
        config_parameter='kaierp.admission_webhook_secret',
        help='Shared secret sent by Railway as the X-Webhook-Secret header.',
    )
    admission_registrar_email = fields.Char(
        string='Registrar Notification Email',
        config_parameter='kaierp.admission_registrar_email',
        help='Receives an email whenever a new admission application is submitted.',
    )
    document_upload_token_days = fields.Integer(
        string='Document Upload Link Validity (days)',
        config_parameter='kaierp.document_upload_token_days',
        default=14,
        help='How long the applicant secure upload link remains valid (1–90 days).',
    )

    # ── Razorpay (Payment Links) ────────────────────────────────
    razorpay_key_id = fields.Char(
        string='Razorpay Key ID',
        config_parameter='kaierp.razorpay_key_id',
    )
    razorpay_key_secret = fields.Char(
        string='Razorpay Key Secret',
        config_parameter='kaierp.razorpay_key_secret',
    )
    razorpay_webhook_secret = fields.Char(
        string='Razorpay Webhook Secret',
        config_parameter='kaierp.razorpay_webhook_secret',
        help='From Razorpay Dashboard → Webhooks. Used to verify payment_link.paid events.',
    )
    razorpay_webhook_url = fields.Char(
        compute='_compute_razorpay_webhook_url',
        string='Razorpay Webhook URL',
    )

    @api.depends()
    def _compute_razorpay_webhook_url(self):
        url = self.env['school.razorpay.payment'].get_webhook_url()
        for rec in self:
            rec.razorpay_webhook_url = url
