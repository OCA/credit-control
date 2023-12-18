from contextlib import contextmanager
from unittest import mock

from odoo.addons.base_upflow.tests.common import AccountingCommonCase
from odoo.addons.component.tests.common import SavepointComponentRegistryCase


class EDIUpflowCommonCase(SavepointComponentRegistryCase, AccountingCommonCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_env()
        cls._load_module_components(cls, "component_event")
        cls._load_module_components(cls, "edi_oca")
        cls._load_module_components(cls, "edi_account_oca")
        cls._load_module_components(cls, "edi_upflow")
        cls._setup_records()

        @contextmanager
        def _consumer_record_no_new_env(record, new_cursor=True):
            yield record

        patcher_consumer_record_same_transaction = mock.patch(
            "odoo.addons.webservice.models.webservice_backend."
            "WebserviceBackend._consumer_record_env",
            side_effect=_consumer_record_no_new_env,
        )
        cls.addClassCleanup(patcher_consumer_record_same_transaction.stop)
        patcher_consumer_record_same_transaction.start()

    @classmethod
    def _setup_context(cls):
        return dict(
            cls.env.context, tracking_disable=True, test_queue_job_no_delay=False
        )

    @classmethod
    def _setup_env(cls):
        cls.env = cls.env(context=cls._setup_context())

    @classmethod
    def _setup_records(cls):
        cls.backend = cls._get_backend()
        cls.env.company.upflow_backend_id = cls.backend
        cls.upflow_ws = cls.backend.webservice_backend_id
        cls.partner = cls.env.ref("base.res_partner_1")
        cls.partner.ref = "EDI_EXC_TEST"
        cls.partner.commercial_partner_id.vat = "FR13542107651"
        cls._setup_accounting()

    @classmethod
    def _get_backend(cls):
        return cls.env.ref("edi_upflow.upflow_edi_backend")


class EDIUpflowCommonCaseRunningJob(EDIUpflowCommonCase):
    @classmethod
    def _setup_context(cls):
        return dict(
            cls.env.context, tracking_disable=True, test_queue_job_no_delay=True
        )
