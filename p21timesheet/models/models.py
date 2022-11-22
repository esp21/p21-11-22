# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class extAcctAticLine(models.Model):
    _name="account.analytic.line"
    _inherit="account.analytic.line"    

    # Validation constraint to ensure non-stand hours does not exceed hours worked
    # (nb: unit_amount is the field that stores work duration)
    _sql_constraints = [('non_std_too_high', 'CHECK(non_std_hours <= unit_amount OR unit_amount < 0)',
        'Number of non-standard hours must not exceed work duration.')]

    # Field for amount of out-of-hours
    non_std_hours = fields.Float(
        string = 'of which, Non-Std. Hrs.',
        digits = (5,2),
        default = 0,
        copy=False,
        help = "The number of non-standard hours worked in this shift."
    )

    # Check if this project requires the description field to be completed
    # But only apply rule if there's time (unit_amount) on the line
    @api.constrains('name', 'project_id', 'unit_amount')
    def _check_reqd_desc(self):
        for rec in self:
            if rec.project_id and rec.project_id.ts_desc_reqd and rec.unit_amount and rec.unit_amount > 0:
                if rec.name :
                    if len(rec.name.strip()) < 3 or rec.name.strip() == 'Timesheet Adjustment':
                        # The description (name) field is less than 3 chars
                        raise models.ValidationError('Timesheet description must be filled in for this project')
                else:
                    # The description (name) field is blank altogether
                    raise models.ValidationError('Timesheet description must be filled in for this project')

    # Check if this project blocks timesheets that would put us over the days-bought amount
    @api.constrains('project_id', 'unit_amount')
    def _check_project_block_ts(self):
        for rec in self:
            if rec.project_id and rec.project_id.prevent_overbudget and rec.project_id.percent_used > 100 :
                # Text of error message comes from project record
                raise models.ValidationError(rec.project_id.timesheet_warn_text)
