# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


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

    # ── Canvas LMS ──────────────────────────────────────────────
    canvas_base_url = fields.Char(
        string='Canvas URL',
        config_parameter='kaierp.canvas_base_url',
        help='Canvas site URL with no trailing slash, e.g. https://ets.instructure.com',
    )
    canvas_account_id = fields.Char(
        string='Canvas Account ID',
        config_parameter='kaierp.canvas_account_id',
        help='Number after /accounts/ in the Admin URL. Often 1 on a dedicated ETS instance.',
    )
    canvas_client_id = fields.Char(
        string='Developer Key ID',
        config_parameter='kaierp.canvas_client_id',
    )
    canvas_client_secret = fields.Char(
        string='Developer Key Secret',
        config_parameter='kaierp.canvas_client_secret',
    )
    canvas_redirect_uri_override = fields.Char(
        string='Redirect URI override',
        config_parameter='kaierp.canvas_redirect_uri',
        help='Leave blank to use this database’s public URL. '
             'Must match the Redirect URI on the Canvas Developer Key.',
    )
    canvas_sync_enabled = fields.Boolean(
        string='Nightly Canvas sync',
        config_parameter='kaierp.canvas_sync_enabled',
    )
    canvas_sync_unpublished = fields.Boolean(
        string='Include unpublished courses',
        config_parameter='kaierp.canvas_sync_unpublished',
    )
    canvas_sync_completed_courses = fields.Boolean(
        string='Include completed courses',
        config_parameter='kaierp.canvas_sync_completed_courses',
        default=True,
    )
    canvas_oauth_callback_url = fields.Char(
        compute='_compute_canvas_status',
        string='OAuth Redirect URI',
    )
    canvas_connected = fields.Boolean(compute='_compute_canvas_status')
    canvas_connected_user = fields.Char(compute='_compute_canvas_status')
    canvas_last_sync_at = fields.Char(compute='_compute_canvas_status')
    canvas_last_sync_summary = fields.Char(compute='_compute_canvas_status')
    canvas_last_oauth_error = fields.Char(compute='_compute_canvas_status')

    @api.depends()
    def _compute_canvas_status(self):
        api = self.env['school.canvas.api']
        icp = self.env['ir.config_parameter'].sudo()
        callback = api.callback_url()
        connected = api.is_connected()
        connected_user = icp.get_param('kaierp.canvas_connected_user', '') or ''
        last_sync = icp.get_param('kaierp.canvas_last_sync_at', '') or ''
        summary = icp.get_param('kaierp.canvas_last_sync_summary', '') or ''
        oauth_error = icp.get_param('kaierp.canvas_last_oauth_error', '') or ''
        for rec in self:
            rec.canvas_oauth_callback_url = callback
            rec.canvas_connected = connected
            rec.canvas_connected_user = connected_user
            rec.canvas_last_sync_at = last_sync
            rec.canvas_last_sync_summary = summary
            rec.canvas_last_oauth_error = oauth_error

    def _flush_canvas_settings(self):
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        if self.canvas_base_url:
            icp.set_param('kaierp.canvas_base_url', self.canvas_base_url.strip().rstrip('/'))
        if self.canvas_account_id:
            icp.set_param('kaierp.canvas_account_id', self.canvas_account_id.strip())
        if self.canvas_client_id:
            icp.set_param('kaierp.canvas_client_id', self.canvas_client_id.strip())
        if self.canvas_client_secret:
            icp.set_param('kaierp.canvas_client_secret', self.canvas_client_secret.strip())
        if self.canvas_redirect_uri_override:
            icp.set_param(
                'kaierp.canvas_redirect_uri',
                self.canvas_redirect_uri_override.strip().rstrip('/'),
            )

    def action_canvas_oauth_start(self):
        self._flush_canvas_settings()
        url = self.env['school.canvas.api'].get_authorize_url()
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    def action_canvas_disconnect(self):
        self.env['school.canvas.api'].disconnect()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Canvas disconnected'),
                'message': _('Access tokens were cleared. Connection settings were kept.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_canvas_test_connection(self):
        self._flush_canvas_settings()
        info = self.env['school.canvas.api'].test_connection()
        accounts = ', '.join(info.get('accounts') or []) or _('none listed')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Canvas connection OK'),
                'message': _(
                    'Signed in as %(user)s. Account ID in settings: %(account)s. '
                    'Accounts visible: %(accounts)s.',
                    user=info.get('user') or '',
                    account=info.get('account_id') or '',
                    accounts=accounts,
                ),
                'type': 'success',
                'sticky': True,
            },
        }

    def action_canvas_sync_now(self):
        self._flush_canvas_settings()
        run = self.env['school.canvas.sync.run'].run_sync()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Canvas sync finished') if run.state == 'done' else _('Canvas sync failed'),
                'message': run.summary or '',
                'type': 'success' if run.state == 'done' else 'danger',
                'sticky': True,
            },
        }
