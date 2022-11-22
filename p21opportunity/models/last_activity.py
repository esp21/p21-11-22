# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

# Set customer last_activity
class extLead(models.Model):
    _inherit="crm.lead"

    @api.model
    def create(self, values): 
        rec = super(extLead, self).create(values)

        partner_vals = {}
        partner_vals['last_activity'] = datetime.today()
        partner_vals['last_activity_source'] = "Opportunity created"

        own_id = str(rec.partner_id.id)
        if not own_id == 'False':
            partner = self.env['res.partner'].search([('id','=',own_id)])
            partner.write(partner_vals)

        return rec

    def write(self, values):
        if values:
            self.partner_id.last_activity = datetime.today()
            self.partner_id.last_activity_source = "Opportunity updated"
        
        rec = super(extLead, self).write(values)
        return rec