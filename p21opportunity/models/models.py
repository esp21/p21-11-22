# -*- coding: utf-8 -*-

from random import gauss
from urllib import response
from odoo import models, fields, api
from datetime import date
import datetime
import logging
import requests
import json
_logger = logging.getLogger(__name__)

class Reports(models.Model):
    _name = 'p21opportunity.reports'
    
    # User mail module to write changes to chatter audit log
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'Monthly report items added to opportunities'

    # The field that will be shown if this model appears in a combo-box
    # on a Many2one field in another model
    _rec_name = 'name'
    _order = 'name ASC'

    # Can't have the same quarter on the same opportunity, more than once
    _sql_constraints = [('rpt_mth_oppor_uq', 
                        'UNIQUE (name, oppor_id)', 
                        'You cant use the same month twice')]

    # Write new values to chatter of parent
    @api.model
    def create(self, values):
        #Creates the record in the DB. We need to do this first to access the stored values
        rec = super(Reports, self).create(values)

        # We want to write to chatter of parent rec
        parentRec = rec['oppor_id']

        logMsg = 'New Forecast Report: ' + str(rec['name']) + ' - Inv Val: ' + str(rec['invoice'])  + ' - Margin: ' + str(rec['margin']) + ' - Include: ' + str(rec['include'])

        parentRec.message_post(body = logMsg, subject=None)

        return rec

    # Write changed values to parent chatter
    def write(self, values):
        # _logger.info('WRITE self: (%s) values: (%s)', self, values)

        # Old values are in 'self' - New values are in 'values'

        # Only fields that have actually changed, will be in 'values', so we have to
        # check for thier existence using:   if values.get('name') 

        isChanged = False
        changesDesc = ''

        if values.get('name') and self.name != values.get('name'):
            changesDesc += "Month changed to " + str(values.get('name')) + ". "
            isChanged = True

        if values.get('invoice') and self.invoice != values.get('invoice'):
            changesDesc += "Invoice val changed to " + str(values.get('invoice')) + ". "
            isChanged = True
            # _logger.info('invoice changed from: %s to %s', self.invoice, values.get('invoice'))

        if values.get('margin') and self.margin != values.get('margin'):
            changesDesc += "Margin val changed to " + str(values.get('margin')) + ". "
            isChanged = True
            # _logger.info('margin changed from: %s to %s', self.margin, values.get('margin'))

        if values.get('include') and self.include != values.get('include'):
            changesDesc += "Include-in-forecast changed to " + str(values.get('include')) + ". "
            isChanged = True
            # _logger.info('include changed from: %s to %s', self.include, values.get('include'))

        if isChanged:
            # We want to write to chatter of parent rec
            parentRec = self.oppor_id

            oldValues = str(self.name) + ' - Inv Val: ' + str(self.invoice)  + ' - Margin: ' + str(self.margin)  + ' - Include: ' + str(self.include)

            parentRec.message_post(body = "Edited Forecast Report - previous version: ( " + oldValues + " ) - Changes: ( " + changesDesc + ")", subject=None)

        rec = super(Reports, self).write(values)    
        return rec

    # Log delete to parent chatter
    def unlink(self):
        _logger.info('UNLINK self: (%s)', self)

        parentRec = self.oppor_id

        logMsg = 'Deleted Forecast Report: ' + str(self.name) + ' - Inv Val: ' + str(self.invoice)  + ' - Margin: ' + str(self.margin) + ' - Include: ' + str(self.include)

        parentRec.message_post(body = logMsg, subject=None)
        
        return super(Reports, self).unlink()

    # Convetionally all Odoo models have a 'name' field
    name = fields.Selection(
        string="Month",
        required=True,
        selection=lambda self: self.populate_month_list(),
        copy=False
    )    
    
    oppor_id = fields.Many2one('crm.lead',
        string='Opportunity',
        required=True,
        help='Opportunity this belongs to',
        copy=False # Copy the data in this field if the record is duplicated
    )
    
    invoice = fields.Float(
        string='Invoice Value',
        required=True,
        copy=False,
        help='Expected value of invoice(s) in this quarter'
    )    
    
    margin = fields.Float(
        string='Margin Value',
        required=True,
        copy=False,
        help='Expected value of profit margin in this quarter'
    )    
    
    include = fields.Boolean(
        string='Include in Report',
        default=True,
        copy=False,
        help='Include this item in the quarterly sales report?'        
    )

    # The next few fields are duplicated from the parent opportunity, to facilitate
    # the pivot view which can't see related fields. They are automatically updated
    # when the parent is updated.

    priority = fields.Selection(
        string='Confidence',
        selection=[('0', 'Very Low')
        , ('1', 'Low')
        , ('2', 'Medium')
        , ('3', 'High')
        ],
        help='How confident are we about winning this opportunity? (No stars for Low)',
        compute='_compute_priority',        
        store=True        
    )    

    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        compute="_compute_customer",
        store=True
    )

    user_id = fields.Many2one(
        "res.users",
        string="Salesperson",
        compute="_compute_sales_user",
        store=True
    )
    
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',        
        required=True,        
        default=lambda self: self.env.company        
    )
    
    # Populate month list dynamically
    def populate_month_list(self):
        # Show the next 24 months, and the previous six
        _now = datetime.datetime.now()
        _a_month = datetime.timedelta(weeks=+25) # Using 25 weeks instead of 6 months
        _lastmonth = _now - _a_month
        _last_month_str = str(_lastmonth.year) + '-' + str(_lastmonth.month).zfill(2)
        select_list = []        
        select_list.append((_last_month_str,_last_month_str))

        for i in range(1,30):
            # Create a time delta of x months & add it onto last month
            _some_months = datetime.timedelta(weeks=+(i*4))
            _future_month = _lastmonth + _some_months

            # Convert future month to yyyy-mm string & pad month with leading zero
            _future_month_str = str(_future_month.year) + '-' + str(_future_month.month).zfill(2)
            select_list.append((_future_month_str,_future_month_str))

        return select_list

    # Copy in the priority from the parent
    @api.depends('oppor_id.priority')
    def _compute_priority(self):
        for report in self:
            report.priority = report.oppor_id.priority
    
    # Copy in the customer from the parent
    @api.depends('oppor_id.partner_id')
    def _compute_customer(self):
        for report in self:
            report.partner_id = report.oppor_id.partner_id
    
    # Copy in the salesperson from the parent
    @api.depends('oppor_id.user_id')
    def _compute_sales_user(self):
        for report in self:
            report.user_id = report.oppor_id.user_id
    
