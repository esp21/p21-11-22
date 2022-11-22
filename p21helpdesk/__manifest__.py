# -*- coding: utf-8 -*-
{
    'name': "p21helpdesk",

    'summary': """
        Module to add functionality to Helpdesk Enterprise Module as per PlanNet21 Communications needs""",

    'description': """
        Module to add functionality to Helpdesk Enterprise Module as per PlanNet21 Communications needs
    """,

    'author': "PlanNet21 Communications",
    'website': "https://www.plannet21.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'helpdesk', 'p21approval', 'p21timesheet', 'p21contact'],

    # always loaded
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'data/mail_template_all.xml',
        'data/notification_config.xml',
        'data/cronjobs.xml'
        #'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo/demo.xml',
    ],
}
