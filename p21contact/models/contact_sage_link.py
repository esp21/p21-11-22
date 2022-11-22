# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import datetime
import logging
import re
_logger = logging.getLogger(__name__)

# Add the Cust ID field to the partner table
class extPartner(models.Model):
    _name="res.partner"
    _inherit="res.partner"    

    sage_link = fields.Char(
        string='Customer ID',
        help='Customer ID for linking to Sage', 
        readonly=True,
        index=True
    )
    
    ignore_duplicates = fields.Boolean(
        string='Ignore Duplicates',
        help='Force this record to be saved, even if it might be a duplicate'
    )

    credit_ctrlr = fields.Char(
        string='Credit Ctrlr',
        help='Our credit controller'
    )

    # Default salesperson to current user
    user_id = fields.Many2one(
        default=lambda self: self.env.user,
        required=True
    )        

    # Set company to user's default company
    company_id = fields.Many2one(  
        required=True,        
        default=lambda self: self.env.company        
    )

    # Generate sage id based on first 2 chars of name + 5 digits
    @api.constrains('name')
    def _populate_sage_id(self):
        for rec in self:

            # Only change sage id if its not already populated
            if not rec.sage_link and rec.is_company:
                # we want the first 2 letters in the name, in uppercase
                _alphaPrefix = re.sub(r'[^a-zA-Z]', '', rec.name)[0:2].upper()

                if len(_alphaPrefix) > 1:
                    _intSuffix = 10001
                    _idIsGenerated = False

                    # Loop to find next ID with this prefix, that's not already in use
                    while not _idIsGenerated:
                        _proposedID = _alphaPrefix + str(_intSuffix)
                        # Search to see if this ID is in use already
                        _existingID = self.env['res.partner'].search([('sage_link','=',_proposedID)], count=True)

                        if _existingID > 0:
                            _intSuffix+= 1 # Try again with the next number
                        else:
                            rec.sage_link = _proposedID
                            _idIsGenerated = True;

    # Check for potential duplicates on name & domain name
    @api.model
    def create(self, vals):
        
        # _logger.info('create method starting')
        
        if vals.get('company_type') != 'company':
            # _logger.info('Contact is a person, not checking duplicates')
            return super(extPartner, self).create(vals) # Just save          
        
        if vals.get('ignore_duplicates') == True:
            # _logger.info('Ignore duplicates is true')
            return super(extPartner, self).create(vals) # User wants to force saving
        
        _email = vals.get('email')
        _website = vals.get("website")
        _name = vals.get("name")

        # _logger.info('email:%s   web:%s   name:%s', _email, _website, _name)

        # User must supply either email or web address
        if _email == False and _website == False:
            # _logger.info('Both website & email address are missing')
            raise UserError('Please fill-in website or email address.')

        _foundDupe = False
        _dupeList = set() # Using a set will avoid duplicates in the list

        # Check first 7 chars of name for a possible duplicate
        _namePrefix = vals.get("name")[0:7]
        _foundDupeNameCount = self.env['res.partner'].search_count([('name','=ilike',_namePrefix + '%')])
        
        if _foundDupeNameCount > 0:
            # _logger.info('# dupe names found: %s', _foundDupeNameCount)            
            _foundNameDupes = self.env['res.partner'].search([('name','=ilike',_namePrefix + '%')])

            for _foundNameDupe in _foundNameDupes:
                if _foundNameDupe.company_type == 'company':
                    _foundDupe = True
                    _dupeList.add(_foundNameDupe.name)

        # Check if email domain exists in either email or website
        if _email != False:
            _emailDomain = _email.split('@')[1]
            # _logger.info('Email domain %s', _emailDomain)

            _foundDupeEmailCount = self.env['res.partner'].search_count(['|',('email','ilike',_emailDomain ),('website','ilike',_emailDomain )])

            if _foundDupeEmailCount > 0:
                _foundEmailDupes = self.env['res.partner'].search(['|',('email','ilike',_emailDomain ),('website','ilike',_emailDomain )])

                for _foundEmailDupe in _foundEmailDupes:
                    if _foundEmailDupe.company_type == 'company':
                        _foundDupe = True
                        _dupeList.add(_foundEmailDupe.name)

        # Check if web link domain exists in either email or website
        if _website != False:
            _withoutProtocol = _website.replace('http://', '').replace('https://', '')
            _webDomain = _withoutProtocol.replace('www.', '')

            # _logger.info('Web link domain %s', _webDomain)

            _foundDupeWebCount = self.env['res.partner'].search_count(['|',('email','ilike',_webDomain ),('website','ilike',_webDomain )])

            if _foundDupeWebCount > 0:
                _foundWebDupes = self.env['res.partner'].search(['|',('email','ilike',_webDomain ),('website','ilike',_webDomain )])

                for _foundWebDupe in _foundWebDupes:
                    if _foundWebDupe.company_type == 'company':
                        _foundDupe = True
                        _dupeList.add(_foundWebDupe.name)

        if _foundDupe:
            _sortedDupes = sorted(_dupeList)
            _errorString = "THE FOLLOWING POSSIBLE DUPLICATES WERE FOUND. \n \nTick 'Ignore Duplicates' if you want to save anyway.\n"
            
            for _dupeItem in _sortedDupes:                
                _errorString += "\n" + _dupeItem

            raise UserError(_errorString)

        # If we get this far all checks passed
        return super(extPartner, self).create(vals)