# Add the reports field to the opportunities table
class extLead(models.Model):
    _name="crm.lead"
    _inherit="crm.lead"
    
    qtr_reports = fields.One2many(
        string='Quarterly Forecasts',
        comodel_name='p21opportunity.reports',
        inverse_name='oppor_id',
    )

    # Give 'Estimated Closing' field a better name    
    date_deadline = fields.Date(
        string='Est Close Date',
        help="Estimated date when opportunity will be won or lost",
        tracking=True
    )
    
    # Rename the priority (stars) field
    priority = fields.Selection(
        string='Confidence',
        selection=[('0', 'Very Low')
        , ('1', 'Low')
        , ('2', 'Medium')
        , ('3', 'High')
        ],
        help='How confident are we about winning this opportunity? (No stars for Very Low)',
        tracking=True
    )

    # New PO Number field
    po_number = fields.Char(
        string='PO Number',
        required=False,
        help="The customer's PO numbers",
        copy=False, # Copy the data in this field if the record is duplicated
        tracking=True
    )

    # Limit the contact field to contacts of the selected customer
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        for record in self:
            if record.partner_id:
                return {'domain': {'contact_id': [('parent_id', '=', record.partner_id.id)]}}
            else:
                return {'domain': {'contact_id': [('is_company', '=', False)]}}

    # Contact within company
    contact_id = fields.Many2one(
        "res.partner",
        string="Contact",
        copy=False, # Copy the data in this field if the record is duplicated
        tracking=True,
        domain=onchange_partner_id
    )

    # Only show companies in company field
    partner_id = fields.Many2one(
        domain="[('is_company','=', True)]"
    )

    # Active Campaign ID for corresponding 'deal'
    act_camp_deal = fields.Char(
        copy=False
    )

    # Update phone & email on opportunity, when contact changes
    @api.onchange('contact_id')
    def onchange_contact_id(self):
        for record in self:
            if record.contact_id:
                record.email_from = record.contact_id.email
                record.phone = record.contact_id.phone

    def action_set_won(self):
        # Here we are overriding an action that's called by
        # the 'Set Won' button, to trigger the Act Camp api

        # This is our auth token for the AC api
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "api-token": "fede07005fe787cca664c5d89c60cf7933fe602676d1b1de8c1838c8300917b932d4530b"
            }

        url_root = "https://agilenetworks.api-us1.com/api/3/"

        # Only consider leads sourced from Act Camp
        if self.act_camp_deal: 
            url = url_root + "deals/" + self.act_camp_deal
            wonJson = '{\"deal\": { \"status\": 1}}'
            try:
                self._send_admin_msg('Sending Act Camp won', self.name + " :: " + wonJson)
                put_response = requests.put(url, headers=headers, data=wonJson)

                if str(put_response.status_code) != '200':
                    self._send_admin_msg('Non-200 response on Act Camp win', str(put_response.status_code))

            except Exception as e:
                _logger.error(e)
                self._send_admin_msg('Error on Act Camp win', str(e))

        return super(extLead, self).action_set_won() 

    def action_set_lost(self, **additional_values):
        # Here we are overriding an action that's called by
        # the 'Set Lost' button, to trigger the Act Camp api

        # This is our auth token for the AC api
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "api-token": "fede07005fe787cca664c5d89c60cf7933fe602676d1b1de8c1838c8300917b932d4530b"
            }

        url_root = "https://agilenetworks.api-us1.com/api/3/"

        # Only consider leads sourced from Act Camp
        if self.act_camp_deal: 
            url = url_root + "deals/" + self.act_camp_deal
            lostJson = '{\"deal\": { \"status\": 2}}'
            try:
                self._send_admin_msg('Sending Act Camp lost', self.name + " :: " + lostJson)
                put_response = requests.put(url, headers=headers, data=lostJson)

                if str(put_response.status_code) != '200':
                    self._send_admin_msg('Non-200 response on Act Camp lost', str(put_response.status_code))

            except Exception as e:
                _logger.error(e)
                self._send_admin_msg('Error on Act Camp lost', str(e))

