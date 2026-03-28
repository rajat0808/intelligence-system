import os
import unittest
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database.base import Base
from app.models.delivery_logs import DeliveryLog
from app.routers.whatsapp import (
    _extract_status_events,
    _persist_status_events,
    receive_webhook,
    verify_webhook,
)


class _ClientStub:
    def __init__(self, host=None):
        self.host = host


class _RequestStub:
    def __init__(self, payload=None, error=None, headers=None, client_host=None):
        self._payload = payload
        self._error = error
        self.headers = headers or {}
        self.client = _ClientStub(client_host) if client_host is not None else None

    async def json(self):
        if self._error:
            raise self._error
        return self._payload


class WhatsAppWebhookVerifyTest(unittest.TestCase):
    def setUp(self):
        self._original_verify_token = os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN")
        self._original_webhook_allowlist = os.environ.get(
            "WHATSAPP_WEBHOOK_IP_ALLOWLIST"
        )
        get_settings.cache_clear()

    def tearDown(self):
        if self._original_verify_token is None:
            os.environ.pop("WHATSAPP_WEBHOOK_VERIFY_TOKEN", None)
        else:
            os.environ["WHATSAPP_WEBHOOK_VERIFY_TOKEN"] = self._original_verify_token
        if self._original_webhook_allowlist is None:
            os.environ.pop("WHATSAPP_WEBHOOK_IP_ALLOWLIST", None)
        else:
            os.environ["WHATSAPP_WEBHOOK_IP_ALLOWLIST"] = (
                self._original_webhook_allowlist
            )
        get_settings.cache_clear()

    def test_verify_webhook_returns_challenge(self):
        os.environ["WHATSAPP_WEBHOOK_VERIFY_TOKEN"] = "verify-me"
        get_settings.cache_clear()

        response = verify_webhook(
            request=_RequestStub(),
            hub_mode="subscribe",
            hub_verify_token="verify-me",
            hub_challenge="123456",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body.decode("utf-8"), "123456")

    def test_verify_webhook_rejects_invalid_token(self):
        os.environ["WHATSAPP_WEBHOOK_VERIFY_TOKEN"] = "verify-me"
        get_settings.cache_clear()

        with self.assertRaises(HTTPException) as ctx:
            verify_webhook(
                request=_RequestStub(),
                hub_mode="subscribe",
                hub_verify_token="wrong-token",
                hub_challenge="123456",
            )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "Webhook verification failed")

    def test_verify_webhook_requires_verify_token_configuration(self):
        os.environ["WHATSAPP_WEBHOOK_VERIFY_TOKEN"] = ""
        get_settings.cache_clear()

        with self.assertRaises(HTTPException) as ctx:
            verify_webhook(
                request=_RequestStub(),
                hub_mode="subscribe",
                hub_verify_token="anything",
                hub_challenge="123456",
            )

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(
            ctx.exception.detail, "WHATSAPP_WEBHOOK_VERIFY_TOKEN is not configured"
        )

    def test_verify_webhook_rejects_ip_outside_allowlist(self):
        os.environ["WHATSAPP_WEBHOOK_VERIFY_TOKEN"] = "verify-me"
        os.environ["WHATSAPP_WEBHOOK_IP_ALLOWLIST"] = (
            "74.220.48.0/24,74.220.56.0/24"
        )
        get_settings.cache_clear()

        with self.assertRaises(HTTPException) as ctx:
            verify_webhook(
                hub_mode="subscribe",
                hub_verify_token="verify-me",
                hub_challenge="123456",
                request=_RequestStub(headers={"x-forwarded-for": "8.8.8.8"}),
            )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "Webhook source IP is not allowed")

    def test_verify_webhook_accepts_ip_in_allowlist(self):
        os.environ["WHATSAPP_WEBHOOK_VERIFY_TOKEN"] = "verify-me"
        os.environ["WHATSAPP_WEBHOOK_IP_ALLOWLIST"] = (
            "74.220.48.0/24,74.220.56.0/24"
        )
        get_settings.cache_clear()

        response = verify_webhook(
            hub_mode="subscribe",
            hub_verify_token="verify-me",
            hub_challenge="123456",
            request=_RequestStub(headers={"x-forwarded-for": "74.220.56.19"}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body.decode("utf-8"), "123456")


class WhatsAppWebhookReceiveTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._original_webhook_allowlist = os.environ.get("WHATSAPP_WEBHOOK_IP_ALLOWLIST")
        get_settings.cache_clear()

    def tearDown(self):
        if self._original_webhook_allowlist is None:
            os.environ.pop("WHATSAPP_WEBHOOK_IP_ALLOWLIST", None)
        else:
            os.environ["WHATSAPP_WEBHOOK_IP_ALLOWLIST"] = (
                self._original_webhook_allowlist
            )
        get_settings.cache_clear()

    async def test_receive_webhook_acknowledges_payload(self):
        response = await receive_webhook(
            _RequestStub(payload={"object": "whatsapp_business_account", "entry": []})
        )

        self.assertEqual(response["status"], "received")
        self.assertEqual(response["object"], "whatsapp_business_account")
        self.assertEqual(response["status_events"], 0)
        self.assertEqual(response["stored"], 0)
        self.assertEqual(response["updated"], 0)

    async def test_receive_webhook_rejects_invalid_json(self):
        with self.assertRaises(HTTPException) as ctx:
            await receive_webhook(_RequestStub(error=ValueError("invalid json")))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Invalid JSON payload")

    async def test_receive_webhook_rejects_ip_outside_allowlist(self):
        os.environ["WHATSAPP_WEBHOOK_IP_ALLOWLIST"] = "74.220.48.0/24,74.220.56.0/24"
        get_settings.cache_clear()

        with self.assertRaises(HTTPException) as ctx:
            await receive_webhook(
                _RequestStub(
                    payload={"object": "whatsapp_business_account", "entry": []},
                    headers={"x-forwarded-for": "1.1.1.1"},
                )
            )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "Webhook source IP is not allowed")

    async def test_receive_webhook_accepts_ip_in_allowlist(self):
        os.environ["WHATSAPP_WEBHOOK_IP_ALLOWLIST"] = "74.220.48.0/24,74.220.56.0/24"
        get_settings.cache_clear()

        response = await receive_webhook(
            _RequestStub(
                payload={"object": "whatsapp_business_account", "entry": []},
                headers={"x-forwarded-for": "74.220.48.77"},
            )
        )

        self.assertEqual(response["status"], "received")
        self.assertEqual(response["object"], "whatsapp_business_account")


