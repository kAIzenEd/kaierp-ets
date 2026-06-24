from odoo import models, fields, api, _


class SchoolTakeAttendanceWizard(models.TransientModel):
    """Pick a date, then open an editable attendance sheet (real ``school.attendance`` rows)."""
    _name = 'school.take.attendance.wizard'
    _description = 'Take Attendance — Choose Date'

    class_id = fields.Many2one('school.class', string='Class', required=True, ondelete='cascade')
    date = fields.Date(string='Session Date', required=True, default=fields.Date.context_today)


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not res.get('class_id'):
            res['class_id'] = self.env.context.get('default_class_id')

        return res

    def action_open_attendance_sheet(self):
        self.ensure_one()
        return self.class_id._action_open_attendance_list(self.date)

