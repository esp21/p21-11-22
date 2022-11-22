# -*- coding: utf-8 -*-
{
    'name': "P21 Approvals extension",

    'summary': """
        Changes to Approvals module for P21""",

    'description': """
        List of changes this module makes to Approvals module for P21
        
        * Added several new fields to approval request and approval category, for P21 change reqs
        * New auto-email to notify list, after request is submitted.
        * New calendar view (multi-company) that shows requests that have a period of dates
        * Cross-company check if new booking clashes with one in the same dates & category
        * Enabled archiving on approvals

    """,

    'author': "Eanna Sheehan",
    'website': "http://www.plannet21.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Test',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','approvals', 'web_gantt'],

    # always loaded
    'data': [
        'security/my_security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'wizards/wiz_views.xml',
        'views/templates.xml',
        'data/config_data.xml',
        'data/approve_notify_email_template.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
