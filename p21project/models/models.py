# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
import string
import random
_logger = logging.getLogger(__name__)

# Adding a status lookup table for projects, so we can use the sequence field
# to set the column order in a Kanban view
class projStatus(models.Model):
    _name="p21project.projectstatus"
    _order="sequence, id"

    name = fields.Char(
        string="Status",
        required=True
    )

    sequence = fields.Integer(default=1)

class extProject(models.Model):
    _name="project.project"  

    # Use mail module to write changes to chatter audit log
    _inherit = ['project.project', 'mail.thread', 'mail.activity.mixin']    

    def _compute_default_notify(self):
        p21_value = 'P21_odoo@plannet21.ie'
        agile_value = 'projectoffice@agilenetworks.ie'

        _logger.info(self.env.company.name)

        if 'Agile' not in self.env.company.name:
            return p21_value
        else:
            return agile_value

    # Validation constraints for some of the fields below
    _sql_constraints = [('hrs_per_day_positive', 'CHECK(hours_per_day >= 1)',
        'Number of working hours in a day must not be less than one.'),
        ('non_std_ratio_positive', 'CHECK(non_std_ratio >= 1)',
        'The ratio for calculationg non-standard hours must not be less than one.'),
        ('notify_threshold_range', 'CHECK(notify_threshold > 4 AND notify_threshold < 76)',
        'The budget notification percentage must be between 5 and 75 percent')]

    # Make existing customer field mandatory
    partner_id = fields.Many2one(
        "res.partner", 
        required = True)
    
    # Default email address where notifications are sent
    default_notify = fields.Char(
        string = 'Default notify email',
        default = _compute_default_notify,
        required = True,
        tracking = True,
        help = "Default address where over-budget notifications are sent"
    )

    # Fields to hold PO & SO nums, and days bought
    cust_po = fields.Char(
        string = 'Cust PO Num',
        help = "The customer's PO number for this project"
    )

    p21_so = fields.Char(
        string = 'Our SO Num',
        help = "Our SO number for this project, from accounts", 
        required = True
    )

    days_bought = fields.Float(
        string = 'Days Bought',
        digits = (5,2),
        tracking = True,
        help = "Number of days the customer has agreed to pay for"
    )

    # Fields showing total DAYS worked, including params to calculate them
    
    # How many worked hours are in one day (for converting timesheet hours to days)
    hours_per_day = fields.Float(
        string = "Hours in day",
        digits = (5,2),
        default = 8,
        help = "For calculating # days worked. How many worked hours are in a day.",
        tracking = True,
        required = True
    )

    # When converting tiemsheet hours to days worked, how many normal hours, 
    # should one non-std hour be equal to
    non_std_ratio = fields.Float(
        string = "Non-std ratio",
        digits = (5,2),
        default = 1,
        help = "For calculating # days worked. How many normal hours, should one non-std hour be equal to?",
        required = True,
        tracking = True
    )

    # Read only calc field showing total standard days worked
    days_work_std = fields.Float(
        string = "Std days worked",
        digits = (5,2),
        readonly = True,
        help = "Total number of standard-hours days recorded on timesheets",
        compute = '_calc_std_days_worked',
        store = True,
        tracking = True
    )

    # Read only calc field showing percentage of days used up
    percent_used = fields.Float(
        string = "Used %",
        digits = (5,0),
        readonly = True,
        help = "Percentage of days-bought that have been used",
        compute = '_calc_used_percent',
        store = True,
        tracking = True
    )

    # Read only calc field showing total non-standard days worked
    days_work_non_std = fields.Float(
        string = "Non-std days",
        digits = (5,2),
        readonly = True,
        help = "Total number of non-standard-hours days recorded on timesheets",
        compute = '_calc_non_std_days_worked',
        store = True,
        tracking = True
    )

    # List of people we want to notify if the budget is running out
    notify_ids = fields.Many2many(
        'res.users',
        string = "Extra notifications to",
        relation='project_notify_res_users_rel',
        help = 'List of people we want to notify if the budget is running out',
        domain=[('share', '=', False)]
    )

    # Have we sent the out-of-budget notification email?
    budget_notify_sent = fields.Boolean(default=False, tracking = True)

    # Should we send budget notifications for this project?
    notify_budget = fields.Boolean(
        default=True, 
        string = 'Notify re over-budget',
        tracking = True,
        help = 'Should we send budget notifications for this project?')

    # What percentage of budgeted days should be left, when we send a notification
    notify_threshold = fields.Integer(
        default = 15,
        string = 'Budget notify %',
        tracking = True,
        help = 'What percentage of budgeted days should be left, when we send a notification'
    )

    # What is the status of the project?
    status = fields.Selection(
        selection=[
            ('nokit', 'Pre-Planning NO Kit'),
            ('preplan','Pre-Planning With Kit'), 
            ('plan','Planned'), 
            ('in-prog','In Progress'), 
            ('suspend', 'Suspended'), 
            ('closed', 'Closed'),
            ('invoiced', 'Invoiced')],
        default = 'preplan',
        string = 'Old Status',
        required = True
    )
    
    def _default_new_status(self):
         return self.env['p21project.projectstatus'].search([('name', '=', 'Pre-Planning With Kit')], limit=1).id

    new_status = fields.Many2one('p21project.projectstatus', 
        string='Status', 
        default = _default_new_status,
        required=True, 
        tracking = True)

    days_pre_work = fields.Float(
        string = 'Days pre-work',
        digits = (5,2),
        tracking = True,
        help = "Number of days worked prior to this project, that will be allocated against days bought."
    )

    hold_inv_till = fields.Date(
        string = 'Hold invoice till',
        tracking = True,
        help = "Invoice must not issue till after this date"
    )

    # Are timesheet line descriptions mandatory for this project?
    ts_desc_reqd = fields.Boolean(
        default=False, 
        string = 'Timesheet Desc Reqd',
        tracking = True,
        help = 'Should descriptions be mandatory on timesheet lines?')    

    # Should we prevent engineers adding timesheets, if bought time is used up on this project?
    prevent_overbudget = fields.Boolean(
        default=False, 
        string = 'Block TS over-budget',
        tracking = True,
        help = 'Should timesheets be prevented if days-bought are fully used?')    

    timesheet_warn_text = fields.Char(
        string = 'Block TS warning',
        tracking = True,
        help = "Text of warning message to show when blocking a timesheet"
    )

    # Ensure warning text is supplied, if prevent_overbudget is ticked
    @api.constrains('prevent_overbudget')
    def _check_warn_text(self):
        for record in self:
            if record.prevent_overbudget and record.prevent_overbudget == True and not record.timesheet_warn_text:
                raise models.ValidationError('If you want to block over-budget timesheets, you must enter text for the warning message.')

    # Populate the percentage used
    @api.depends('days_pre_work', 'days_work_non_std', 'days_work_std', 'days_bought')
    def _calc_used_percent(self):
        for proj in self:
            if proj.days_bought > 0:
                totalWorked = proj.days_pre_work + proj.days_work_non_std + proj.days_work_std
                proj.percent_used = (totalWorked / proj.days_bought) * 100
            else:
                proj.percent_used = 0

    # Populate the two days-worked calculated fields
    @api.depends('timesheet_ids.non_std_hours', 'timesheet_ids.unit_amount',
        'hours_per_day', 'timesheet_ids.task_id.exclude_proj_days')
    def _calc_std_days_worked(self):
        for proj in self:
            days_worked = 0.0

            for line in proj.timesheet_ids:
                # Only include timesheet lines that have a task
                if line.task_id.exclude_proj_days == False:
                    days_worked += (line.unit_amount - line.non_std_hours) / proj.hours_per_day

                # Auto-change project status to in-progress, if not already there
                if line.unit_amount > 0 and (proj.new_status.name == 'Pre-Planning NO Kit' or proj.new_status.name == 'Pre-Planning With Kit' or proj.new_status.name == 'Planned'):
                    
                    new_id = self.env['p21project.projectstatus'].search([('name', '=', 'In Progress')], limit=1).id 
                    proj.new_status = new_id            
                    
            proj.days_work_std = days_worked

            proj._send_budget_mail_maybe()

    @api.depends('timesheet_ids.non_std_hours', 'hours_per_day', 'non_std_ratio', 
        'timesheet_ids.task_id.exclude_proj_days')
    def _calc_non_std_days_worked(self):
        for proj in self:
            days_worked = 0.0

            for line in proj.timesheet_ids:
                # Only include timesheet lines that have a task
                if line.task_id.exclude_proj_days == False:
                    days_worked += (line.non_std_hours * proj.non_std_ratio) / proj.hours_per_day

            proj.days_work_non_std = days_worked
            
            proj._send_budget_mail_maybe()
    
    # Check if the over-budget notification should be sent, and send it
    def _send_budget_mail_maybe(self):
        for proj in self:
            
            # Prevent mail being sent twice on the same transaction
            if self.env.context.get('MailAlreadySent'):
                return

            if proj.notify_budget == True and proj.budget_notify_sent == False and proj.days_bought > 0:
                
                thresholdValue = proj.days_bought * (proj.notify_threshold / 100)
                totalDaysWorked = proj.days_work_std + proj.days_work_non_std + proj.days_pre_work

                # _logger.info('thresholdValue: %s - totalDaysWorked: %s', thresholdValue, totalDaysWorked)

                if (proj.days_bought - totalDaysWorked) < thresholdValue:
                    # Send the mail

                    # First get the cc recipients list
                    ccListObj = proj.mapped('notify_ids.email')
                    # _logger.info('notify_ids: %s', ccListObj)

                    ccFormatted = ''
                    if len(ccListObj) > 0:
                        ccFormatted = ','.join(ccListObj)

                    
                    if proj.partner_id:
                        custName = proj.partner_id.name

                    ctx = dict(proj._context or {})
                    ctx['to'] = proj.default_notify
                    ctx['cc'] = ccFormatted
                    ctx['proj'] = proj.name
                    ctx['cust'] = custName
                    ctx['bought'] = proj.days_bought
                    ctx['workstd'] = proj.days_work_std
                    ctx['worknon'] = proj.days_work_non_std
                    ctx['workpre'] = proj.days_pre_work
                    
                    template_id = self.env.ref('p21project.proj_budget_email_template').id
                    template = self.env['mail.template'].browse(template_id)
                    template.with_context(ctx).send_mail(proj.id, force_send=True)

                    # Set the flag that prevents repeat sending
                    proj.budget_notify_sent = True

                    # Set context flag to prevent a duplicate mail being sent now
                    self = self.with_context(MailAlreadySent=True)

    def write(self, values):
        # _logger.info('p21project  write')

        # Prevent archiving unless at Invoiced or Suspended status
        if 'active' in values and values['active'] == False:
            if self.new_status.name == 'Invoiced' or self.new_status.name == 'Suspended':
                pass
            else:
                raise ValidationError('Only invoiced or suspended projects can be archived!')

        # Override the update of days_bought, to unset budget_notify_sent
        # if days_bought is increased
        if 'days_bought' in values and 'budget_notify_sent' not in values:
            values['budget_notify_sent'] = False        
            
        # Save the changes, so our code that checks if mail should be sent
        # can see the updated values
        saveResult =  super(extProject, self).write(values)

        # Prevent mail being sent twice on the same transaction
        if self.env.context.get('MailAlreadySent'):
            return saveResult

        # If any fields that affect the project budget warning are changed,
        # check if we need to send the mail
        else:
            if ('hours_per_day' in values 
            or 'non_std_ratio' in values 
            or 'days_bought' in values
            or 'days_work_std' in values
            or 'days_work_non_std' in values
            or 'days_pre_work' in values):

                self._send_budget_mail_maybe()

            return saveResult

    def _merge_projs(self):
        # Merge projects

        # Ensure there's only two projects selected
        proj_count = 0
        keep_proj_id = 0
        trash_proj_id = 0
        keep_proj_name = ''
        trash_proj_name = ''

        for proj in self:
            proj_count += 1

            # Default to keeping the first project
            if proj_count == 1:
                keep_proj_id = proj.id
                keep_proj_name = proj.name
            else:
                trash_proj_id = proj.id
                trash_proj_name = proj.name

        if proj_count != 2:
            raise models.ValidationError('You should select exactly two projects. No more. No less.')

        # Find the tasks for the trash project
        taskObj = self.env['project.task']
        trashTasks = taskObj.sudo().search([('project_id', '=', trash_proj_id)])

        for task in trashTasks:            
            task.sudo().update({'project_id': keep_proj_id})
        
        # Find the task analysis recs for the trash project
        analObj = self.env['report.project.task.user']
        trashAnalys = analObj.sudo().search([('project_id', '=', trash_proj_id)])

        for anal in trashAnalys:            
            task.sudo().update({'project_id': keep_proj_id})
        
        # Find timesheet lines for the trash project
        timesheetObj = self.env['account.analytic.line']
        trashLines = timesheetObj.sudo().search([('project_id', '=', trash_proj_id)])

        for line in trashLines:            
            line.sudo().update({'project_id': keep_proj_id})

        # Find planning slots for the trash project
        slotObj = self.env['planning.slot']
        trashSlots = slotObj.sudo().search([('project_id', '=', trash_proj_id)])

        for slot in trashSlots:            
            slot.sudo().update({'project_id': keep_proj_id})

        # Find sub-task references for tasks of the trash project
        subObj = self.env['project.task']
        subTasks = subObj.sudo().search([('subtask_project_id', '=', trash_proj_id)])

        for sub in subTasks:            
            sub.sudo().update({'subtask_project_id': keep_proj_id})

        # Find sub-task references for the trash project
        projObj = self.env['project.project']
        trashItems = projObj.sudo().search([('subtask_project_id', '=', trash_proj_id)])

        for proj in trashItems:            
            proj.sudo().update({'subtask_project_id': keep_proj_id})

        # Write notes in the history of the projects
        for proj in self:

            if proj.id == keep_proj_id:
                proj.message_post(body = 'PROJECT: (' + trash_proj_name + ') IS BEING MERGED INTO THIS ONE', subject=None)
            elif proj.id == trash_proj_id:
                proj.active = False # Archive the trash project
                proj.message_post(body = 'THIS PROJECT CLOSED AFTER MERGE. IS MERGED INTO (' + keep_proj_name + ')', subject=None)        

    # Temporary method which will migrate old 'selection' status field
    # to new many2one new_status field
    def _migrate_status(self):
        for proj in self:
            
            # Default status
            lookupString = 'Pre-Planning With Kit'
            
            if proj.status == 'nokit':
                lookupString = 'Pre-Planning NO Kit'
            
            if proj.status == 'plan':
                lookupString = 'Planned'
            
            if proj.status == 'in-prog':
                lookupString = 'In Progress'
            
            if proj.status == 'suspend':
                lookupString = 'Suspended'
            
            if proj.status == 'closed':
                lookupString = 'Closed'
            
            if proj.status == 'invoiced':
                lookupString = 'Invoiced'
            
            new_id = self.env['p21project.projectstatus'].search([('name', '=', lookupString)], limit=1).id                  

            proj.new_status = new_id



    
    # Extend the search used on many2one dropdowns, to include
    # customer name & our SO num
    @api.model 
    def _name_search(self, name='', args=None, operator='ilike', 
                limit=100, name_get_uid=None): 

        _logger.info('search_args: %s search_name: %s operator: %s ', args, name, operator)
        
        # Preserve any args that were passed in
        args = args or [] 

        newArgs = []

        # The user's search string is the 'name' param
        # Only proceed if the search string is not blank
        # and the search operator is ilike
        if not(name == '' and operator == 'ilike'): 
            newArgs += ['|', '|', 
                ('name', operator, name), 
                ('p21_so', operator, name), 
                ('partner_id.name', operator, name) 
                ] 

            _logger.info('new_args: %s ', newArgs + args )

        # Send back the modified search args
        #return super(extProject, self)._name_search( 
        #    name=name, args=newArgs, operator=operator, 
        #    limit=limit, name_get_uid=name_get_uid)

        return self._search(newArgs + args, 
            limit = limit, access_rights_uid = name_get_uid)

    # Append the SO to the end of the project name
    def name_get(self):
        result = []
        for rec in self:
            rec_name = "%s (SO:%s)" % (rec.name, rec.p21_so)
            result.append((rec.id,rec_name))

        return result
        
        
