# -*- coding: utf-8 -*-
{
    'name': 'kAI ERP — WhatsApp',
    'version': '19.0.1.2.0',
    'category': 'Education',
    'summary': 'Meta WhatsApp Cloud API for school admissions messaging',
    'description': """
WhatsApp integration for kAI ERP using the Meta Cloud API.

Features:
- Send template and free-text messages
- Receive inbound replies via webhook
- Delivery status tracking
- Conversation inbox and reply wizard
- Settings for tokens, templates, and webhook verification
- Configurable admission notification rules (state → Meta template)

Requires kAI ERP (kaierp) for admission-linked messaging. Other clients map
their own admission states and Meta templates via Notification Rules —
no Python edits required.
    """,
    'author': 'kAIzenEd Innovations',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'kaierp',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/whatsapp_data.xml',
        'views/whatsapp_message_view.xml',
        'views/whatsapp_event_rule_view.xml',
        'views/res_config_settings_views.xml',
        'views/admission_view.xml',
        'views/student_view.xml',
        'wizard/whatsapp_reply_wizard_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kaierp_whatsapp/static/src/css/whatsapp_chat.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': True,
    'post_init_hook': 'post_init_hook',
}
