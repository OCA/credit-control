# Copyright 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# Copyright 2017 David Vidal <david.vidal@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import exceptions
from odoo.tests import TransactionCase


class TestStockFinancialRisk(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestStockFinancialRisk, cls).setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Partner test", "customer_rank": 1}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Test product", "type": "product"}
        )
        cls.location = cls.env["stock.location"].create(
            {"name": "Test location", "usage": "internal"}
        )
        cls.location_customers = cls.env["stock.location"].create(
            {"name": "Test location customers", "usage": "customer"}
        )
        cls.sequence = cls.env["ir.sequence"].create(
            {
                "name": "test seq",
                "implementation": "standard",
                "padding": 1,
                "number_increment": 1,
            }
        )
        cls.stock_picking_type = cls.env["stock.picking.type"].create(
            {
                "name": "Test picking type",
                "code": "outgoing",
                "sequence_id": cls.sequence.id,
                "sequence_code": "test",
            }
        )
        cls.quant = cls.env["stock.quant"].create(
            {
                "quantity": 100,
                "location_id": cls.location.id,
                "product_id": cls.product.id,
            }
        )
        cls.picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.stock_picking_type.id,
                "location_id": cls.location.id,
                "location_dest_id": cls.location_customers.id,
                "partner_id": cls.partner.id,
            }
        )
        cls.move = cls.env["stock.move"].create(
            {
                "name": "/",
                "picking_id": cls.picking.id,
                "product_uom_qty": 10,
                "product_uom": cls.product.uom_id.id,
                "location_id": cls.location.id,
                "location_dest_id": cls.location_customers.id,
                "product_id": cls.product.id,
            }
        )
        cls.env.user.lang = "en_US"

    def test_stock_move_ok(self):
        self.move._action_done()

    def test_stock_move_error(self):
        self.partner.risk_exception = True
        self.move.partner_id = self.partner
        with self.assertRaises(exceptions.UserError):
            self.move._action_done()

    def test_stock_picking_ok(self):
        self.picking.action_assign()
        self.picking.action_confirm()

    def test_stock_picking_error(self):
        self.partner.risk_exception = True
        res = self.picking.action_assign()
        self.assertEqual(res["name"], "Partner risk exceeded")
        res = self.picking.action_confirm()
        self.assertEqual(res["name"], "Partner risk exceeded")

    def test_button_validate_ok(self):
        self.picking.action_assign()
        self.picking.move_line_ids[:1].qty_done = 5
        self.picking.button_validate()

    def test_button_validate_error(self):
        self.picking.action_assign()
        self.picking.move_line_ids[:1].qty_done = 5
        self.partner.risk_exception = True
        res = self.picking.button_validate()
        self.assertEqual(res["name"], "Partner risk exceeded")
