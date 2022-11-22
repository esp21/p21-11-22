# -*- coding: utf-8 -*-
{
    'name': "P21 Employee extension",

    'summary': """
        Changes to Employee module for P21""",

    'description': """
        List of changes this module makes to Employee module for P21
        
        * New Selection office_name in hr.employee
        * New Date start_date in hr.employee
        * New Selection seniority in hr.employee
    """,

    'author': "Eanna Sheehan",
    'website': "http://www.plannet21.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Test',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr'],

    # always loaded
    'data': [
        'security/my_security.xml',
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
