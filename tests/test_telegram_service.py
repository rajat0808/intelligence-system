import unittest
from unittest.mock import Mock, patch

import requests

from app.services.channels.telegram_service import send_telegram_alert


class TelegramServiceTest(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_send_telegram_alert_skips_when_config_missing(self):
        with patch("app.services.channels.telegram_service.requests.post") as post_mock:
            self.assertFalse(send_telegram_alert("Inventory alert"))
            post_mock.assert_not_called()

    @patch.dict(
        "os.environ",
        {"TELEGRAM_BOT_TOKEN": "bot-token", "TELEGRAM_CHAT_ID": "chat-id"},
        clear=True,
    )
    def test_send_telegram_alert_posts_expected_payload(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}

        with patch(
            "app.services.channels.telegram_service.requests.post",
            return_value=response,
        ) as post_mock:
            result = send_telegram_alert("Inventory alert")

        self.assertTrue(result)
        post_mock.assert_called_once()
        self.assertEqual(
            post_mock.call_args.args[0],
            "https://api.telegram.org/botbot-token/sendMessage",
        )
        self.assertEqual(
            post_mock.call_args.kwargs["json"],
            {"chat_id": "chat-id", "text": "Inventory alert"},
        )

    @patch.dict(
        "os.environ",
        {"TELEGRAM_BOT_TOKEN": "bot-token", "TELEGRAM_CHAT_ID": "chat-id"},
        clear=True,
    )
    def test_send_telegram_alert_handles_telegram_error_payload(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": False, "description": "Bad Request"}

        with patch(
            "app.services.channels.telegram_service.requests.post",
            return_value=response,
        ):
            self.assertFalse(send_telegram_alert("Inventory alert"))

    @patch.dict(
        "os.environ",
        {"TELEGRAM_BOT_TOKEN": "bot-token", "TELEGRAM_CHAT_ID": "chat-id"},
        clear=True,
    )
    def test_send_telegram_alert_handles_request_exception(self):
        with patch(
            "app.services.channels.telegram_service.requests.post",
            side_effect=requests.RequestException("network error"),
        ):
            self.assertFalse(send_telegram_alert("Inventory alert"))


if __name__ == "__main__":
    unittest.main()
