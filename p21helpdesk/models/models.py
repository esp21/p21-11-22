# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

#Config model used to set up the email addresses
class helpdesk_config(models.Model):
    _name = 'p21helpdesk.helpdesk_config'
    _description = 'Helpdesk Mail Config'

    support_manager_email = fields.Char('Support Manager email', size=50, required=False)
    engineering_manager_email = fields.Char('Engineering Manager email', size=50, required=False)
    cto_email = fields.Char('CTO email', size=50, required=False)
    ceo_email = fields.Char('CEO email', size=50, required=False)


#Closing results model
class closing_result_code(models.Model):
    _name = 'p21helpdesk.closing_result_code'
    name = fields.Char('Result Code', size=30, required=False)

#Category model
class category(models.Model):
    _name = 'p21helpdesk.category'
    name = fields.Char('Category', size=30, required=False)
    category_path = fields.Char('Category Path', size=50, required=False)

#Modify helpdesk.ticket model
class helpdesk_mixins(models.Model):
    _inherit = 'helpdesk.ticket'

    #Calcluated field to show Partner status and P21_Priority_mapping
    x_status = fields.Char('Partner Status', size=30, compute='partner_status', required=False, readonly=True)
    x_p21_priority_mapping = fields.Char('P21 Priority mapping', size=30, compute='p21_priority', required=False, readonly=True)

    #Calculated field for ticket active time
    x_active_time_seconds = fields.Integer('Active time in seconds', default=0)
    x_inactive_time_seconds = fields.Integer('Inactive time in seconds', default=0)
    x_active_time_human_readable = fields.Char('Active time', compute='get_active_time')
    x_excluded_stage_initial_date = fields.Datetime('Excluded Stage start time', required=False, default=None)

    #Problem ticket
    x_is_problem_ticket = fields.Boolean(default=False, string = 'Problem Ticket', help = "Is this a recurring problem already seen in other tickets?")
    x_problem_ticket_source = fields.Many2one('helpdesk.ticket', string='Source problem ticket', required=False)

    #Timesheet management
    x_project = fields.Many2one('project.project', string='Project', required=False)
    x_create_timesheet = fields.Boolean(default=True, string = 'Populate timesheet', help = "Should a line be added to the engineer's timesheet, for this date?")    
    x_task = fields.Many2one('project.task', string='Task', required=False)

    #Add exta engineers
    x_extra_engineers = fields.Many2many('res.users', string='Other Assigned', required=False)

    #Uncategorized new fields
    x_customer_reference = fields.Char('Customer Internal Reference', size=30, required=False)
    #Two fields for categories. Char field / selection / or a relationship to a new model called category?
    x_categories = fields.Many2many('p21helpdesk.category', string='Categories', required=False)
    x_reported_by = fields.Many2one('res.users', string='Closed by', required=False, default=lambda self: self.env.user)
    x_tac_id = fields.Char('TAC ID', size=30, required=False)
    
    #Initial Response fields
    x_initial_response_complete = fields.Boolean('Initial Response Complete', default=False)
    x_initial_response_at = fields.Datetime('Initial response At', required=False)
    x_initial_response_within_SLA = fields.Boolean('Within SLA', default=False)
    x_initial_response_notes = fields.Char('Initial Response Notes', size=300, required=False)

    #Change Request fields
    x_is_change_request = fields.Boolean('Is Change Request', default=False)
    x_is_change_request_complexity = fields.Selection([('minor', 'Minor'), ('major', 'Major'), ('complex', 'Complex')], string='Complexity') #Minor / Major / Complex
    x_change_request_approval = fields.Many2one('approval.request', string='Change Request Approval', required=False, readonly=True)

    #PlanNet21 Internal Issues fields
    x_p21_internal_issue = fields.Boolean('P21 Internal Issue', default=False)
    x_p21_internal_date_detected = fields.Datetime('Date Detected', required=False)
    x_p21_internal_rca_provided = fields.Boolean('RCA Provided', default=False)
    x_p21_internal_sec_team_closed = fields.Boolean('Sec Team Closed', default=False)
    x_p21_internal_gdpr_applies = fields.Boolean('GDPR applies', default=False)
    x_p21_internal_dpc_notified_72hrs = fields.Boolean('DPC Notified 72hrs', default=False)
    x_p21_internal_security_incident = fields.Boolean('Security Incident', default=False)

    #Fields for closing the ticket
    x_closing_reason = fields.Selection([('resolved', 'Resolved'), ('no_issue_found', 'No issue found'), ('no_resolution', 'No resolution'), ('known_error', 'Known Error')], string='Closing Reason') #Resolved / No issue found / No resolution / Known error
    x_closing_result_code = fields.Many2many('p21helpdesk.closing_result_code', string='Result codes', required=False)
    x_closing_work_ended = fields.Datetime('Work ended', required=False)
    x_closing_closed_by = fields.Many2one('res.users', string='Closed by', required=False) #For default active_user add ->  default=lambda self: self.env.user
    x_closing_closing_notes = fields.Char('Closing Notes', size=100, required=False)

    #Fields for email notifications (Escalation matrix)
    x_email_am_latest = fields.Datetime('Account Manager latest notification', required=False)
    x_email_support_latest = fields.Datetime('Support latest notification', required=False)
    x_email_engineering_latest = fields.Datetime('Engineering latest notification', required=False)
    x_email_cto_latest = fields.Datetime('CTO latest notification', required=False)
    x_email_ceo_latest = fields.Datetime('CEO latest notification', required=False)


    @api.model
    def create(self, values):
        #Creates the record in the DB. 
        rec = super(helpdesk_mixins, self).create(values)

        #Send notifications to assigned engineers
        self.is_assigned(values, rec)
        self.asignee_mails(values, rec)

        #Send notifications according to escalation matrix
        self.escalation_matrix(values, rec)

        #Create a record in timesheets
        self.create_timesheet_record(values, rec)

        #CR check
        self.is_cr(values, rec)

        #Problem ticket check
        self.problem_ticket_check(values)

        return rec

    def write(self, values): 
        #Problem ticket check
        self.problem_ticket_check(values)

        #CR check
        self.cr_stage_change(values)

        #Ticket active time calculations
        self.excluded_stage_change(values)

        #Things that are done when creating a record are done in the updates only under certain circumstances
        #-------------------------------------------
        #Send notifications to assigned engineers
        if self.user_id.id != values.get('user_id'): #Did the assigned user change?
            self.is_assigned(values, self)
        if values.get('x_extra_engineers') is not None and self.x_extra_engineers.ids != values.get('x_extra_engineers'):
            self.asignee_mails(values, self)

        #Send notifications according to escalation matrix
        # if self.priority != values.get('priority'):
        #     self.escalation_matrix(values, self)

        #CR check
        self.is_cr_write_method(values, self)

        #Create a record in timesheets
        if self.x_create_timesheet and self.x_project.id != values.get('x_project'):
            self.create_timesheet_record_write_method(values, self)

        #Creates the record in the DB.
        #-------------------------------------------
        rec = super(helpdesk_mixins, self).write(values)

        return rec

    #If ticket is assigned, send notification
    def is_assigned(self, values, rec):
        user_id = values.get('user_id')
        if user_id is not None:
            base_url = self.get_current_url(rec)
            user = self.env['res.users'].sudo().browse(user_id)
            self.send_email(rec, user.user_id.partner_id.email, 'Asignee', base_url)

    #If the ticket is a CR, move to AM Approval Pending stage and create an approval for it
    def is_cr(self, values, rec):
        if rec.x_is_change_request == True:
            if not rec.partner_id.user_id.id:
                raise UserError('Please select a Customer if you want to flag this ticket as a Change Request')
            if not rec.x_is_change_request_complexity:
                raise UserError('Please select the complexity of the Change Request')

            #Get current date
            now = datetime.now()

            #Create approval ---------------------
            #Get the Approval Category
            approval_category = self.env['approval.category'].sudo().search([('name', '=', 'Helpdesk CR Approval')], limit=1)
            if not approval_category.id:
                approval_category = self.env['approval.category'].sudo().create({"name":"Helpdesk CR Approval"})

            approver = self.env['approval.approver'].sudo().search([('user_id', '=', rec.partner_id.user_id.id)], limit=1)
            approver_data = {
                'user_id': rec.partner_id.user_id.id,
                'status' : 'new'
            }
            approver = self.env['approval.approver'].sudo().create(approver_data)

            approval_data = {
                'name': values.get('name'),
                'date': now, 
                'request_owner_id': self.env.user.id,
                'category_id':approval_category.id,
                'approver_ids': [(4, approver.id)]
            }
            approval = self.env['approval.request'].sudo().create(approval_data)
            approval.approver_ids = [(4, approver.id)]

            #Change stage and link to the newly created approval
            am_pending_stage = self.env['helpdesk.stage'].sudo().search([('name', '=', 'AM Approval Pending')])
            rec.stage_id = am_pending_stage.id
            rec.x_change_request_approval = approval.id

    #If the ticket is a CR, move to AM Approval Pending stage and create an approval for it
    def is_cr_write_method(self, values, rec):
        if values.get('x_is_change_request') == True:
            if not rec.partner_id.user_id.id:
                raise UserError('Please select a Customer and save this record first if you want to flag this ticket as a Change Request')
            if not values.get('x_is_change_request_complexity'):
                raise UserError('Please select the complexity of the Change Request')

            #Get current date
            now = datetime.now()

            #Create approval ---------------------
            #Get the Approval Category
            approval_category = self.env['approval.category'].sudo().search([('name', '=', 'Helpdesk CR Approval')], limit=1)
            if not approval_category.id:
                approval_category = self.env['approval.category'].sudo().create({"name":"Helpdesk CR Approval"})

            approver = self.env['approval.approver'].sudo().search([('user_id', '=', rec.partner_id.user_id.id)], limit=1)
            approver_data = {
                'user_id': rec.partner_id.user_id.id,
                'status' : 'new'
            }
            approver = self.env['approval.approver'].sudo().create(approver_data)

            approval_data = {
                'name': values.get('name') or self.name,
                'date': now, 
                'request_owner_id': self.env.user.id,
                'category_id':approval_category.id,
                'approver_ids': [(4, approver.id)]
            }
            approval = self.env['approval.request'].sudo().create(approval_data)
            approval.approver_ids = [(4, approver.id)]

            #Change stage and link to the newly created approval
            am_pending_stage = self.env['helpdesk.stage'].sudo().search([('name', '=', 'AM Approval Pending')])
            values['stage_id'] = am_pending_stage.id
            values['x_change_request_approval'] = approval.id


    ##If the stage is AM Approval Pending and we try to move it to another stage, check if it has been approved by the AM
    def cr_stage_change(self, values):
        #Get stage
        am_pending_stage = self.env['helpdesk.stage'].sudo().search([('name', '=', 'AM Approval Pending')])

        #Get the approval. Can´t move to other stage if approval is pending
        if values.get('stage_id') is not None: #Is this an update?
            if self.stage_id.id == am_pending_stage.id and self.stage_id.id != values.get('stage_id'): #Are we moving the ticket from "AM Approval Pending to other stage?"
                if self.x_change_request_approval.request_status in ['new', 'pending']: #Is the approval still pending?
                    raise UserError('The ticket cannot be moved to another stage until the Account Manager approves/rejects the CR')

    #Manage ticket active time count for excluded stages
    def excluded_stage_change(self, values):
        #Get excluded stages
        excluded_stages = self.get_excluded_stages()

        if values.get('stage_id') is not None: #Is this an update?
            now = datetime.now()
            _logger.info(self.stage_id.id)
            _logger.info(excluded_stages)
            #If we are moving FROM an excluded stage, append inactive time and reset x_excluded_stage_initial_date
            if self.stage_id.id in excluded_stages:
                inactive_time_in_current_stage = abs(now - self.x_excluded_stage_initial_date).total_seconds()
                self.x_inactive_time_seconds += inactive_time_in_current_stage
                x_excluded_stage_initial_date = None

            #If we are moving TO an excluded stage, set x_excluded_stage_initial_date
            if values.get('stage_id') in excluded_stages:
                self.x_excluded_stage_initial_date = now

    #Validation for problem tickets
    def problem_ticket_check(self, values):
        if (not values.get('x_problem_ticket_source') and values.get('x_is_problem_ticket')):
            raise UserError('If you want to mark this as a problem ticket, you must select the problem ticket source.')

    #Creates a record for the ticket in Odoo Timesheets
    def create_timesheet_record(self, values, rec):
        if (not values.get('x_project')) and (values.get('x_create_timesheet')):
            raise UserError('If you want to populate the timesheet, you must select the project also.')

        timesheet_option = values.get('x_create_timesheet')
        if timesheet_option != False:
            #We need to lookup some values in the project
            projectObj = self.env['project.project'].sudo().browse(values.get('x_project'))
            accountID = projectObj.analytic_account_id.id
            partnerID = projectObj.partner_id

            #Get the employee's user_id
            #employeeObj = self.env['hr.employee'].sudo().browse(values.get('employee_id'))
            empUserID = self.env.user.id

            #Default datetime
            now = datetime.now()

            timesheetData = {
            'name': values.get('name'),
            'date': now, 
            'amount': 0,
            'unit_amount': 0,
            'product_uom_id': 6,
            'account_id': accountID,
            'user_id' : empUserID,
            'project_id': values.get('x_project'),
            'company_id': self.env.company.id,
            'currency_id': 1,
            'employee_id': values.get('employee_id'),
            'non_std_hours': 0
            }

            #Some optional fields
            if partnerID:
                timesheetData['partner_id'] = partnerID.id

            if values.get('x_task'):
                timesheetData['task_id'] = values.get('x_task')
            else:
                task_dict = {"name":rec.id, "project_id":values.get('x_project')}

                #Does the task already exist?
                task = self.env['project.task'].sudo().search([('name', '=', rec.id),('project_id','=',values.get('x_project'))], limit=1)
                if not task.id:
                    task = self.env['project.task'].sudo().create(task_dict) #Creates task with Ticket ID                    

                timesheetData['task_id'] = task.id
                rec.x_task = task.id

            self.env['account.analytic.line'].sudo().create(timesheetData)

