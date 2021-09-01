import datetime
from dateutil import relativedelta
from odoo import api, fields, models


class HelpdeskTeam(models.Model):

    _name = 'helpdesk.ticket.team'
    _description = 'Helpdesk Ticket Team'
    _inherit = ['mail.thread', 'mail.alias.mixin']

    name = fields.Char(string='Name', required=True)
    user_ids = fields.Many2many(comodel_name='res.users', string='Members')
    active = fields.Boolean(default=True)
    category_ids = fields.Many2many(
        comodel_name='helpdesk.ticket.category',
        string='Category')
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env['res.company']._company_default_get(
            'helpdesk.ticket')
    )
    alias_id = fields.Many2one(help="The email address associated with "
                               "this channel. New emails received will "
                               "automatically create new tickets assigned "
                               "to the channel.")
    color = fields.Integer("Color Index", default=0)

    ticket_ids = fields.One2many(
        'helpdesk.ticket',
        'team_id',
        string="Tickets")

    todo_ticket_ids = fields.One2many(
        'helpdesk.ticket',
        'team_id',
        string="Todo tickets", domain=[("closed", '=', False)])

    todo_ticket_count = fields.Integer(
        string="Number of tickets",
        compute='_compute_todo_tickets')

    todo_ticket_count_unassigned = fields.Integer(
        string="Number of tickets unassigned",
        compute='_compute_todo_tickets')

    todo_ticket_count_unattended = fields.Integer(
        string="Number of tickets unattended",
        compute='_compute_todo_tickets')

    todo_ticket_count_high_priority = fields.Integer(
        string="Number of tickets in high priority",
        compute='_compute_todo_tickets')

    @api.depends('ticket_ids', 'ticket_ids.stage_id')
    def _compute_todo_tickets(self):
        ticket_model = self.env["helpdesk.ticket"]
        fetch_data = ticket_model.read_group(
            [("team_id", "in", self.ids), ("closed", "=", False)],
            ["team_id", "user_id", "unattended", "priority"],
            ["team_id", "user_id", "unattended", "priority"],
            lazy=False,
        )
        result = [
            [
                data["team_id"][0],
                data["user_id"] and data["user_id"][0],
                data["unattended"],
                data["priority"],
                data["__count"]
            ] for data in fetch_data
        ]
        for team in self:
            team.todo_ticket_count = sum([
                r[4] for r in result
                if r[0] == team.id
            ])
            team.todo_ticket_count_unassigned = sum([
                r[4] for r in result
                if r[0] == team.id and not r[1]
            ])
            team.todo_ticket_count_unattended = sum([
                r[4] for r in result
                if r[0] == team.id and r[2]
            ])
            team.todo_ticket_count_high_priority = sum([
                r[4] for r in result
                if r[0] == team.id and r[3] == "3"
            ])

    def get_alias_model_name(self, vals):
        return 'helpdesk.ticket'

    def get_alias_values(self):
        values = super(HelpdeskTeam, self).get_alias_values()
        values['alias_defaults'] = {'team_id': self.id}
        return values

    @api.model
    def retrieve_dashboard(self):
        domain = [('user_id', '=', self.env.uid)]
        group_fields = ['priority', 'create_date', 'stage_id', 'closed_date']
        #TODO: remove SLA calculations if user_uses_sla is false.
        user_uses_sla = self.user_has_groups('helpdesk_mgmt.group_helpdesk_manager') and\
            bool(self.env['helpdesk.ticket.team'].search([('use_sla', '=', True), '|', ('user_ids', 'in', self._uid), ('user_ids', '=', False)]))
        if user_uses_sla:
            group_fields.insert(1, 'priority')
        HelpdeskTicket = self.env['helpdesk.ticket']
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.closed', '=', False)], group_fields, group_fields, lazy=False)
        team = self.env['helpdesk.ticket.team'].search([], limit=1, order='id asc')
        result = {
            'helpdesk_target_closed': self.env.user.helpdesk_target_closed,
            'helpdesk_target_rating': self.env.user.helpdesk_target_rating,
            'helpdesk_target_success': self.env.user.helpdesk_target_success,
            'today': {'count': 0, 'rating': 0, 'success': 0},
            '7days': {'count': 0, 'rating': 0, 'success': 0},
            'my_all': {'count': 0, 'hours': 0, 'failed': 0},
            'my_high': {'count': 0, 'hours': 0, 'failed': 0},
            'my_urgent': {'count': 0, 'hours': 0, 'failed': 0},
            'show_demo': not bool(HelpdeskTicket.search([], limit=1)),
            'rating_enable': False,
            'success_rate_enable': user_uses_sla,
            'alias_name': team.alias_name,
            'alias_domain': team.alias_domain,
            'use_alias': team.alias_id.alias_contact
        }

        def add_to(ticket, key="my_all"):
            result[key]['count'] += ticket['__count']
            # result[key]['hours'] += ticket['closed_date']
            result[key]['hours'] += 1
            if ticket.get('priority'):
                result[key]['failed'] += ticket['__count']

        for ticket in tickets:
            add_to(ticket, 'my_all')
            if ticket['priority'] == '2':
                add_to(ticket, 'my_high')
            if ticket['priority'] == '3':
                add_to(ticket, 'my_urgent')

        dt = fields.Date.today()
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.closed', '=', True), ('closed_date', '>=', dt)], group_fields, group_fields, lazy=False)
        for ticket in tickets:
            result['today']['count'] += ticket['__count']
            if not ticket.get('priority'):
                result['today']['success'] += ticket['__count']

        dt = fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6)))
        tickets = HelpdeskTicket.read_group(domain + [('stage_id.closed', '=', True), ('closed_date', '>=', dt)], group_fields, group_fields, lazy=False)
        for ticket in tickets:
            result['7days']['count'] += ticket['__count']
            if not ticket.get('priority'):
                result['7days']['success'] += ticket['__count']

        result['today']['success'] = round((result['today']['success'] * 100) / (result['today']['count'] or 1), 2)
        result['7days']['success'] = round((result['7days']['success'] * 100) / (result['7days']['count'] or 1), 2)
        result['my_all']['hours'] = round(result['my_all']['hours'] / (result['my_all']['count'] or 1), 2)
        result['my_high']['hours'] = round(result['my_high']['hours'] / (result['my_high']['count'] or 1), 2)
        result['my_urgent']['hours'] = round(result['my_urgent']['hours'] / (result['my_urgent']['count'] or 1), 2)

        # if self.env['helpdesk.ticket.team'].search([('use_rating', '=', True), '|', ('user_ids', 'in', self._uid), ('user_ids', '=', False)]):
        #     result['rating_enable'] = True
        #     # rating of today
        #     domain = [('user_id', '=', self.env.uid)]
        #     dt = fields.Date.today()
        #     tickets = self.env['helpdesk.ticket'].search(domain + [('stage_id.closed', '=', True), ('closed_date', '>=', dt)])
        #     activity = tickets.rating_get_grades()
        #     total_rating = self.compute_activity_avg(activity)
        #     total_activity_values = sum(activity.values())
        #     team_satisfaction = round((total_rating / total_activity_values if total_activity_values else 0), 2)
        #     if team_satisfaction:
        #         result['today']['rating'] = team_satisfaction
        #
        #     # rating of last 7 days (6 days + today)
        #     dt = fields.Datetime.to_string((datetime.date.today() - relativedelta.relativedelta(days=6)))
        #     tickets = self.env['helpdesk.ticket'].search(domain + [('stage_id.closed', '=', True), ('closed_date', '>=', dt)])
        #     activity = tickets.rating_get_grades()
        #     total_rating = self.compute_activity_avg(activity)
        #     total_activity_values = sum(activity.values())
        #     team_satisfaction_7days = round((total_rating / total_activity_values if total_activity_values else 0), 2)
        #     if team_satisfaction_7days:
        #         result['7days']['rating'] = team_satisfaction_7days
        return result
