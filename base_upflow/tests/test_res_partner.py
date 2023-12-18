from uuid import uuid4

from odoo.tests import SavepointCase


class TestResPartner(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Partner",
                "email": "email@example.com",
                "phone": "123456789",
                "mobile": "123456789",
                "street": "Street",
                "street2": "Street2",
                "zip": "12345",
                "city": "City",
            }
        )

    def test_uplow_uuid_not_duplicated(self):
        self.partner.upflow_uuid = str(uuid4())
        partner2 = self.partner.copy()
        self.assertFalse(partner2.upflow_uuid)
        self.assertNotEqual(self.partner.upflow_uuid, partner2.upflow_uuid)

    def test_upflow_direct_url_not_duplicate(self):
        self.partner.upflow_direct_url = "/invoice/1234"
        partner2 = self.partner.copy()
        self.assertFalse(partner2.upflow_direct_url)
        self.assertNotEqual(self.partner.upflow_direct_url, partner2.upflow_direct_url)