#Creates a record for the ticket in Odoo Timesheets
    def create_timesheet_record_write_method(self, values, rec):
        self.ensure_one()
        if (not values.get('x_project')) and (values.get('x_create_timesheet')):
            _logger.info('inside')
            raise UserError('If you want to populate the timesheet, you must select the project also.')

        if (values.get('x_project') is None and values.get('x_create_timesheet') is None):
            return

        _logger.info('outside')
        _logger.info(values.get('x_project'))
        _logger.info(values.get('x_create_timesheet'))

        timesheet_option = values.get('x_create_timesheet') or self.x_create_timesheet
        if timesheet_option != False:
            #Project id
            proj = values.get('x_project') or self.x_project.id

            #We need to lookup some values in the project
            projectObj = self.env['project.project'].sudo().browse(proj)
            accountID = projectObj.analytic_account_id.id
            partnerID = projectObj.partner_id

            #Get the employee's user_id
            #employeeObj = self.env['hr.employee'].sudo().browse(values.get('employee_id'))
            empUserID = self.env.user.id

            #Default datetime
            now = datetime.now()

            timesheetData = {
            'name': values.get('name') or self.name,
            'date': now, 
            'amount': 0,
            'unit_amount': 0,
            'product_uom_id': 6,
            'account_id': accountID,
            'user_id' : empUserID,
            'project_id': proj,
            'company_id': self.env.company.id,
            'currency_id': 1,
            'employee_id': values.get('employee_id'),
            'non_std_hours': 0
            }

            #Some optional fields
            if partnerID:
                timesheetData['partner_id'] = partnerID.id

            if values.get('x_task'):
                timesheetData['task_id'] = values.get('x_task') or self.x_task
            else:
                task_dict = {"name":self.id, "project_id":proj}

                #Does the task already exist?
                task = self.env['project.task'].sudo().search([('name', '=', self.id),('project_id','=',proj)], limit=1)
                if not task.id:
                    task = self.env['project.task'].sudo().create(task_dict) #Creates task with Ticket ID
                    
                timesheetData['task_id'] = task.id
                values['x_task'] = task.id

            self.env['account.analytic.line'].sudo().create(timesheetData)


    #Send mails to other assignees
    def asignee_mails(self, values, rec):
        #Get the link of the record and add it to the context
        base_url = self.get_current_url(rec)

        other_asigned = values.get('x_extra_engineers')[0][2]

        for eng in other_asigned:
            user = self.env['res.users'].sudo().browse(eng)
            self.send_email(rec, user.partner_id.email, 'Asignee', base_url)

    #Sends inmediate emails for P1s as described in the scalation matrix
    def escalation_matrix(self, values, rec):

        support, engineering, cto, ceo = self.get_destination_emails()
        account_manager = self.get_account_manager_email(rec)

        #Get the link of the record and add it to the context
        base_url = self.get_current_url(rec)
        ctx = dict(self._context or {})
        ctx['link'] = base_url

        #Check priority, creation date and current stage (not solved)
        #P1
        #Send email to support_manager and account_manager inmediately
        if(rec.priority == "3"):
            self.send_email(rec, account_manager, 'Account Manager', base_url)
            self.send_email(rec, support, 'Support Manager', base_url)
            now = datetime.now()
            rec.x_email_am_latest = now
            rec.x_email_support_latest = now

    #Gets destination emails from config
    def get_destination_emails(self):
        #Get notification emails
        config = self.env['p21helpdesk.helpdesk_config'].sudo().search([('id', '=', '1')], limit=1)
        support = config.support_manager_email
        engineering = config.engineering_manager_email
        cto = config.cto_email
        ceo = config.ceo_email

        return support, engineering, cto, ceo

    #Gets AM's email from the record's FK
    def get_account_manager_email(self, rec):
        #Get account manager's email using a different method
        user_records = self.env['res.users']
        user = rec.partner_id.user_id
        account_manager = user.partner_id.email

        return account_manager

    #Gets the ticket URL
    def get_current_url(self, rec):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (rec.id, rec._name)

        return base_url

    #Sends an email given a ticket, destination, destination description and link
    def send_email(self, ticket, to, who, link):
        ctx = dict(self._context or {})
        ctx['link'] = link #hyperlink
        ctx['to'] = to #email address
        ctx['who'] = who #string to use in email
        template_id = self.env.ref('p21helpdesk.p21helpdesk_mail_all').id
        template = self.env['mail.template'].sudo().browse(template_id)
        template.with_context(ctx).send_mail(ticket.id, force_send=True)

    #Gets status of customer
    @api.depends('partner_id')   
    def partner_status(self):
        status = 'Unknown'
        if self.partner_id:
            status = self.partner_id.status
        self.x_status = status

    #Priority mapping
    @api.depends('priority')   
    def p21_priority(self):
        priority = 'P4'
        if self.priority == '1':
            priority = 'P3'
        elif self.priority == '2':
            priority = 'P2'
        elif self.priority == '3':
            priority = 'P1'
        self.x_p21_priority_mapping = priority

    #Active_time calculations
    @api.depends('x_active_time_seconds', 'x_inactive_time_seconds')
    def get_active_time(self):

        #Get active time
        now = datetime.now()
        total_active_seconds = abs(now - self.create_date).total_seconds()

        #Get inactive time
        inactive_seconds = 0
        if not self.x_excluded_stage_initial_date in [None, False]:

            excluded_stages = self.get_excluded_stages()

            #Are we currently on an excluded stage?
            if self.stage_id.id in excluded_stages:
                inactive_seconds = abs(now - self.x_excluded_stage_initial_date).total_seconds()
        
        #Total time in excluded stages
        total_inactive_seconds = self.x_inactive_time_seconds + inactive_seconds

        #Get active_time and make it human readable
        total_time_seconds = total_active_seconds - total_inactive_seconds
        readable_time = timedelta(seconds=total_time_seconds)

        self.x_active_time_human_readable = str(readable_time.days) + ' days, ' + str(readable_time.seconds//3600) + ' hours, ' + str((readable_time.seconds//60)%60) + ' minutes.' 

    #Gets the SLA excluded stages, given a ticket
    def get_excluded_stages(self):
        #We need the excluded_stages ids
        excluded_stages = []
        slas = self.sla_ids
        for sla in slas:
            for excluded in sla.exclude_stage_ids:
                excluded_stages.append(excluded.id)
        
        return excluded_stages

    #Actions
    #Additional button to unassign ticket to self
    def unassign_ticket_to_self(self):
        self.ensure_one()
        self.user_id = None

    #Creates a Problem ticket linked to current ticket
    def create_problem_ticket(self):
        self.ensure_one()
        id = self.id
        name = str(id) + " Problem ticket - " 
        ticket_dict = {
            "name":name,
            "x_is_problem_ticket":True,
            "x_problem_ticket_source":self.id,
            "x_create_timesheet":False
        }
        pt = self.env['helpdesk.ticket'].sudo().create(ticket_dict)
        message = 'A new ticket(' + str(pt.id) + ') has been created, and it is linked to this source Problem Ticket'
        #raise UserError(message)
        self.message_post(body=message)


    #Sends needed notifications as per the escalation matrix requirements
    def escalation_checks(self):
        #Get tickets that aren't closed
        solved_stage = self.env['helpdesk.stage'].sudo().search([('name', '=', 'Solved')])
        open_tickets = self.env['helpdesk.ticket'].sudo().search([('stage_id', '!=', solved_stage.id)])

        for t in open_tickets:
        
            #use create_date or date_last_stage_update
            now = datetime.now()

            #The check will be performed every 5 minutes (This is configured in data/cronjobs.xml)
            #It MUST be set to 5 minutes for the logic to work properly. We avoid additional checks (email_already_sent) this way.

            #Get ticket lifetime
            diff = now - t.create_date
            diff_m = diff.total_seconds() / 60

            #Get email addresses
            support, engineering, cto, ceo = self.get_destination_emails()
            account_manager = self.get_account_manager_email(t)

            #Get link
            link = self.get_current_url(t)

            #First, we take a look at re-sends
            #####################################################################
            #Support Manager
            if t.x_email_support_latest not in [None,False]:
                diff_latest_support_mail = now - t.x_email_support_latest
                diff_latest_support_mail_m = diff_latest_support_mail.total_seconds() / 60
                #send email to Support Manager after 1h if ticket is still open
                if diff_latest_support_mail_m > 60:
                    self.send_email(t, support, 'Support Manager', link)
                    t.x_email_support_latest = now

            #Account Manager
            if t.x_email_am_latest not in [None,False]:
                diff_latest_am_mail = now - t.x_email_am_latest
                diff_latest_am_mail_m = diff_latest_am_mail.total_seconds() / 60
                #send email to Account Manager after 4h if ticket is still open
                if diff_latest_am_mail_m > 240:
                    self.send_email(t, account_manager, 'Account Manager', link)
                    t.x_email_am_latest = now

            #Engineering Manager
            if t.x_email_engineering_latest not in [None,False]:
                diff_latest_eng_mail = now - t.x_email_engineering_latest
                diff_latest_eng_mail_m = diff_latest_eng_mail.total_seconds() / 60
                #send email to Engineering Manager after 8h if ticket is still open
                if diff_latest_eng_mail_m > 480:
                    self.send_email(t, engineering, 'Engineering Manager', link)
                    t.x_email_engineering_latest = now

            #CTO
            if t.x_email_cto_latest not in [None,False]:
                diff_latest_cto_mail = now - t.x_email_cto_latest
                diff_latest_cto_mail_m = diff_latest_cto_mail.total_seconds() / 60
                #send daily email to CTO if ticket is still open
                if diff_latest_cto_mail_m > 1440:
                    self.send_email(t, cto, 'CTO', link)
                    t.x_email_cto_latest = now
            
            #CEO
            if t.x_email_ceo_latest not in [None,False]:
                diff_latest_ceo_mail = now - t.x_email_ceo_latest
                diff_latest_ceo_mail_m = diff_latest_ceo_mail.total_seconds() / 60
                #send daily email to CEO if ticket is still open
                if diff_latest_ceo_mail_m > 480:
                    self.send_email(t, ceo, 'CEO', link)
                    t.x_email_ceo_latest = now


            #First scheduled notifications
            #####################################################################

            #P1
            #Send email to engineering_manager (4h), CTO(8h), CEO(24h)
            if(t.priority == "3"):
                if diff_m > 240 and diff_m <= 245:
                    #send email to eng
                    self.send_email(t, engineering, 'Engineering Manager', link)
                    t.x_email_engineering_latest = now
                elif diff_m > 480 and diff_m <= 485:
                    #send email to CTO
                    self.send_email(t, cto, 'CTO', link)
                    t.x_email_cto_latest = now
                elif diff_m > 1440 and diff_m <= 1445:
                    #send email to CEO
                    self.send_email(t, ceo, 'CEO', link)
                    t.x_email_ceo_latest = now

            #P2
            #30m support_manager, 4h account_manager, 8h engineering_manager, 16h CTO, 48h CEO
            elif(t.priority == "2"):
                if diff_m > 30 and diff_m <= 35:
                    #send email to support
                    self.send_email(t, support, 'Support Manager', link)
                    t.x_email_support_latest = now
                elif diff_m > 240 and diff_m <= 245:
                    #send email to account manager
                    self.send_email(t, account_manager, 'Account Manager', link)
                    t.x_email_am_latest = now
                elif diff_m > 480 and diff_m <= 485:
                    #send email to engineering
                    self.send_email(t, engineering, 'Engineering Manager', link)
                    t.x_email_engineering_latest = now
                elif diff_m > 960 and diff_m <= 965:
                    #send email to CTO
                    self.send_email(t, cto, 'CTO', link)
                    t.x_email_cto_latest = now
                elif diff_m > 2880 and diff_m <= 2885:
                    #send email to CEO
                    self.send_email(t, ceo, 'CEO',link)
                    t.x_email_ceo_latest = now

            #P3
            #6h support_manager, 24h account_manager, 72h engineering manager
            elif(t.priority == "1"):
                if diff_m > 360 and diff_m <= 365:
                    #send email to support
                    self.send_email(t, support, 'Support Manager', link)
                    t.x_email_support_latest = now
                elif diff_m > 1440 and diff_m <= 1445:
                    #send email to account manager
                    self.send_email(t, account_manager, 'Account Manager', link)
                    t.x_email_am_latest = now
                elif diff_m > 4320 and diff_m <= 4325:
                    #send email to engineering
                    self.send_email(t, engineering, 'Engineering Manager', link)
                    t.x_email_engineering_latest = now

            #P4
            #24h support_manager, 48h account_manager
            elif(t.priority == "0"):
                if diff_m > 1440 and diff_m <= 1445:
                    #send email to support
                    self.send_email(t, support, 'Support Manager', link)
                    t.x_email_support_latest = now
                elif diff_m > 2880 and diff_m <= 2885:
                    #send email to account manager
                    self.send_email(t, account_manager, 'Account Manager', link)
                    t.x_email_am_latest = now