# -*- coding: utf-8 -*-
{
    'name': "P21 Planning extension",

    'summary': """
        Changes to Planning module for P21""",

    'description': """
        List of changes this module makes to Planning module for P21
        
        * Wizard that allows engineers change times of thier own planning slots.
        * Wizard that allows engineers delete thier own planning slots.
        * Wizard that allows engineers create planning slots for themselves.
        * New create_timesheet bool field on planning.slot
        * Override "create" on planning.slot to allow populating a timesheet line
        * Update project status to 'planned' if not already, when slot created
        * Send warning email when double-book on planning calendar

    """,

    'author': "Eanna Sheehan",
    'website': "http://www.plannet21.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Test',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','timesheet_grid','p21timesheet'],

    # always loaded
    'data': [
        'security/my_security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'wizards/wiz_views.xml',
        'views/templates.xml',
        'data/config_data.xml',
        'data/double_book_email_template.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
