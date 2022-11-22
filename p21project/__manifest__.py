# -*- coding: utf-8 -*-
{
    'name': "P21 Project extension",

    'summary': """
        Changes to Project module for P21""",

    'description': """
        List of changes this module makes to Project module for P21
        (Also small change to res.users)

        Add fields to project.project
        * cust_po (char)
        * p21_so (char)
        * days_bought (float)
        * hours_per_day (float)
        * non_std_ratio (float)
        * days_work_std (float) (compute)
        * days_work_non_std (float) (compute)
        * notify_ids (m2m)
        * budget_notify_sent (bool)
        * notify_budget (bool)
        * notify_threshold (int) (percent)
        * days_pre_work (float)
        * hold_inv_till (date)

        Above fields added to the project edit form (project.edit_project)

        Customer field moved to top of project edit form (project.edit_project)
        and also made mandatory

        Customer, Our SO and company fields added to the project quick-create form
        (project.project_project_view_form_simplified)

        Methods added to model to compute value of the days_work... fields
        based on hours entered in the timesheets of the project.

        Code in project.project module sends over-budget warning email, based on the 
        'notify' fields above. Uses the mail template proj_budget_email_template.

        Our SO number and direct link to project details, added to project kanban view.

        Added fields to res.users
        * ical_token (char) (compute)
        * ical_url (char) (compute)

        Modified the user prefs form base.view_users_form_simple_modif
        to display new ical_url field above

        Added new web controller with route /p21project/plan_cal that exports a users
        planning calendar in iCal format, for Outlook integration.

        Added a 'stat' button to the top of the project-task form to show timesheet 
        hours total

        Added a 'project status' field (open/suspended/closed) and default filter
        on kanban only shows open projects

        Altered default search on many2one fields in other models, that reference project,
        so that the search looks in customer name and project SO also.

        Appended SO number to end of project name in project lookups

        Added exclude_proj_days to task, so that timesheets from that task
        are not counted in total days worked on project

        Added new tab to project form, to show order status data

        Displayed the project list (tree) view

        2 new statuses for project, and auto-update to in-progress when first timesheet slot created

        Can require some projects to have timesheet description field mandatory

        Added 'stat' button to partner (customer) form, linking to projects

        Fields on project to block timesheets if days bought is used up

    """,

    'author': "Eanna Sheehan",
    'website': "http://www.plannet21.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Test',
    'version': '0.6',

    # any module necessary for this one to work correctly
    'depends': ['base', 'project', 'timesheet_grid', 'p21timesheet'],

    # always loaded
    'data': [
        'security/my_security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'wizards/wiz_views.xml',
        'views/templates.xml',
        'data/config_data.xml',
        'data/proj_budget_email_template.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
