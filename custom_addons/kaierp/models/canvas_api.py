# -*- coding: utf-8 -*-
import json
import logging
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CANVAS_OAUTH_SCOPES = ' '.join([
    'url:GET|/api/v1/accounts',
    'url:GET|/api/v1/accounts/:id',
    'url:GET|/api/v1/accounts/:account_id/terms',
    'url:GET|/api/v1/accounts/:account_id/enrollment_terms',
    'url:GET|/api/v1/accounts/:account_id/courses',
    'url:GET|/api/v1/courses/:id',
    'url:GET|/api/v1/courses/:course_id/enrollments',
    'url:GET|/api/v1/courses/:course_id/users',
    'url:GET|/api/v1/courses/:course_id/sections',
    'url:GET|/api/v1/users/:id',
    'url:GET|/api/v1/users/self',
])

OAUTH_STATE_TTL_SECONDS = 600
TOKEN_EXPIRY_SKEW_SECONDS = 60


class SchoolCanvasApi(models.AbstractModel):
    _name = 'school.canvas.api'
    _description = 'Canvas LMS API client'

    @api.model
    def _icp(self, key, default=''):
        return (self.env['ir.config_parameter'].sudo().get_param(key, default) or '').strip()

    @api.model
    def _set_icp(self, key, value):
        self.env['ir.config_parameter'].sudo().set_param(key, value if value is not None else '')

    @api.model
    def base_url(self):
        return self._icp('kaierp.canvas_base_url').rstrip('/')

    @api.model
    def callback_url(self):
        override = self._icp('kaierp.canvas_redirect_uri')
        if override:
            return override.rstrip('/')
        base = self._icp('web.base.url').rstrip('/')
        return f'{base}/kaierp/canvas/oauth/callback' if base else '/kaierp/canvas/oauth/callback'

    @api.model
    def is_configured(self):
        return bool(
            self.base_url()
            and self._icp('kaierp.canvas_client_id')
            and self._icp('kaierp.canvas_client_secret')
            and self._icp('kaierp.canvas_account_id')
        )

    @api.model
    def is_connected(self):
        return bool(self._icp('kaierp.canvas_access_token'))

    @api.model
    def get_authorize_url(self):
        if not self.is_configured():
            raise UserError(_(
                'Fill in Canvas URL, Account ID, Developer Key ID, and Secret, then Save, '
                'before connecting.',
            ))
        state = secrets.token_urlsafe(32)
        uid = self.env.uid
        self._set_icp(
            'kaierp.canvas_oauth_state',
            f'{state}:{uid}:{int(time.time())}',
        )
        params = {
            'client_id': self._icp('kaierp.canvas_client_id'),
            'response_type': 'code',
            'redirect_uri': self.callback_url(),
            'state': state,
            'purpose': 'Odoo kaierp',
            'scope': CANVAS_OAUTH_SCOPES,
        }
        return f'{self.base_url()}/login/oauth2/auth?{urllib.parse.urlencode(params)}'

    @api.model
    def consume_oauth_state(self, state):
        raw = self._icp('kaierp.canvas_oauth_state')
        self._set_icp('kaierp.canvas_oauth_state', '')
        if not state or not raw:
            raise UserError(_('Canvas authorization state is missing. Start Connect from Odoo settings again.'))
        parts = raw.split(':')
        if len(parts) != 3 or parts[0] != state:
            raise UserError(_('Canvas authorization state did not match. Start Connect from Odoo settings again.'))
        try:
            started = int(parts[2])
        except ValueError as err:
            raise UserError(_('Canvas authorization state is invalid.')) from err
        if time.time() - started > OAUTH_STATE_TTL_SECONDS:
            raise UserError(_('Canvas authorization expired. Start Connect from Odoo settings again.'))
        return int(parts[1])

    @api.model
    def exchange_authorization_code(self, code):
        payload = {
            'grant_type': 'authorization_code',
            'client_id': self._icp('kaierp.canvas_client_id'),
            'client_secret': self._icp('kaierp.canvas_client_secret'),
            'redirect_uri': self.callback_url(),
            'code': code,
        }
        data = self._oauth_token_request(payload)
        self._store_tokens(data)
        return data

    @api.model
    def disconnect(self):
        for key in (
            'kaierp.canvas_access_token',
            'kaierp.canvas_refresh_token',
            'kaierp.canvas_token_expiry',
            'kaierp.canvas_connected_user',
            'kaierp.canvas_last_oauth_error',
        ):
            self._set_icp(key, '')

    @api.model
    def _store_tokens(self, data):
        access = data.get('access_token') or ''
        refresh = data.get('refresh_token') or ''
        if not access:
            raise UserError(_('Canvas did not return an access token.'))
        self._set_icp('kaierp.canvas_access_token', access)
        if refresh:
            self._set_icp('kaierp.canvas_refresh_token', refresh)
        expires_in = data.get('expires_in')
        if expires_in:
            expiry = datetime.now(timezone.utc) + timedelta(
                seconds=max(int(expires_in) - TOKEN_EXPIRY_SKEW_SECONDS, 30),
            )
            self._set_icp('kaierp.canvas_token_expiry', expiry.isoformat())
        else:
            self._set_icp('kaierp.canvas_token_expiry', '')
        user = data.get('user') or {}
        label = user.get('name') or user.get('global_id') or str(user.get('id') or '')
        self._set_icp('kaierp.canvas_connected_user', label)
        self._set_icp('kaierp.canvas_last_oauth_error', '')

    @api.model
    def _refresh_access_token(self):
        refresh = self._icp('kaierp.canvas_refresh_token')
        if not refresh:
            raise UserError(_(
                'Canvas access expired and no refresh token is stored. '
                'Disconnect and Connect to Canvas again.',
            ))
        payload = {
            'grant_type': 'refresh_token',
            'client_id': self._icp('kaierp.canvas_client_id'),
            'client_secret': self._icp('kaierp.canvas_client_secret'),
            'refresh_token': refresh,
        }
        data = self._oauth_token_request(payload)
        self._store_tokens(data)

    @api.model
    def _oauth_token_request(self, payload):
        url = f'{self.base_url()}/login/oauth2/token'
        body = urllib.parse.urlencode(payload).encode('utf-8')
        request_obj = urllib.request.Request(
            url,
            data=body,
            method='POST',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'User-Agent': 'kaierp-odoo-canvas/1.0',
            },
        )
        return self._read_json(request_obj)

    @api.model
    def _token_needs_refresh(self):
        expiry_raw = self._icp('kaierp.canvas_token_expiry')
        if not expiry_raw:
            return False
        try:
            expiry = datetime.fromisoformat(expiry_raw)
        except ValueError:
            return False
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= expiry

    @api.model
    def request_json(self, method, path, query=None, retry_auth=True):
        if not self.is_connected():
            raise UserError(_('Canvas is not connected. Use Connect to Canvas in kAI-ERP Settings.'))
        if self._token_needs_refresh():
            self._refresh_access_token()
        url = f'{self.base_url()}{path}'
        if query:
            url = f'{url}?{urllib.parse.urlencode(query, doseq=True)}'
        request_obj = urllib.request.Request(
            url,
            method=method,
            headers={
                'Authorization': f'Bearer {self._icp("kaierp.canvas_access_token")}',
                'Accept': 'application/json',
                'User-Agent': 'kaierp-odoo-canvas/1.0',
            },
        )
        try:
            return self._read_json(request_obj)
        except UserError as err:
            if retry_auth and '401' in str(err):
                self._refresh_access_token()
                return self.request_json(method, path, query=query, retry_auth=False)
            raise

    @api.model
    def request_paginated(self, path, query=None):
        if query is None:
            query_items = [('per_page', '100')]
        elif isinstance(query, dict):
            query_items = list(query.items())
            if 'per_page' not in query:
                query_items.append(('per_page', '100'))
        else:
            query_items = list(query)
            if not any(key == 'per_page' for key, _unused in query_items):
                query_items.append(('per_page', '100'))
        items = []
        first = True
        next_url = None
        while True:
            if first:
                data, headers = self._request_json_headers('GET', path, query=query_items)
                first = False
            else:
                data, headers = self._request_json_headers('GET', next_url, absolute=True)
            if isinstance(data, list):
                items.extend(data)
            elif isinstance(data, dict):
                # Some Canvas term endpoints wrap the list.
                nested = data.get('enrollment_terms') or data.get('terms')
                if isinstance(nested, list):
                    items.extend(nested)
                else:
                    items.append(data)
            next_url = self._next_link(headers.get('Link') or headers.get('link'))
            if not next_url:
                break
        return items

    @api.model
    def _request_json_headers(self, method, path, query=None, absolute=False, retry_auth=True):
        if not self.is_connected():
            raise UserError(_('Canvas is not connected. Use Connect to Canvas in kAI-ERP Settings.'))
        if self._token_needs_refresh():
            self._refresh_access_token()
        url = path if absolute else f'{self.base_url()}{path}'
        if query and not absolute:
            url = f'{url}?{urllib.parse.urlencode(query, doseq=True)}'
        request_obj = urllib.request.Request(
            url,
            method=method,
            headers={
                'Authorization': f'Bearer {self._icp("kaierp.canvas_access_token")}',
                'Accept': 'application/json',
                'User-Agent': 'kaierp-odoo-canvas/1.0',
            },
        )
        try:
            return self._read_json(request_obj, with_headers=True)
        except UserError as err:
            if retry_auth and '401' in str(err):
                self._refresh_access_token()
                return self._request_json_headers(
                    method, path, query=query, absolute=absolute, retry_auth=False,
                )
            raise

    @api.model
    def _next_link(self, link_header):
        if not link_header:
            return False
        for part in link_header.split(','):
            section = part.strip()
            if 'rel="next"' not in section:
                continue
            start = section.find('<')
            end = section.find('>')
            if start >= 0 and end > start:
                return section[start + 1:end]
        return False

    @api.model
    def _read_json(self, request_obj, with_headers=False):
        try:
            with urllib.request.urlopen(request_obj, timeout=60) as response:
                raw = response.read().decode('utf-8') or '{}'
                headers = dict(response.headers.items()) if with_headers else None
        except urllib.error.HTTPError as err:
            body = ''
            try:
                body = err.read().decode('utf-8', errors='replace')
            except Exception:
                body = ''
            message = self._canvas_error_message(body) or err.reason or str(err)
            raise UserError(_('Canvas API error (%s): %s') % (err.code, message)) from err
        except urllib.error.URLError as err:
            raise UserError(_('Could not reach Canvas: %s') % err.reason) from err
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError as err:
            raise UserError(_('Canvas returned invalid JSON.')) from err
        if with_headers:
            return data, headers
        return data

    @api.model
    def _canvas_error_message(self, body):
        if not body:
            return ''
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return body[:500]
        errors = payload.get('errors')
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                return first.get('message') or str(first)
            return str(first)
        if payload.get('error_description'):
            return payload['error_description']
        if payload.get('message'):
            return payload['message']
        return body[:500]

    @api.model
    def test_connection(self):
        me = self.request_json('GET', '/api/v1/users/self')
        accounts = self.request_json('GET', '/api/v1/accounts')
        account_id = self._icp('kaierp.canvas_account_id')
        names = []
        if isinstance(accounts, list):
            names = [f"{a.get('name')} ({a.get('id')})" for a in accounts if isinstance(a, dict)]
        return {
            'user': me.get('name') or me.get('short_name') or str(me.get('id')),
            'accounts': names,
            'account_id': account_id,
        }

    @api.model
    def list_terms(self):
        account_id = self._icp('kaierp.canvas_account_id')
        path = f'/api/v1/accounts/{account_id}/terms'
        try:
            return self.request_paginated(path)
        except UserError as err:
            if '404' not in str(err):
                raise
            return self.request_paginated(
                f'/api/v1/accounts/{account_id}/enrollment_terms',
            )

    @api.model
    def list_courses(self, include_unpublished=False, include_completed=True):
        account_id = self._icp('kaierp.canvas_account_id')
        states = ['available']
        if include_unpublished:
            states.append('unpublished')
        if include_completed:
            states.append('completed')
        query = [
            ('include[]', 'term'),
            ('include[]', 'teachers'),
        ]
        for state in states:
            query.append(('state[]', state))
        return self.request_paginated(
            f'/api/v1/accounts/{account_id}/courses',
            query=query,
        )

    @api.model
    def list_course_users(self, course_id):
        query = [
            ('include[]', 'email'),
            ('include[]', 'enrollments'),
            ('enrollment_type[]', 'student'),
            ('enrollment_type[]', 'teacher'),
        ]
        return self.request_paginated(
            f'/api/v1/courses/{course_id}/users',
            query=query,
        )
