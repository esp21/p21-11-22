# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class EngineerSlotEdit(models.TransientModel):
    _name = 'p21planning.slot.engineer.edit'
    _description = 'Engineer Edit'

    change_reason = fields.Char(
        string = 'Reason for Change',
        required=True
    )
    
    new_start_time = fields.Datetime(
        string = 'New Start Time',
        required=True
    )

    new_end_time = fields.Datetime(
        string = 'New End Time',
        required=True
    )

    def button_save_edit(self):
        if self.env.context.get('active_model') == 'planning.slot':
            
            # Before saving, check that current user is the engineer assigned to the slot
            slotID = self.env.context.get('active_id')
            slotObj = self.env['planning.slot'].browse(slotID)
            oldStartTime = slotObj.start_datetime
            oldEndTime = slotObj.end_datetime
            # _logger.info('slot user: %s - current user: %s', slotObj.user_id.id, self.env.user.id)
            if slotObj.user_id.id != self.env.user.id:
                raise ValidationError('This change can only be made by the person who is scheduled to do this work item!')

            for wizData in self:
                dataToWrite = {
                    'start_datetime': wizData.new_start_time, 
                    'end_datetime': wizData.new_end_time
                    }

                slotObj.sudo().update(dataToWrite)

                # Write a log message to the project's chatter
                if slotObj.project_id:
                    
                    # There might not be a task
                    taskPart = ''
                    if slotObj.task_id:
                        taskPart = 'task "' + str(slotObj.task_id.name or '') + '" in '

                    logMsg = 'For ' + taskPart + 'this project, a planned slot has been changed by ' \
                        + str(slotObj.user_id.name or '') + '. The start time changed from ' \
                        + str(oldStartTime or '') + ' to ' + str(wizData.new_start_time or '') \
                        + '. The end time changed from ' \
                        + str(oldEndTime or '') + ' to ' + str(wizData.new_end_time or '') + '. ' \
                        + 'The reason given was: ' + str(wizData.change_reason or '')

                    slotObj.project_id.sudo().message_post(body = logMsg, subject = None)
                    # _logger.info(logMsg)
        else:
            raise UserError('Technical problem: Called from wrong model. Expected planning.slot')
        

class EngineerSlotDelete(models.TransientModel):
    _name = 'p21planning.slot.engineer.delete'
    _description = 'Engineer Delete'

    change_reason = fields.Char(
        string = 'Reason for Deleting',
        required=True
    )
    
    def button_delete(self):
        if self.env.context.get('active_model') == 'planning.slot':
            
            # Gather the details of the record, so we can log a note about them
            slotID = self.env.context.get('active_id')
            slotObj = self.env['planning.slot'].browse(slotID)
            projectObj = self.env['project.project'].browse(slotObj.project_id.id)
            oldStartTime = str(slotObj.start_datetime or '')
            oldEndTime = str(slotObj.end_datetime or '')
            slotUser = str(slotObj.user_id.name or '')
            slotTask = str(slotObj.task_id.name or '')

            # _logger.info('slot user: %s - current user: %s', slotObj.user_id.id, self.env.user.id)
            # Before saving, check that current user is the engineer assigned to the slot
            if slotObj.user_id.id != self.env.user.id:
                raise ValidationError('This change can only be made by the person who is scheduled to do this work item!')

            for wizData in self:

                # Delete the slot
                slotObj.sudo().unlink()

                # Write a log message to the project's chatter
                if projectObj:
                    
                    # There might not be a task
                    taskPart = ''
                    if len(slotTask) > 0:
                        taskPart = 'task "' + slotTask + '" in '

                    logMsg = 'For ' + taskPart + 'this project, a planned slot has been deleted by ' \
                        + slotUser + '. The start time was ' \
                        + oldStartTime \
                        + ', and the end time was ' \
                        + oldEndTime + '. ' \
                        + 'The reason given was: ' + str(wizData.change_reason or '')

                    projectObj.sudo().message_post(body = logMsg, subject = None)
                    # _logger.info(logMsg)
        else:
            raise UserError('Technical problem: Called from wrong model. Expected planning.slot')
        

class EngineerSlotCreate(models.TransientModel):
    _name = 'p21planning.slot.engineer.create'
    _description = 'Engineer Create'

    create_reason = fields.Char(
        string = 'Reason for Creating',
        required=True,
        help='Why are you creating this work slot?'
    )
    
    start_time = fields.Datetime(
        string = 'Start Time',
        required=True
    )

    end_time = fields.Datetime(
        string = 'End Time',
        required=True
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True
    )

    task_id = fields.Many2one(
        'project.task',
        string='Task'        
    )

    def button_create(self):
        
        # Get employee_id for user
        employeeObj = self.env['hr.employee'].sudo().search([('user_id','=', self.env.user.id)])
        try:
            employeeID = employeeObj[0].id
        except:
            raise ValidationError("You can't create a planning slot, because you have no Employee record on Odoo.")
        
        # We will be calling the create method on this slot object
        slotObj = self.env['planning.slot']
        
        for wizData in self:
            
            dataToWrite = {
                'user_id': self.env.user.id,
                'employee_id': employeeID,
                'company_id': self.env.company.id,
                'start_datetime': wizData.start_time,
                'end_datetime': wizData.end_time,
                'project_id': wizData.project_id.id,
                'task_id': wizData.task_id.id,
                'was_copied': False,
                'is_published': True,
                'publication_warning': False,
                'template_reset': False
            }

            slotObj.sudo().create(dataToWrite)

            # Write details to project log
            # There might not be a task
            taskPart = ''
            slotTask = str(wizData.task_id.name or '')
            if len(slotTask) > 0:
                taskPart = 'task "' + slotTask + '" in '

            logMsg = 'For ' + taskPart + 'this project, a planned slot has been created by ' \
                + str(self.env.user.name or '') + '. The start time is ' \
                + str(wizData.start_time) \
                + ', and the end time is ' \
                + str(wizData.end_time) + '. ' \
                + 'The reason given was: ' + str(wizData.create_reason or '')

            projectObj = self.env['project.project'].browse(wizData.project_id.id)
            projectObj.sudo().message_post(body = logMsg, subject = None)
            # _logger.info(logMsg)