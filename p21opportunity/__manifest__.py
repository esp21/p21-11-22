# -*- coding: utf-8 -*-
{
    'name': "P21 Opportunities extension",

    'summary': """
        Extra features for the CRM app""",

    'description': """
        Module that extends the default opportunities app
    """,

    'author': "Eanna Sheehan",
    'website': "http://www.plannet21.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Test',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','crm', 'p21contact'],

    # always loaded
    'data': [
        'security/oppor_security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'wizards/wiz_views.xml',
        'views/templates.xml',
        'data/config_data.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
