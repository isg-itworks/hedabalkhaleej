
from odoo import models, fields, api,_
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class IsgExpenseUpdates(models.Model):
    _inherit = 'hr.expense'
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', states={'post': [('readonly', True)],'approved': [('required', True)], 'done': [('readonly', True)]}, oldname='analytic_account')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('reported', 'Submitted'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('done', 'Paid'),
        ('refused', 'Refused')
    ], compute='_compute_state', string='Status', copy=False, index=True, readonly=True, store=True,
        help="Status of the expense.")
    @api.model
    def _get_employee_id_domain(self):
        res = [('id', '=', 0)]  # Nothing accepted by domain, by default
        if self.user_has_groups('hr_expense.group_hr_expense_manager') or self.user_has_groups(
                'account.group_account_user'):
            res = []  # Then, domain accepts everything
        elif self.user_has_groups('hr_expense.group_hr_expense_user') and self.env.user.employee_ids:
            user = self.env.user
            employee = user.employee_ids[0]
            res = [
                '|', '|', '|',
                ('department_id.manager_id', '=', employee.id),
                ('parent_id', '=', employee.id),
                ('id', '=', employee.id),
                ('expense_manager_id', '=', user.id),
            ]
        elif self.env.user.employee_ids:
            employee = self.env.user.employee_ids[0]
            res = [('id', '=', employee.id)]
        return []

    @api.depends('sheet_id', 'sheet_id.account_move_id', 'sheet_id.state')
    def _compute_state(self):
        for expense in self:
            if not expense.sheet_id or expense.sheet_id.state == 'draft':
                expense.state = "draft"
            elif expense.sheet_id.state == "cancel":
                expense.state = "refused"
            elif expense.sheet_id.state == "pending":
                expense.state = "pending"
            elif expense.sheet_id.state == "approve" or expense.sheet_id.state == "post":
                expense.state = "approved"
            elif not expense.sheet_id.account_move_id:
                expense.state = "reported"
            else:
                expense.state = "done"


class IsgExpenseUpdatesSheet(models.Model):
    _inherit = 'hr.expense.sheet'
    department_id = fields.Many2one('hr.department',store=True, string='Department',compute='_onchange_employee_id', states={'post': [('readonly', True)], 'done': [('readonly', True)]})
    user_id = fields.Many2one('res.users', 'Manager',store=True,  readonly=True,compute='_onchange_employee_id', copy=False, states={'draft': [('readonly', False)]}, track_visibility='onchange', oldname='responsible_id')
    expense_line_ids = fields.One2many('hr.expense', 'sheet_id', string='Expense Lines', states={'approve': [('readonly', False)], 'done': [('readonly', True)], 'post': [('readonly', True)]}, copy=False)
    can_approve = fields.Boolean(compute='compute_can_approve')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('pending', 'Pending'),
        ('approve', 'Approved'),
        ('post', 'Posted'),
        ('done', 'Paid'),
        ('cancel', 'Refused')
    ], string='Status', index=True, readonly=True, track_visibility='onchange', copy=False, default='draft',
        required=True, help='Expense Report State')

    def compute_can_approve(self):
        for record in self:
            if record.state=='submit' and (record.env.user == record.user_id or self.user_has_groups('hr_expense.group_hr_expense_user')) :
                record.can_approve = True
            else :
                record.can_approve= False

    @api.multi
    def confirm_expense_sheets(self):
        self.write({'state': 'pending'})
        # self.activity_update()

    @api.multi
    def action_sheet_move_create(self):
        if any(sheet.state != 'approve' for sheet in self):
            raise UserError(_("You can only generate accounting entry for approved expense(s)."))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(_("Expenses must have an expense journal specified to generate accounting entries."))
        if any(not sheet.analytic_account_id for sheet in self.expense_line_ids):
            raise UserError(_("Expenses must have an analytic account to generate accounting entries."))
        expense_line_ids = self.mapped('expense_line_ids')\
            .filtered(lambda r: not float_is_zero(r.total_amount, precision_rounding=(r.currency_id or self.env.user.company_id.currency_id).rounding))
        res = expense_line_ids.sudo().action_move_create()

        if not self.accounting_date:
            self.accounting_date = self.account_move_id.date

        if self.payment_mode == 'own_account' and expense_line_ids:
            self.write({'state': 'post'})
        else:
            self.write({'state': 'done'})
        self.activity_update()
        return res

    @api.multi
    def approve_expense_sheets(self):
        self.write({'state': 'approve'})
        self.activity_update()

    @api.onchange('employee_id')
    @api.depends('employee_id')
    def _onchange_employee_id(self):
        self.address_id = self.employee_id.sudo().address_home_id
        self.department_id = self.employee_id.department_id
        self.user_id = self.employee_id.parent_id.user_id or self.employee_id.department_id.manager_id.user_id or self.employee_id.expense_manager_id
