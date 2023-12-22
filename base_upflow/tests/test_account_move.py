from odoo.tests.common import SavepointCase

class TestAccountMove(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test partner", "email": "email@example.co"}
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "Test journal", "type": "sale", "code": "TEST"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Test product", "type": "service"}
        )
        cls.account_user_type = cls.env["account.account.type"].create(
            {"name": "Test account type", "type": "receivable", "internal_group": "asset"}
        )
        cls.account = cls.env["account.account"].create(
            {"name": "Test account", "code": "TEST", "user_type_id": cls.account_user_type.id, "reconcile": True}
        )
        cls.entry_move = cls.env["account.move"].create(
            {
                "journal_id": cls.journal.id,
                "move_type": "entry",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": cls.account.id,
                            "partner_id": cls.partner.id,
                            "name": "Test entry",
                            "debit": 0,
                            "credit": 0,
                        },
                    )
                ],
            }
        )
        cls.account_move = cls.env["account.move"].create(
            {
                "journal_id": cls.journal.id,
                "partner_id": cls.partner.id,
                "move_type": "out_invoice",
            }
        )

    def test_compute_upflow_commercial_partner_id_entry(self):
        self.assertEqual(self.entry_move.upflow_commercial_partner_id, self.partner.commercial_partner_id)

    def test_compute_upflow_commercial_partner_id_invoice(self):
        self.assertEqual(self.account_move.upflow_commercial_partner_id, self.partner.commercial_partner_id)
