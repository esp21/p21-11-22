# -*- coding: utf-8 -*-
{
    'name': "P21 Timesheet extension",

    'summary': """
        Changes to Timesheet module for P21""",

    'description': """
        List of changes this module makes to Timesheet module for P21
        
        * Added new field non_std_hours to account.analytic.line
        * Added above field to editable list hr_timesheet.hr_timesheet_line_tree
        * Check if timesheet desc is mandatory for project
        * Block adding timesheet line if project is over-budget, and disallows overbudget timesheets

    """,

    'author': "Eanna Sheehan",
    'website': "http://www.plannet21.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Test',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','timesheet_grid'],

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
