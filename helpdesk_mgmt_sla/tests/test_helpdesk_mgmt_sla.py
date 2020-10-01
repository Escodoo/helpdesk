# Copyright (C) 2020 GARCO Consulting <www.garcoconsulting.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import datetime
import logging

from odoo.addons.helpdesk_mgmt.tests import test_helpdesk_ticket

_log = logging.getLogger(__name__)


class TestHelpdeskMgmtSla(test_helpdesk_ticket.TestHelpdeskTicket):
    @classmethod
    def setUpClass(cls):
        super(TestHelpdeskMgmtSla, cls).setUpClass()
        cls.team_id = cls.env["helpdesk.ticket.team"].create(
            {"name": "Team SLA", "use_sla": True}
        )
        cls.stage_id = cls.env["helpdesk.ticket.stage"].create({"name": "Reach stage"})
        cls.sla_id = cls.env["helpdesk.sla"].create(
            {
                "name": "Generic SLA",
                "team_ids": [(6, 0, [cls.team_id.id])],
                "stage_id": cls.stage_id.id,
                "hours": 2,
            }
        )

    def generate_ticket(self):
        return self.env["helpdesk.ticket"].create(
            {
                "name": "Test Ticket 1",
                "description": "Test ticket description",
                "team_id": [(6, 0, [self.team_id.id])],
                "create_date": datetime.datetime.now() - datetime.timedelta(hours=3),
            }
        )

    def test_helpdesk_mgmt_sla(self):
        ticket = self.generate_ticket()
        ticket._compute_team_sla()
        self.assertEqual(ticket.sla_expired, True)
