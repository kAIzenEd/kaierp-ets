# -*- coding: utf-8 -*-
{
    'name': 'kAI ERP',
    'version': '19.0.1.3.6',
    'category': 'Education',
    'summary': 'Complete school management: students, classes, admissions, grades & transcripts',
    'description': """
        kAI-ERP
        ========================
        A comprehensive school management addon for Odoo 19 featuring:
        - Custom home dashboard with image, shortcuts, and live date/time
        - Student profiles with full academic records
        - Class management with student enrollment
        - Admissions pipeline with approval workflow
        - Grades and transcript generation
        - Integration with Odoo Calendar and To-Do
        - Fee tracking and payment management
        - Attendance tracking
        - Teacher/Staff management
        - Announcements board
    """,
    'author': 'kAIzenEd Innovations',
    'depends': [
        'base',
        'mail',
        'calendar',
        'project',         # For To-Do integration
        'web',
        'portal',
        'product',
        'account',         # For fee invoicing
    ],
    'data': [
        # Security
        'security/school_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/school_sequence.xml',
        'data/school_data.xml',
        'data/api_integration.xml',
        'data/whatsapp_data.xml',
        'data/school_fee_products.xml',

        # Views
        'views/school_dashboard_view.xml',
        'views/login_templates.xml',
        'views/student_view.xml',
        'views/class_view.xml',
        'views/admission_view.xml',
        'views/grade_view.xml',
        'views/attendance_view.xml',
        'views/teacher_view.xml',
        'views/registrar_view.xml',
        'views/announcement_view.xml',
        'views/fee_view.xml',
        'views/school_menu.xml',
        'views/res_config_settings_views.xml',
        'views/whatsapp_message_view.xml',

        # Wizards
        'wizard/enroll_student_wizard_view.xml',
        'wizard/bulk_grade_wizard_view.xml',
        'wizard/take_attendance_wizard_view.xml',
        'wizard/whatsapp_reply_wizard_view.xml',
        'wizard/assign_fee_wizard_view.xml',
        # Reports
        'report/transcript_report.xml',
        'report/report_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kaierp/static/src/css/school_dashboard.css',
            'kaierp/static/src/js/school_dashboard.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    # 'external_dependencies': {
    #     'python': [
    #         'odoorpc',
    #         'crewai',
    #     ],
    # },
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
    # 'images': ['static/description/icon.png'],
}