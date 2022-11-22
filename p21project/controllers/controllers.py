# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
from datetime import datetime
from time import strftime
import email.utils

class Main(http.Controller):
    @http.route('/p21project/plan_cal', auth='none', type='http')
    def plan_cal(self, t):
        # The t param is a querystring param from the url

        nowStamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        #Last modified header (this is just a placeholder. modified later.)
        modHeader = ('x-no-mod', 'none')

        outputText = '''BEGIN:VCALENDAR
PRODID:-//PlanNet21//Odoo14//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-TIMEZONE:Europe/Dublin
BEGIN:VTIMEZONE
TZID:Europe/Dublin
X-LIC-LOCATION:Europe/Dublin
BEGIN:DAYLIGHT
TZOFFSETFROM:+0000
TZOFFSETTO:+0100
TZNAME:IST
DTSTART:19700329T010000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0100
TZOFFSETTO:+0000
TZNAME:GMT
DTSTART:19701025T020000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE'''

        users = request.env['res.users'].sudo().search([('ical_token','=',t)])
        for user in users:
            outUserName = '''
X-WR-CALNAME:''' + user.name
            outputText += outUserName

            slots = request.env['planning.slot'].sudo().search([('user_id','=',user.id)])
            for slot in slots:
                
                outStartEvent = '''
BEGIN:VEVENT
SEQUENCE:0
TRANSP:OPAQUE
DTSTART:''' + slot.start_datetime.strftime("%Y%m%dT%H%M%SZ")
                outputText += outStartEvent

                outEndEvent = '''
DTEND:''' + slot.end_datetime.strftime("%Y%m%dT%H%M%SZ")
                outputText += outEndEvent

                outNow = '''
DTSTAMP:''' + nowStamp
                outputText += outNow

                outCreated = '''
CREATED:''' + slot.create_date.strftime("%Y%m%dT%H%M%SZ")
                outputText += outCreated

                outModified = '''
LAST-MODIFIED:''' + slot.write_date.strftime("%Y%m%dT%H%M%SZ")
                outputText += outModified

                outUID = '''
UID:''' + str(slot.id) + '@itwarehouse.ie'
                outputText += outUID

                outDesc = '''
DESCRIPTION:''' + str(slot.name or '') 
                outputText += outDesc

                outSummary = '''
SUMMARY:''' + str(slot.project_id.name or '')  + ' == ' + str(slot.task_id.name or '')
                outputText += outSummary

                outStatus = 'TENTATIVE'
                if slot.is_published == True:
                    outStatus = 'CONFIRMED'

                outStat = '''
STATUS:''' + outStatus
                outputText += outStat

                outputText += '''
END:VEVENT'''

            try:
                # Calculate http header last-modified
                # by using the date of the latest modified planning slot
                modHeader = ('Last-Modified', email.utils.formatdate(
                (
                fields.Datetime.from_string(
                request.env['planning.slot'].sudo()
                .search([('user_id','=',user.id)],order='write_date desc',limit=1)
                .write_date) - datetime(1970, 1, 1)
                ).total_seconds(),usegmt=True))
            except:
                pass # No action if exception

        outputText += '''
END:VCALENDAR'''

        headMimeType = ('Content-Type','text/calendar')

        return request.make_response(outputText, headers=[modHeader,headMimeType])