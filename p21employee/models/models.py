# -*- coding: utf-8 -*-

from email.policy import default
from odoo import models, fields, api
import logging
import requests
import json
_logger = logging.getLogger(__name__)

class extSlot(models.Model):
    _name="hr.employee"
    _inherit="hr.employee"

    # This is intended to for one-time use only
    # to populate the webex_id field for existing employees
    def _batch_webex_id(self):
        for rec in self:
            companyDomain = ''
            if rec.company_id.id == 1:
                companyDomain = "@plannet21.ie"
            elif rec.company_id.id == 8:
                companyDomain = "@agilenetworks.ie"
            
            # First names are concatenated, then a dot before surname
            userName = ''
            listNameBits = rec.name.split(" ")
            i = 0
            while i < len(listNameBits):
                if i == (len(listNameBits) - 1):
                    userName += '.' + listNameBits[i].lower()
                else:
                    userName += listNameBits[i].lower()

                i+=1

            rec.webex_id = userName + companyDomain

    @api.model
    def create(self, values):
        if 'webex_id' not in values:
            # Set default value of webex_id
            companyDomain = ''
            if values['company_id'] == 1:
                companyDomain = "@plannet21.ie"
            elif values['company_id'] == 8:
                companyDomain = "@agilenetworks.ie"
            
            # First names are concatenated, then a dot before surname
            userName = ''
            listNameBits = values['name'].split(" ")
            i = 0
            while i < len(listNameBits):
                if i == (len(listNameBits) - 1):
                    userName += '.' + listNameBits[i].lower()
                else:
                    userName += listNameBits[i].lower()

                i+=1

            values['webex_id'] = userName + companyDomain

        return super(extSlot, self).create(values)
    
    office_name = fields.Selection(
        string='Office',
        selection=[('Dublin', 'Dublin')
        , ('Cork', 'Cork')
        , ('Galway', 'Galway')
        , ('France', 'France')
        ],
        help='Which office is employee attached to?'
    )

    seniority = fields.Selection(
        string='Seniority',
        selection=[('1', '1')
        , ('2', '2')
        , ('3', '3')
        ],
        help='How senior is this employee?'
    )

    start_date = fields.Date(
        string='Started',     
        help='The date the employee started with us'
    )    

    ms_proj_eng_code = fields.Char(
        string = 'MS Proj Eng Code',
        help = "Code that identifies the engineer in MS Project"
    )    

    webex_id = fields.Char(
        string = 'Webex ID',
        help = "Email address (ID) for this user in Webex"
    )    

    webex_role = fields.Selection(
        string='Webex Role',
        selection=[('none', 'None'),
            ('member', 'Member'),
            ('announce', 'Announcer')],
        default='member',
        help="The user's level of participation in company webex spaces."
    )

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

    @api.model
    def _del_from_webex(self):
        url_root = 'https://webexapis.com/v1/'
        bot_token = 'MWMxOGE3OGEtYzdmZS00MWU4LTk0MmMtNWYwODUxZjBjYWZlZmMwMmRhNzAtMDEz_PF84_37b07341-aae6-497a-af39-7825b03fc47e'
        bot_address = 'plannet21.odoo@webex.bot'
        room_announce = 'Y2lzY29zcGFyazovL3VzL1JPT00vYmY5MDM3MDAtMjNhYy0xMWVkLThjYmMtNDkyZDM3ZjZiODJk'

        self._send_admin_msg('Starting _del_from_webex', '')
        
        # Get the current list of members in the P21 Announcements room
        url = url_root + 'memberships?max=100&roomId=' + room_announce

        headers = {
            "Accept": "application/json",
            "content-type": "application/json",
            "Authorization": "Bearer " + bot_token
            }

        try:
            jsonData = json.loads(requests.get(url, headers=headers).text)

        except Exception as e:
            _logger.error(e)
            self._send_admin_msg('Error on Webex api - list members', str(e))
            return

        # Get the current list of active employees
        employees = self.sudo().search([])

        # Check if we need to delete any webex users from the room
        for webexUser in jsonData["items"]:
            empFound = False

            # Don't remove the bot that we use for api access
            if webexUser["personEmail"] == bot_address or webexUser["personEmail"].lower() == 'eanna.sheehan@plannet21.ie':
                continue

            for emp in employees:
                if not emp.webex_id:
                    continue

                if emp.webex_id.lower() == webexUser["personEmail"].lower() and emp.webex_role in ["member", "announce"]:
                    empFound = True

            if not empFound:
                # Remove user from webex room
                url = url_root + 'memberships/' + webexUser["id"]

                try:
                    post_response = requests.delete(url, headers=headers)

                    if post_response.status_code > 299:
                        self._send_admin_msg('Non-200 response on delete Webex user', str(post_response.status_code))
                    else:
                        self._send_admin_msg('Deleted Webex user', webexUser["personEmail"])

                except Exception as e:
                    _logger.error(e)
                    self._send_admin_msg('Error on delete Webex user', str(e))   

                self._send_admin_msg('Finished _del_from_webex', '')


    @api.model
    def _sync_to_webex(self):
        url_root = 'https://webexapis.com/v1/'
        bot_token = 'MWMxOGE3OGEtYzdmZS00MWU4LTk0MmMtNWYwODUxZjBjYWZlZmMwMmRhNzAtMDEz_PF84_37b07341-aae6-497a-af39-7825b03fc47e'
        bot_address = 'plannet21.odoo@webex.bot'
        room_announce = 'Y2lzY29zcGFyazovL3VzL1JPT00vYmY5MDM3MDAtMjNhYy0xMWVkLThjYmMtNDkyZDM3ZjZiODJk'

        self._send_admin_msg('Starting _sync_to_webex', '')
        
        # Get the current list of members in the P21 Announcements room
        url = url_root + 'memberships?max=100&roomId=' + room_announce

        headers = {
            "Accept": "application/json",
            "content-type": "application/json",
            "Authorization": "Bearer " + bot_token
            }

        try:
            jsonData = json.loads(requests.get(url, headers=headers).text)

        except Exception as e:
            _logger.error(e)
            self._send_admin_msg('Error on Webex api - list members', str(e))
            return

        # Get the current list of active employees
        employees = self.sudo().search([])

        # Step through the employees & check which are not in the webex room
        for emp in employees:
            if not emp.webex_id:
                continue
            
            if emp.webex_id.lower() == "eanna.sheehan@plannet21.ie":
                # Skip any changes to Eanna's account
                continue

            if emp.webex_id and emp.webex_role in ["member", "announce"]:
                empFound = False

                for webexUser in jsonData["items"]:
                    if emp.webex_id.lower() == webexUser["personEmail"].lower():
                        empFound = True

                        # Should they be a moderator & vice-versa
                        if emp.webex_role == "member" and webexUser["isModerator"]:
                            # Demote the user in Webex
                            webexMemberID = webexUser["id"]
                            url = url_root + 'memberships/' + webexMemberID
                            content = '{\"isModerator\": false, \"isRoomHidden\": false}'

                            try:
                                put_response = requests.put(url, headers=headers, data=content)

                                if put_response.status_code > 299 :
                                    self._send_admin_msg('Non-200 response on demote Webex user', str(put_response.status_code))
                                else:
                                    self._send_admin_msg('Demoted Webex user', emp.name)

                            except Exception as e:
                                _logger.error(e)
                                self._send_admin_msg('Error on demote Webex user', str(e))

                        elif emp.webex_role == "announce" and not webexUser["isModerator"]:
                            # Promote the user in webex
                            webexMemberID = webexUser["id"]
                            url = url_root + 'memberships/' + webexMemberID
                            content = '{\"isModerator\": true, \"isRoomHidden\": false}'

                            try:
                                put_response = requests.put(url, headers=headers, data=content)

                                if put_response.status_code > 299:
                                    self._send_admin_msg('Non-200 response on promote Webex user', str(put_response.status_code))
                                else:
                                    self._send_admin_msg('Promoted Webex user', emp.name)

                            except Exception as e:
                                _logger.error(e)
                                self._send_admin_msg('Error on promote Webex user', str(e))


                if not empFound:
                    # Add the user to Webex
                    if emp.webex_role == "announce":
                        isMod = "true"
                    else:
                        isMod = "false"

                    url = url_root + 'memberships'
                    content = '{\"isModerator\": ' + isMod + ', \"personEmail\": \"' + emp.webex_id + '\", \"roomId\": \"' + room_announce + '\" }'

                    try:
                        post_response = requests.post(url, headers=headers, data=content)

                        if post_response.status_code > 299:
                            self._send_admin_msg('Non-200 response on add Webex user', str(post_response.status_code))
                        else:
                            self._send_admin_msg('Added Webex user', emp.name)

                    except Exception as e:
                        _logger.error(e)
                        self._send_admin_msg('Error on add Webex user', str(e))

        self._send_admin_msg('Finished _sync_to_webex', '')

class extEmpPublic(models.Model):
    _name="hr.employee.public"
    _inherit="hr.employee.public"

    office_name = fields.Selection(
        string='Office',
        selection=[('Dublin', 'Dublin')
        , ('Cork', 'Cork')
        , ('Galway', 'Galway')
        , ('France', 'France')
        ],
        help='Which office is employee attached to?'
    )

    seniority = fields.Selection(
        string='Seniority',
        selection=[('1', '1')
        , ('2', '2')
        , ('3', '3')
        ],
        help='How senior is this employee?'
    )

    start_date = fields.Date(
        string='Started',     
        help='The date the employee started with us'
    )    

    ms_proj_eng_code = fields.Char(
        string = 'MS Proj Eng Code',
        help = "Code that identifies the engineer in MS Project"
    )    

    webex_id = fields.Char(
        string = 'Webex ID',
        help = "Email address (ID) for this user in Webex"
    )    

    webex_role = fields.Selection(
        string='Webex Role',
        selection=[('none', 'None'),
            ('member', 'Member'),
            ('announce', 'Announcer')],
        default='member',
        help="The user's level of participation in company webex spaces."
    )



        


