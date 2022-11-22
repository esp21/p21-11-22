# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

CATEGORY_SELECTION = [
    ('required', 'Required'),
    ('optional', 'Optional'),
    ('no', 'None')]

class extApprovalCategory(models.Model):
    _name="approval.category"
    _inherit="approval.category"    

    # New field types added for P21 change requests
    has_tech_affected = fields.Selection(CATEGORY_SELECTION, string="Tech Affected", default="no", required=True)
    has_biz_impact = fields.Selection(CATEGORY_SELECTION, string="Business Impact", default="no", required=True)
    has_implement_plan = fields.Selection(CATEGORY_SELECTION, string="Implement Plan", default="no", required=True)
    has_test_plan = fields.Selection(CATEGORY_SELECTION, string="Test Plan", default="no", required=True)
    has_rollback_plan = fields.Selection(CATEGORY_SELECTION, string="Rollback Plan", default="no", required=True)
    has_comm_plan = fields.Selection(CATEGORY_SELECTION, string="Comms Plan", default="no", required=True)
    has_implement_by = fields.Selection(CATEGORY_SELECTION, string="Implemented By", default="no", required=True)
    has_notify_list = fields.Selection(CATEGORY_SELECTION, string="Notify List", default="no", required=True)
    has_implement_date = fields.Selection(CATEGORY_SELECTION, string="Implementation Date", default="no", required=True)

# Technology area categories, has m2m with approval.request
class ApprovalTechAreas(models.Model):
    _name = 'p21approval.techarea'
    _description = 'Technology Area'

    name = fields.Char(string="Tech Area")

