# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models

from ..hooks import ensure_dashboard_layout_column

# Keep in sync with DASHBOARD_TILES KPI keys in school_dashboard.js
KAIERP_DASHBOARD_KPI_KEYS = frozenset((
    'active_students',
    'active_courses',
    'pending_admissions',
    'program_map',
    'grades',
    'transcripts',
    'attendance',
    'faculty',
    'fees',
    'calendar',
    'todo',
))

KAIERP_DASHBOARD_SKIP_MENU_XMLIDS = frozenset((
    'kaierp.menu_school_root',
    'kaierp.menu_school_dashboard',
))


class ResUsers(models.Model):
    _inherit = 'res.users'

    kaierp_dashboard_layout = fields.Text(
        string='kAI-ERP Dashboard Layout',
        help='JSON list of dashboard tile keys, saved per user.',
    )

    def _register_hook(self):
        super()._register_hook()
        ensure_dashboard_layout_column(self.env.cr)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['kaierp_dashboard_layout']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['kaierp_dashboard_layout']

    @api.model
    def kaierp_get_dashboard_layout(self):
        """Return saved tile keys, or False when the user still uses the default."""
        raw = self.env.user.sudo().kaierp_dashboard_layout
        if not raw:
            return False
        try:
            keys = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return False
        if not isinstance(keys, list):
            return False
        return self._kaierp_sanitize_dashboard_keys(keys)

    @api.model
    def kaierp_set_dashboard_layout(self, keys):
        """Persist this user's dashboard tiles. Pass False to restore the default."""
        user = self.env.user.sudo()
        if keys is False or keys is None:
            user.kaierp_dashboard_layout = False
            return False
        cleaned = self._kaierp_sanitize_dashboard_keys(keys)
        user.kaierp_dashboard_layout = json.dumps(cleaned)
        return cleaned

    @api.model
    def _kaierp_sanitize_dashboard_keys(self, keys):
        if not isinstance(keys, list):
            return []
        seen = set()
        cleaned = []
        allowed = self._kaierp_allowed_dashboard_keys()
        for key in keys:
            if not isinstance(key, str) or key not in allowed:
                continue
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(key)
        return cleaned

    @api.model
    def kaierp_get_dashboard_shortcut_catalog(self):
        """Visible kAI-ERP menu leaves, grouped like the sidebar, for the picker."""
        root = self.env.ref('kaierp.menu_school_root', raise_if_not_found=False)
        if not root:
            return []
        menus = self.env['ir.ui.menu'].load_menus(False)
        app = self._kaierp_dashboard_menu_get(menus, root.id)
        if not app:
            return []

        sections = []
        more_items = []
        for section_id in app.get('children') or []:
            section = self._kaierp_dashboard_menu_get(menus, section_id)
            if not section:
                continue
            xmlid = section.get('xmlid') or ''
            if xmlid in KAIERP_DASHBOARD_SKIP_MENU_XMLIDS:
                continue
            children = section.get('children') or []
            if not children:
                item = self._kaierp_dashboard_item_from_menu(section, 'More')
                if item:
                    more_items.append(item)
                continue
            items = []
            for leaf in self._kaierp_dashboard_iter_leaves(section_id, menus):
                item = self._kaierp_dashboard_item_from_menu(
                    leaf, section.get('name') or ''
                )
                if item:
                    items.append(item)
            if items:
                sections.append({'name': section.get('name') or '', 'items': items})
        if more_items:
            sections.append({'name': 'More', 'items': more_items})
        return sections

    @api.model
    def _kaierp_dashboard_menu_get(self, menus, menu_id):
        if menu_id in (None, False):
            return False
        return menus.get(menu_id) or menus.get(str(menu_id)) or False

    @api.model
    def _kaierp_dashboard_iter_leaves(self, menu_id, menus):
        menu = self._kaierp_dashboard_menu_get(menus, menu_id) or {}
        children = menu.get('children') or []
        if children:
            for child_id in children:
                yield from self._kaierp_dashboard_iter_leaves(child_id, menus)
            return
        yield menu

    @api.model
    def _kaierp_dashboard_item_from_menu(self, menu, section_name):
        xmlid = menu.get('xmlid') or ''
        if xmlid in KAIERP_DASHBOARD_SKIP_MENU_XMLIDS:
            return False
        action_id = menu.get('action_id')
        action_model = menu.get('action_model')
        if not action_id or not action_model:
            return False
        action_xmlid = ''
        try:
            action = self.env[action_model].browse(action_id)
            action_xmlid = action.get_external_id().get(action.id) or ''
        except Exception:
            action_xmlid = ''
        return {
            'key': xmlid or 'menu_%s' % menu.get('id'),
            'label': menu.get('name') or '',
            'section': section_name,
            'action_id': action_id,
            'action_xmlid': action_xmlid,
        }

    @api.model
    def _kaierp_allowed_dashboard_keys(self):
        allowed = set(KAIERP_DASHBOARD_KPI_KEYS)
        for section in self.kaierp_get_dashboard_shortcut_catalog():
            for item in section.get('items') or []:
                key = item.get('key')
                if key:
                    allowed.add(key)
        return allowed

    @api.model
    def _kaierp_school_group_ids(self):
        xmlids = (
            'kaierp.group_school_registrar',
            'kaierp.group_school_secretary',
            'kaierp.group_school_teacher',
            'kaierp.group_school_ta',
            'kaierp.group_school_finance',
            'kaierp.group_school_academic_dean',
            'kaierp.group_school_president',
            'kaierp.group_school_chaplain',
            'kaierp.group_school_dean_students',
            'kaierp.group_school_manager',
            'kaierp.group_school_it_admin',
        )
        group_ids = set()
        for xmlid in xmlids:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                group_ids.add(group.id)
        return group_ids

    @api.model
    def _kaierp_home_action(self):
        return self.env.ref('kaierp.action_school_dashboard', raise_if_not_found=False)

    def _kaierp_apply_default_home_action(self):
        """Send school-role users to the kAI-ERP dashboard after login."""
        action = self._kaierp_home_action()
        school_group_ids = self._kaierp_school_group_ids()
        if not action or not school_group_ids:
            return

        for user in self:
            if user.share:
                continue
            if not (school_group_ids & set(user.group_ids.ids)):
                continue
            if not user.action_id:
                user.sudo().write({'action_id': action.id})

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._kaierp_apply_default_home_action()
        return users

    def write(self, vals):
        res = super().write(vals)
        if 'group_ids' in vals:
            self._kaierp_apply_default_home_action()
        return res

    @api.model
    def kaierp_set_dashboard_home_for_all_school_users(self):
        """Callable from hooks/migrations to update existing users."""
        school_group_ids = list(self._kaierp_school_group_ids())
        if not school_group_ids:
            return
        users = self.search([
            ('share', '=', False),
            ('group_ids', 'in', school_group_ids),
        ])
        users._kaierp_apply_default_home_action()
