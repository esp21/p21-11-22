# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class extSlot(models.Model):
    _name="planning.slot"
    _inherit="planning.slot"

    # Should we create a timesheet line on the date of this slot?
    create_timesheet = fields.Boolean(
        default=True, 
        string = 'Populate timesheet',
        help = "Should a line be added to the engineer's timesheet, for this date?")

    # Override create, to check if we should create a timesheet line
    # Also, send mail if double-booked
    @api.model
    def create(self, values):
        if (not values.get('project_id')) and (values.get('create_timesheet')):
            raise UserError('If you want to populate the timesheet, you must select the project also.')

        timesheetOption = values.get('create_timesheet')
        if timesheetOption != False:
            # We need to lookup some values in the project
            projectObj = self.env['project.project'].sudo().browse(values.get('project_id'))
            accountID = projectObj.analytic_account_id.id
            partnerID = projectObj.partner_id

            # Get the employee's user_id
            employeeObj = self.env['hr.employee'].sudo().browse(values.get('employee_id'))
            empUserID = employeeObj.user_id.id

            timesheetData = {
            'date': values.get('start_datetime'), 
            'amount': 0,
            'unit_amount': 0,
            'product_uom_id': 6,
            'account_id': accountID,
            'user_id' : empUserID,
            'project_id': values.get('project_id'),
            'company_id': self.env.company.id,
            'currency_id': 1,
            'employee_id': values.get('employee_id'),
            'non_std_hours': 0
            }

            # Some optional fields
            if partnerID:
                timesheetData['partner_id'] = partnerID.id

            if values.get('task_id'):
                timesheetData['task_id'] = values.get('task_id')

            # _logger.info(timesheetData)
            self.env['account.analytic.line'].sudo().create(timesheetData)

        # Should we set the project status to Planned (ie this is first planning slot)
        if values.get('project_id'):
            projectObj = self.env['project.project'].sudo().browse(values.get('project_id'))

            if projectObj.new_status.name == 'Pre-Planning NO Kit' or projectObj.new_status.name == 'Pre-Planning With Kit':
                
                new_id = self.env['p21project.projectstatus'].search([('name', '=', 'Planned')], limit=1).id 
                projectObj.new_status = new_id

        # Check if we are doing double-booking warning emails
        warning_address = self.env['ir.config_parameter'].sudo().get_param('p21planning.warn_email', False)

        if warning_address:
            newStart = values.get('start_datetime')
            newEnd = values.get('end_datetime')
            newEmployee = values.get('employee_id')
            newProj = '(empty)'
            newTask = '(empty)'
            theBooker = '(unknown)'

            # Search for clashing bookings
            _domain = ['&','&',('employee_id', '=', newEmployee),
                ('start_datetime','<', newEnd), 
                ('end_datetime','>', newStart)]

            recsFound = self.sudo().search(_domain, limit=1)

            if recsFound:
                # There's a clash
                oldStart = recsFound.start_datetime
                oldEnd = recsFound.end_datetime
                oldProjName = '(empty)'
                oldTaskName = '(empty)'

                if recsFound.project_id:
                    oldProjName = recsFound.project_id.name

                if recsFound.task_id:
                    oldTaskName = recsFound.task_id.name

                if values.get('project_id'):
                    newProj = self.env['project.project'].sudo().browse(values.get('project_id')).name

                if values.get('task_id'):
                    newTask = self.env['project.task'].sudo().browse(values.get('task_id')).name

                # Get name of the person who created new booking
                thisContext = self._context
                current_uid = thisContext.get('uid')
                theBooker = self.env['res.users'].browse(current_uid).name

                # Populate mail placeholders into context
                ctx = dict(self._context or {})
                ctx['to'] = warning_address
                ctx['person'] = recsFound.employee_id.name
                ctx['newproj'] = newProj
                ctx['newtask'] = newTask
                ctx['newfrom'] = newStart
                ctx['newto'] = newEnd
                ctx['oldproj'] = oldProjName
                ctx['oldtask'] = oldTaskName
                ctx['oldfrom'] = oldStart
                ctx['oldto'] = oldEnd
                ctx['booker'] = theBooker

                # send mail
                template_id = self.env.ref('p21planning.double_book_email_template').id
                template = self.env['mail.template'].browse(template_id)
                template.with_context(ctx).send_mail(self.id, force_send=True)

        return super(extSlot, self).create(values)





