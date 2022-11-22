# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import dateutil.relativedelta
import logging

_logger = logging.getLogger(__name__)

#res.partner inheritance as we need to add some custom fields
class cr_partner(models.Model):
    _inherit = 'res.partner'
    
    group = fields.Many2one('p21_change_request.custom_contact_group', string="Group", track_visibility="onchange")
    last_activity = fields.Date(string='Last activity', default=datetime.today())
    status = fields.Selection([('potential','Potential'),('customer','Customer'),('repeat','Repeat customer')], string='Status', default='potential')
    last_activity_source = fields.Char(
        string='Last Activity Source',
        help='Origin of the last account activity', 
        default="Contact created"
    )
    no_marketing = fields.Boolean(string="No Marketing")

    def write(self, values):
        if values:
            values['last_activity'] = datetime.today()
            #values['last_activity_source'] = "Contact updated"
        
        rec = super(cr_partner, self).write(values)
        return rec

    def cron_notifications(self):
        cust_obj = self.env['res.partner']
        #Calculate previous 3 months date
        d = datetime.today()
        inactivity_date = d - dateutil.relativedelta.relativedelta(days=2)
        _logger.info(inactivity_date)

        custs = cust_obj.search(['&',('last_activity','<',inactivity_date),('is_company','=','True')])
        #custs = cust_obj.search([('last_activity','<',inactivity_date),])
        _logger.info(custs.ids)

        for customer in custs:

            #Get the link of the record and add it to the context
            ctx = dict(self._context or {})
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (customer.id, customer._name)

            #Pick name, last activity date and link
            # mail = 'alberto.fausto@plannet21.ie'
            mail = ''            
            ctx['to'] = mail
            ctx['link'] = base_url
            ctx['last_act'] = customer.last_activity 
            ctx['last_act_source'] = customer.last_activity_source 

            template_id = self.env.ref('p21contact.inactive_account_template').id
            template = self.env['mail.template'].browse(template_id)
            template.with_context(ctx).send_mail(customer.id, force_send=True)
            _logger.info("Inactive accounts report sent to {}".format(mail))

#Contact group class
class custom_contact_group(models.Model):
    _name = 'p21_change_request.custom_contact_group'
    _description = 'Contacts grouping'

    name = fields.Char(string="Group name", required=True, track_visibility='onchange')
    group_id = fields.Integer(string="Group ID", required=True, track_visibility="onchange")
