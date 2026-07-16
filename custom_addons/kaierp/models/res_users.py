# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

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