class extUser(models.Model):
    _name="res.users"
    _inherit="res.users"    

    def _make_ical_token(self):
        # Generate random 6-char alpha-numeric string
        tokenLength = 6
        chars=string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(tokenLength))

    # Unique token for this user
    ical_token = fields.Char(
        default = _make_ical_token
    )

    # The full URL, including token, which we will show to the user
    ical_url = fields.Char(
        compute = '_make_ical_url',
        string = 'Planning iCal URL',
        readonly = True,
        help = 'Use this URL to subscribe Outlook to your Odoo planning calendar'
    )

    @api.depends('ical_token')
    def _make_ical_url(self):
        urlRoot = 'https://crm.itwarehouse.ie/p21project/plan_cal?t='
        for user in self:
            user.ical_url = urlRoot + user.ical_token

    # This hack required to allow ordinary users see the URL field on thier 'my profile' form
    def __init__(self, pool, cr):
        #  Override of __init__ to add access rights on ical_url & ical_token.             
        #  Access rights are disabled by default, but allowed            
        #  on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.  
        init_res = super(extUser, self).__init__(pool, cr)        
        # duplicate list to avoid modifying the original reference        
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)        
        type(self).SELF_WRITEABLE_FIELDS.extend(['ical_url', 'ical_token'])        
        # duplicate list to avoid modifying the original reference        
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)        
        type(self).SELF_READABLE_FIELDS.extend(['ical_url', 'ical_token'])        
        return init_res

class extTask(models.Model):
    _name="project.task"
    _inherit="project.task"    

    # Should we prevent work done on this task, from counting towards project days total ?
    exclude_proj_days = fields.Boolean(
        default=False, 
        string = 'Exclude Proj Totals',
        tracking = True,
        help = 'Should we prevent work done on this task, from counting towards project days total ?')

    ms_proj_line_id = fields.Integer(
        default = 0,
        help = 'Internal item ID from MS Proj file'
    )

# Add a count of projects to the partner (customer) table
class extPartner(models.Model):
    _name="res.partner"
    _inherit="res.partner"    

    project_count = fields.Integer(
        compute="_compute_proj_count"
    )

    def _compute_proj_count(self):
        projModel = self.env['project.project']
        for cust in self:
            cust.project_count = projModel.search_count([('partner_id','=',cust.id)])