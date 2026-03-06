import unittest
from unittest.mock import patch

from app.services import notification_service


class NotificationServiceTest(unittest.TestCase):
    def test_send_inventory_alert_dispatches_raw_message(self):
        captured = {}

        def fake_telegram_sender(message):
            captured["message"] = message
            return True

        with patch.dict(
            notification_service._CHANNEL_HANDLERS,
            {"telegram": fake_telegram_sender},
            clear=True,
        ):
            result = notification_service.send_inventory_alert("Inventory event")

        self.assertEqual(result, {"telegram": True})
        self.assertEqual(captured["message"], "Inventory event")

    def test_send_low_stock_alert_formats_and_dispatches_message(self):
        captured = {}

        def fake_telegram_sender(message):
            captured["message"] = message
            return True

        with patch.dict(
            notification_service._CHANNEL_HANDLERS,
            {"telegram": fake_telegram_sender},
            clear=True,
        ):
            result = notification_service.send_low_stock_alert("SKU-1001", 3)

        self.assertEqual(result, {"telegram": True})
        self.assertIn("[LOW STOCK ALERT]", captured["message"])
        self.assertIn("Product: SKU-1001", captured["message"])
        self.assertIn("Current Stock: 3", captured["message"])

    def test_send_anomaly_alert_formats_score_with_two_decimals(self):
        captured = {}

        def fake_telegram_sender(message):
            captured["message"] = message
            return True

        with patch.dict(
            notification_service._CHANNEL_HANDLERS,
            {"telegram": fake_telegram_sender},
            clear=True,
        ):
            result = notification_service.send_anomaly_alert("SKU-2002", 0.9876)

        self.assertEqual(result, {"telegram": True})
        self.assertIn("[ANOMALY ALERT]", captured["message"])
        self.assertIn("Product: SKU-2002", captured["message"])
        self.assertIn("Anomaly Score: 0.99", captured["message"])

    def test_send_low_stock_alert_with_unknown_channel_returns_empty_dispatch(self):
        with patch.dict(notification_service._CHANNEL_HANDLERS, {}, clear=True):
            result = notification_service.send_low_stock_alert(
                "SKU-3003",
                1,
                channels=["slack"],
            )
        self.assertEqual(result, {})

    def test_send_inventory_alert_empty_message_returns_empty_dispatch(self):
        with patch.dict(
            notification_service._CHANNEL_HANDLERS,
            {"telegram": lambda message: True},
            clear=True,
        ):
            result = notification_service.send_inventory_alert("   ")
        self.assertEqual(result, {})

    def test_send_inventory_alert_forwards_image_url_when_supported(self):
        captured = {}

        def fake_telegram_sender(message, image_url=None):
            captured["message"] = message
            captured["image_url"] = image_url
            return True

        with patch.dict(
            notification_service._CHANNEL_HANDLERS,
            {"telegram": fake_telegram_sender},
            clear=True,
        ):
            result = notification_service.send_inventory_alert(
                "Inventory event",
                image_url="/static/images/ABC.jpg",
            )

        self.assertEqual(result, {"telegram": True})
        self.assertEqual(captured["message"], "Inventory event")
        self.assertEqual(captured["image_url"], "/static/images/ABC.jpg")


if __name__ == "__main__":
    unittest.main()