class extApprovalRequest(models.Model):
    _name="approval.request"
    _inherit="approval.request"    

    # New field types added for P21 change requests. These mirror the ones in the category model.
    has_tech_affected = fields.Selection(related="category_id.has_tech_affected")
    has_biz_impact = fields.Selection(related="category_id.has_biz_impact")
    has_implement_plan = fields.Selection(related="category_id.has_implement_plan")
    has_test_plan = fields.Selection(related="category_id.has_test_plan")
    has_rollback_plan = fields.Selection(related="category_id.has_rollback_plan")
    has_comm_plan = fields.Selection(related="category_id.has_comm_plan")
    has_implement_by = fields.Selection(related="category_id.has_implement_by")
    has_notify_list = fields.Selection(related="category_id.has_notify_list")
    has_implement_date = fields.Selection(related="category_id.has_implement_date")

    # Enable Odoo's archiving feature
    active = fields.Boolean('Active', default=True)

    tech_affected = fields.Many2many('p21approval.techarea', string='Tech Areas', tracking=True)

    biz_impact = fields.Selection(
        [('no_outage','No Outage'), ('outage','Outage'), ('partial', 'Partial Outage')],
        string="Business Impact", default="no_outage", tracking=True
    )

    implement_plan = fields.Text(string="Implementation Plan")
    test_plan = fields.Text(string="Test Plan")
    rollback_plan = fields.Text(string="Rollback Plan")
    comm_plan = fields.Text(string="Communication Plan")
    implement_date = fields.Date(string="Implementation Date", tracking=True)
    
    implement_by = fields.Many2one('res.users', string="Implemented By", tracking=True)

    notify_list = fields.Many2many(
        'res.users',
        string = "Notification List",
        help = 'List of people we want to notify about this request', tracking=True)

    notify_mail_sent = fields.Boolean(store=True, compute='_maybe_send_notify_mail', tracking=True)

    @api.depends('request_status')
    def _maybe_send_notify_mail(self):
        for approval in self:
            # _logger.info('_maybe_send_notify_mail - status: %s ', approval.request_status)

            if approval.request_status != 'new' and approval.notify_mail_sent == False:
                approval._send_notify_mail()
                approval.notify_mail_sent = True # flip the flag to true

            elif approval.notify_mail_sent == True:
                approval.notify_mail_sent = True # keep the flag at true (ie only send the mail once)

            else:
                approval.notify_mail_sent = False # keep the flag at false, too soon to send mail

   
    def _send_notify_mail(self):
        for approval in self:

                # Prevent mail being sent twice on the same transaction
                if self.env.context.get('MailAlreadySent'):
                    return
            
                emailTo = approval.request_owner_id.email;
                
                ccListObj = approval.mapped('notify_list.partner_id.email')
                # _logger.info('notify_ids: %s', ccListObj)

                ccFormatted = ''
                if len(ccListObj) > 0:
                    ccFormatted = ', '.join(ccListObj)

                # _logger.info('_send_notify_mail - cc: %s ', ccFormatted)

                ctx = dict(approval._context or {})
                ctx['to'] = emailTo
                ctx['cc'] = ccFormatted
                ctx['title'] = approval.name
                ctx['desc'] = approval.reason
                ctx['category'] = approval.category_id.name
                ctx['owner'] = approval.request_owner_id.name

                template_id = self.env.ref('p21approval.approve_notify_email_template').id
                template = self.env['mail.template'].browse(template_id)
                template.with_context(ctx).send_mail(approval.id, force_send=True)

                # Set context flag to prevent a duplicate mail being sent now
                self = self.with_context(MailAlreadySent=True)

    # Override create to check for overlapping start & end dates (ie duplicates)
    # if the record has start & end dates, and within the same type of request
    @api.model
    def create(self,vals):

        if 'date_start' in vals and 'date_end' in vals:

            #This one has start & end dates, so check them
            _cat = vals.get('category_id')
            _start = vals.get('date_start')
            _end = vals.get('date_end')

            # We are going to search on the basis of category name, so we can
            # include similar categories from other companies
            categoryName = self.env['approval.category'].browse(int(_cat)).name

            # We'll be seraching the custom calendar view, which has all companies in it
            objCalendar = self.env['p21approval.calendar']

            # Check start date first, but ignore cancelled & refused bookings
            _domain = ['&','&','&',('category_id.name', '=', categoryName),
                ('date_start','<=', _start), ('date_end','>', _start),
                ('request_status', 'in', ['approved','new','pending'])]

            recsFound = objCalendar.sudo().search_count(_domain)

            if recsFound > 0:
                raise UserError('Unable to save. This booking clashes with another one. Check the calendar.')

            else:
                # Start date is OK, so check the end date
                _domain = ['&','&','&',('category_id.name', '=', categoryName),
                    ('date_start','<', _end), ('date_end','>=', _end),
                    ('request_status', 'in', ['approved','new','pending'])]

                recsFound = objCalendar.sudo().search_count(_domain)

                if recsFound > 0:
                    raise UserError('Unable to save. This booking clashes with another one. Check the calendar.')

                else:
                    # Finally check if the new booking entirely eclipses an old one
                    _domain = ['&','&','&',('category_id.name', '=', categoryName),
                        ('date_start','>=', _start), ('date_end','<=', _end),
                        ('request_status', 'in', ['approved','new','pending'])]

                    recsFound = objCalendar.sudo().search_count(_domain)

                    if recsFound > 0:
                        raise UserError('Unable to save. This booking clashes with another one. Check the calendar.')

                    else:                    
                        # All OK, so save the record
                        return super(extApprovalRequest, self).create(vals) 

        else:
            # No start & end dates to check, so just do a normal save
            return super(extApprovalRequest, self).create(vals) 


# Read-only model, based on SQL view of approval.request table
# This allows us skirt around the multi-company restrictions, so the 
#  approvals calendar shows bookings from all companies
class ApprovalCalendar(models.Model):
    _name = 'p21approval.calendar'
    _auto = False # Don't create a table for this model

    name = fields.Char(string="Approval Subject", readonly=True)
    date_start = fields.Datetime(string="Date start", readonly=True)
    date_end = fields.Datetime(string="Date end", readonly=True)
    category_id = fields.Many2one('approval.category', string="Category", readonly=True)

    request_status = fields.Selection([
        ('new', 'To Submit'),
        ('pending', 'Submitted'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel'),
    ], readonly=True)

    request_owner_id = fields.Many2one('res.users', string="Request Owner", readonly=True)

    # Create the SQL view in the database
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        query = """
            CREATE OR REPLACE VIEW p21approval_calendar as (
                SELECT id, name, date_start, date_end, category_id, 
                request_status, request_owner_id 
                FROM approval_request
            )
        """

        self.env.cr.execute(query)