class WhatsAppWebhookStatusPersistenceTest(unittest.TestCase):
    def test_extract_status_events(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "1015568374973326"},
                                "statuses": [
                                    {
                                        "id": "wamid.HBgMOTk5",
                                        "status": "delivered",
                                        "timestamp": "1700000000",
                                        "recipient_id": "917388863677",
                                    }
                                ],
                            }
                        }
                    ]
                }
            ],
        }

        events = _extract_status_events(payload)
        self.assertEqual(len(events), 1)

        event = events[0]
        self.assertEqual(event["alert_type"], "WHATSAPP:wamid.HBgMOTk5")
        self.assertEqual(event["category"], "delivered")
        self.assertEqual(event["phone_number"], "917388863677")
        self.assertTrue(event["delivered"])
        self.assertEqual(event["provider_message_id"], "wamid.HBgMOTk5")
        self.assertEqual(event["metadata_phone_number_id"], "1015568374973326")
        self.assertEqual(
            event["alert_date"],
            datetime.fromtimestamp(1700000000, tz=timezone.utc).date(),
        )

    def test_persist_status_events_inserts_and_updates(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        db = None
        try:
            events = _extract_status_events(
                {
                    "object": "whatsapp_business_account",
                    "entry": [
                        {
                            "changes": [
                                {
                                    "value": {
                                        "statuses": [
                                            {
                                                "id": "wamid.HBgMOTk5",
                                                "status": "failed",
                                                "timestamp": "1700000001",
                                                "recipient_id": "8303233429",
                                                "errors": [
                                                    {
                                                        "code": 131026,
                                                        "title": "Message undeliverable",
                                                    }
                                                ],
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    ],
                }
            )
            first = _persist_status_events(events, session_factory=session_factory)
            self.assertEqual(first, {"stored": 1, "updated": 0})

            second = _persist_status_events(events, session_factory=session_factory)
            self.assertEqual(second, {"stored": 0, "updated": 1})

            db = session_factory()
            row = db.execute(select(DeliveryLog)).scalar_one()
        finally:
            if db is not None:
                db.close()
            engine.dispose()

        self.assertEqual(row.webhook_status, "failed")
        self.assertFalse(row.delivered)
        self.assertEqual(row.provider_message_id, "wamid.HBgMOTk5")
        self.assertIn("Message undeliverable", row.failure_reason)


if __name__ == "__main__":
    unittest.main()
