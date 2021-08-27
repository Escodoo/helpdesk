# Copyright 2021 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class ResUsers(models.Model):

    _inherit = 'res.users'

    helpdesk_target_closed = fields.Float(string='Target Tickets to Close')
    helpdesk_target_rating = fields.Float(string='Target Customer Rating')
    helpdesk_target_success = fields.Float(string='Target Success Rate')
