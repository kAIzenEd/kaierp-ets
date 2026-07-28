# -*- coding: utf-8 -*-
"""Reassign WhatsApp XML IDs from kaierp and migrate event rules after the module split."""

_REASSIGN_NAMES = (
    'model_school_whatsapp_message',
    'model_school_whatsapp_reply_wizard',
    'view_school_whatsapp_message_list',
    'view_school_whatsapp_message_form',
    'view_school_whatsapp_message_search',
    'action_school_whatsapp_message',
    'action_school_whatsapp_message_inbound',
    'menu_school_whatsapp_messages',
    'menu_school_whatsapp_inbox',
    'view_school_whatsapp_reply_wizard_form',
    'access_school_whatsapp_reply_wizard_manager',
    'access_school_whatsapp_reply_wizard_registrar',
    'access_school_whatsapp_reply_wizard_secretary',
    'access_school_whatsapp_message_manager',
    'access_school_whatsapp_message_registrar',
    'access_school_whatsapp_message_secretary',
    'kaierp_whatsapp_webhook_verify_token',
    'kaierp_whatsapp_api_version',
    'kaierp_whatsapp_default_country_code',
    'kaierp_whatsapp_template_language',
    'kaierp_whatsapp_template_test',
)

_PARAM_DEFAULTS = {
    'kaierp.whatsapp_webhook_verify_token': 'change-me-whatsapp-webhook',
    'kaierp.whatsapp_api_version': 'v21.0',
    'kaierp.whatsapp_default_country_code': '91',
    'kaierp.whatsapp_template_language': 'en',
    'kaierp.whatsapp_template_test': 'hello_world',
}

# Legacy Phase-1 settings keys → event-rule seed (ETS defaults).
_LEGACY_TEMPLATE_RULES = (
    {
        'xmlid_name': 'whatsapp_event_rule_received',
        'name': 'Application received',
        'trigger': 'on_create',
        'state': False,
        'param_key': 'kaierp.whatsapp_template_received',
        'body_param_keys': 'name,reference,course',
        'sequence': 10,
        'notes': 'Body: {{1}} name, {{2}} reference, {{3}} course',
    },
    {
        'xmlid_name': 'whatsapp_event_rule_pending_applicant',
        'name': 'Pending applicant response',
        'trigger': 'on_state',
        'state': 'pending_applicant',
        'param_key': 'kaierp.whatsapp_template_pending_applicant',
        'body_param_keys': 'name,reference',
        'sequence': 20,
        'notes': 'Body: {{1}} name, {{2}} reference',
    },
    {
        'xmlid_name': 'whatsapp_event_rule_exam_interview',
        'name': 'Exam & interview',
        'trigger': 'on_state',
        'state': 'pending_exam_interview',
        'param_key': 'kaierp.whatsapp_template_exam_interview',
        'body_param_keys': 'name,reference',
        'sequence': 30,
        'notes': 'Body: {{1}} name, {{2}} reference',
    },
    {
        'xmlid_name': 'whatsapp_event_rule_accepted',
        'name': 'Admission accepted',
        'trigger': 'on_state',
        'state': 'accepted',
        'param_key': 'kaierp.whatsapp_template_accepted',
        'body_param_keys': 'name,course',
        'sequence': 40,
        'notes': 'Body: {{1}} name, {{2}} course',
    },
    {
        'xmlid_name': 'whatsapp_event_rule_denied',
        'name': 'Admission denied',
        'trigger': 'on_state',
        'state': 'admission_denied',
        'param_key': 'kaierp.whatsapp_template_denied',
        'body_param_keys': 'name,reference',
        'sequence': 50,
        'notes': 'Body: {{1}} name, {{2}} reference',
    },
)


def _ensure_event_rules(env):
    """Create event rules from legacy ICP template names if none exist yet."""
    Rule = env['school.whatsapp.event.rule'].sudo()
    if Rule.search_count([]):
        return

    icp = env['ir.config_parameter'].sudo()
    Imd = env['ir.model.data'].sudo()
    for spec in _LEGACY_TEMPLATE_RULES:
        template_name = (icp.get_param(spec['param_key'], '') or '').strip()
        if not template_name:
            # Still create inactive placeholder so managers can fill Meta names.
            template_name = ''
        vals = {
            'name': spec['name'],
            'trigger': spec['trigger'],
            'state': spec['state'] or False,
            'template_name': template_name or 'CHANGE_ME',
            'body_param_keys': spec['body_param_keys'],
            'sequence': spec['sequence'],
            'notes': spec['notes'],
            'active': bool(template_name),
        }
        rule = Rule.create(vals)
        Imd.create({
            'name': spec['xmlid_name'],
            'module': 'kaierp_whatsapp',
            'model': 'school.whatsapp.event.rule',
            'res_id': rule.id,
            'noupdate': True,
        })


def post_init_hook(env):
    """Move legacy kaierp XML IDs, ensure default config, seed event rules."""
    if not env['ir.module.module'].search([
        ('name', '=', 'kaierp'),
        ('state', '=', 'installed'),
    ], limit=1):
        return

    env.cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'kaierp_whatsapp'
         WHERE module = 'kaierp'
           AND name = ANY(%s)
        """,
        (list(_REASSIGN_NAMES),),
    )

    icp = env['ir.config_parameter'].sudo()
    for key, default in _PARAM_DEFAULTS.items():
        if not icp.get_param(key):
            icp.set_param(key, default)

    _ensure_event_rules(env)
