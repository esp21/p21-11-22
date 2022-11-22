# -*- coding: utf-8 -*-
{
    'name': "P21 Contacts extension",

    'summary': """
        Extra features for the contacts app""",

    'description': """
        Module that extends the default contacts app
    """,

    'author': "Eanna Sheehan",
    'website': "http://www.plannet21.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Test',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'calendar', 'crm'],

    # always loaded
    'data': [
        'security/expenses_security.xml',
        'data/cronjobs.xml',
        'data/inactive_account_template.xml',
        'security/ir.model.access.csv',
	'views/window_actions.xml',
        'views/contact_sage_link.xml',
        'views/contact_last_activity_and_group.xml',
        'wizards/wiz_views.xml',
        'data/config_data.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