#        if additional_values:
#            return super(extLead, self).action_set_lost(additional_values) 
#        else:
        return super(extLead, self).action_set_lost() 

    def write(self, values):
        # For leads that were sourced from Active Campaign
        # update any changes to kanban stages

        # Map odoo stages to Act Camp stages
        # (name below is just for readability)
        stage_map = {
            "1":{"ActCamp": "4", "name": "new"},
            "2":{"ActCamp": "5", "name": "qualified"},
            "6":{"ActCamp": "6", "name": "sol devt"},
            "3":{"ActCamp": "7", "name": "proposal"},
            "4":{"ActCamp": "7", "name": "won"}
        }

        # This is our auth token for the AC api
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "api-token": "fede07005fe787cca664c5d89c60cf7933fe602676d1b1de8c1838c8300917b932d4530b"
            }

        url_root = "https://agilenetworks.api-us1.com/api/3/"

        # Only consider leads sourced from Act Camp
        if self.act_camp_deal: 
            url = url_root + "deals/" + self.act_camp_deal

            # Has the stage (kanban column) changed
            if 'stage_id' in values:
                ActCampStage = stage_map[str(values['stage_id'])]['ActCamp']
                json_body = '{\"deal\": { \"stage\": \"' + ActCampStage + '\" }}'
                try:
                    self._send_admin_msg('Sending Act Camp stage change', self.name + " :: " + json_body)
                    put_response = requests.put(url, headers=headers, data=json_body)

                    if str(put_response.status_code) != '200':
                        self._send_admin_msg('Non-200 response on Act Camp stage change', str(put_response.status_code))

                except Exception as e:
                    _logger.error(e)
                    self._send_admin_msg('Error on Act Camp stage change', str(e))

                # Has the deal just been  won
                stage_id = self.env['crm.stage'].browse(values['stage_id'])
                
                if stage_id.is_won:
                    wonJson = '{\"deal\": { \"status\": 1}}'
                    try:
                        self._send_admin_msg('Sending Act Camp won', self.name + " :: " + wonJson)
                        put_response = requests.put(url, headers=headers, data=wonJson)

                        if str(put_response.status_code) != '200':
                            self._send_admin_msg('Non-200 response on Act Camp win', str(put_response.status_code))

                    except Exception as e:
                        _logger.error(e)
                        self._send_admin_msg('Error on Act Camp win', str(e))

        return super(extLead, self).write(values) 

    @api.model
    def _send_admin_msg(self, the_heading, the_message):
        # Sends a log message for the system admin, to the admin_log channel
        # NB For this to work, the administrator needs to follow that channel
        try:
            channel_obj = self.env['mail.channel']
            channel_id = channel_obj.sudo().search([('name', 'like', 'admin_log')])

            channel_id.sudo().message_post(
                subject= None,
                body= the_heading + ' :: ' + the_message,
                message_type='comment',
                subtype_id = self.env.ref('mail.mt_comment').id
            )
        except Exception as e:
            _logger.error(e)

    # Import Agile Active Campaign 'deals'
    @api.model
    def _import_agile_ac_deals(self):
        
        # TODO: 
        #       Change user_map below to easily editable data
        #         so new users can be added easily
        #
        #       Code to change stages & set deal won in AC

        self._send_admin_msg('Starting Active Camp import','starting')
        
        # We only want to look for opportunities that are Agile's
        agile_company_id = "8"; 

        # Map AC user IDs to Odoo user IDs
        # Outer numerical key is the AC id
        # 'name' field is just for readability here
        user_map = {
            "1":{"odoo": 24, "name": "deirdre"},
            "2":{"odoo": 81, "name": "dgoode"},
            "3":{"odoo": 11, "name": "emannion"},
            "4":{"odoo": 69, "name": "klarkin"},
            "5":{"odoo": 80, "name": "mkinsella"},
            "6":{"odoo": 79, "name": "sreynolds"},
            "7":{"odoo": 84, "name": "snolan"},
            "8":{"odoo": 2, "name": "esheehan"}
        }

        # Similarly map kanban stages
        stage_map = {
            "4":{"odoo": 1, "name": "new"},
            "5":{"odoo": 2, "name": "qualified"},
            "6":{"odoo": 6, "name": "sol devt"},
            "7":{"odoo": 3, "name": "proposal"},
            "8":{"odoo": 3, "name": "negotiate"},
            "9":{"odoo": 3, "name": "await signoff"}
        }

        # This is our auth token for the AC api
        headers = {
            "Accept": "application/json",
            "api-token": "fede07005fe787cca664c5d89c60cf7933fe602676d1b1de8c1838c8300917b932d4530b"
            }

        url_root = "https://agilenetworks.api-us1.com/api/3/"

        # Active Campaign sends stuff in pages of 100 items
        # so we need to track if there's more pages
        loop_counter = 0        
        import_counter = 0
        page_counter = 0
        another_page = True

        while another_page:

            # Page offset is zero-based
            page_offset = page_counter * 100
            url = url_root + "deals?limit=100&offset=" + str(page_offset)

            # Get the list of deals
            try:
                # NB may need to change this later to use offset to get next page of 100
                jsonData = json.loads(requests.get(url, headers=headers).text)

            except Exception as e:
                _logger.error(e)
                self._send_admin_msg('Error on Act Camp api - list deals', str(e))
                return

            
            for deal in jsonData['deals']:
                loop_counter+=1
                try:
                    # Only consider deals that are not yet won or lost
                    if int(deal['status']) > 0:
                        continue

                    salesperson_id = user_map[deal['owner']]['odoo']
                    kanban_id = stage_map[deal['stage']]['odoo']

                    # does the deal exist already in Odoo?

                    # Flush all Odoo's data cache to the DB first
                    self.flush()

                    sql_query = """SELECT COUNT(id) AS thecount
                                FROM crm_lead WHERE 
                                act_camp_deal = '""" + deal['id'] + """'
                                AND company_id = """ + agile_company_id

                    self.env.cr.execute(sql_query)
                    sql_result = self.env.cr.dictfetchone()

                    # Skip this one if it's already in Odoo
                    if sql_result['thecount'] > 0:
                        continue

                    import_counter+=1

                    odoo_cust_id = "0"
                    odoo_contact_id = "0"

                    # If there's a customer account on the deal, 
                    # check if we have it already in Odoo
                    if deal['account'] is not None:
                        # Retrieve the customer account from AC
                        url = url_root + "deals/" + deal['id'] + "/account"

                        accountData = json.loads(requests.get(url, headers=headers).text)
                        accountName = accountData['account']['name']
                        
                        sql_query = """SELECT id FROM res_partner
                                    WHERE is_company = true
                                    AND name = '""" + accountName + """'
                                    AND company_id = """ + agile_company_id
                        
                        self.env.cr.execute(sql_query)
                        sql_result = self.env.cr.dictfetchone()

                        if sql_result:
                            # Account exists, we'll need the id later
                            odoo_cust_id = sql_result['id']
                        else:
                            # Create a new account in Odoo
                            new_acct = {
                                'name': accountName,
                                'company_id': int(agile_company_id),
                                'type': 'contact',
                                'is_company': True,
                                'status': 'potential',
                                'last_activity_source': 'Contact created',
                                'last_activity': date.today(),
                                'user_id': salesperson_id,
                                'street': None,
                                'street2': None,
                                'zip': None,
                                'city': None,
                                'state_id' : None,
                                'country_id' : 101
                            }

                            # Fill in the address fileds with blanks to stop Odoo
                            # putting in rubbish addresses

                            new_rec = self.env['res.partner'].sudo().create(new_acct)                        

                            odoo_cust_id = str(new_rec['id'])

                            self._send_admin_msg('Active Camp cust created', accountName)

                    # Init the email & phone fields
                    accountEmail = ''
                    accountPhone = ''

                    # If there's a customer contact on the deal, 
                    # check if we have it already in Odoo
                    if deal['contact'] is not None:
                        # Retrieve the contact from AC
                        url = url_root + "deals/" + deal['id'] + "/contact"

                        contactData = json.loads(requests.get(url, headers=headers).text)
                        accountEmail = contactData['contact']['email']
                        accountPhone = contactData['contact']['phone']
                        full_name = contactData['contact']['firstName'] + " " + contactData['contact']['lastName']
                        
                        # Make sure email address is populated
                        if "@" in accountEmail:
                            sql_query = """SELECT id, email, phone FROM res_partner
                                        WHERE is_company = false
                                        AND email = '""" + accountEmail + """'
                                        AND company_id = """ + agile_company_id
                        
                        else:
                            # No email address so search on name (should be rare)                    

                            sql_query = """SELECT id, email, phone FROM res_partner
                                        WHERE is_company = false
                                        AND name = '""" + full_name + """'
                                        AND company_id = """ + agile_company_id

                        self.env.cr.execute(sql_query)
                        sql_result = self.env.cr.dictfetchone()

                        if sql_result:
                            # Account exists, we'll need the id etc later
                            odoo_contact_id = sql_result['id']
                            accountEmail = sql_result['email']
                            accountPhone = sql_result['phone']
                        else:
                            # Create a new contact in Odoo
                            new_acct = {
                                'name': full_name,
                                'company_id': int(agile_company_id),
                                'email': accountEmail,
                                'phone': accountPhone,
                                'parent_id': int(odoo_cust_id),
                                'type': 'contact',
                                'is_company': False,
                                'status': 'potential',
                                'last_activity_source': 'Contact created',
                                'last_activity': date.today(),
                                'user_id': salesperson_id
                            }

                            new_rec = self.env['res.partner'].sudo().create(new_acct)
                            odoo_contact_id = str(new_rec['id'])
                    
                    # Create the opportunity
                                
                    new_opp = {
                        'name': deal['title'],
                        'user_id': salesperson_id,
                        'company_id': int(agile_company_id),
                        'type': 'opportunity',
                        'priority': 0,
                        'team_id': 1,
                        'stage_id' : kanban_id,
                        'expected_revenue': int(deal['value']) / 100,
                        'won_status': 'pending',
                        'description': deal['description'],
                        'act_camp_deal': deal['id'],
                        'phone' : accountPhone,
                        'email_from' : accountEmail
                    }
                
                    if odoo_contact_id != "0":
                        new_opp['contact_id'] = int(odoo_contact_id)

                    if odoo_cust_id != "0":
                        new_opp['partner_id'] = int(odoo_cust_id)

                    new_rec = self.env['crm.lead'].sudo().create(new_opp)

                    self._send_admin_msg('Active Camp deal imported', deal['title'])

                except Exception as e:
                    _logger.error(e)
                    self._send_admin_msg('Error on one Act Camp deal', str(e))

            if (loop_counter > 99):
                # There's another page
                loop_counter = 0
                page_counter += 1
                another_page = True

            else:
                another_page = False

        self._send_admin_msg('Finished Active Camp import', 'Imported: ' + str(import_counter))
