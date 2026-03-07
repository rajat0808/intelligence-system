import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from app.services.channels.telegram_service import send_telegram_alert, send_telegram_document


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
        {
            "TELEGRAM_BOT_TOKEN": "bot-token",
            "TELEGRAM_CHAT_ID": "chat-id",
            "TELEGRAM_ALERT_TEMPLATE": "[ALERT]\\n{message}",
        },
        clear=True,
    )
    def test_send_telegram_alert_applies_template(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}

        with patch(
            "app.services.channels.telegram_service.requests.post",
            return_value=response,
        ) as post_mock:
            result = send_telegram_alert("Inventory alert")

        self.assertTrue(result)
        self.assertEqual(
            post_mock.call_args.kwargs["json"],
            {"chat_id": "chat-id", "text": "[ALERT]\nInventory alert"},
        )

    @patch.dict(
        "os.environ",
        {
            "TELEGRAM_BOT_TOKEN": "bot-token",
            "TELEGRAM_CHAT_ID": "chat-id",
            "TELEGRAM_ALERT_TEMPLATE": "[ALERT]",
        },
        clear=True,
    )
    def test_send_telegram_alert_appends_message_when_placeholder_missing(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}

        with patch(
            "app.services.channels.telegram_service.requests.post",
            return_value=response,
        ) as post_mock:
            result = send_telegram_alert("Inventory alert")

        self.assertTrue(result)
        self.assertEqual(
            post_mock.call_args.kwargs["json"],
            {"chat_id": "chat-id", "text": "[ALERT]\nInventory alert"},
        )

    @patch.dict(
        "os.environ",
        {"TELEGRAM_BOT_TOKEN": "bot-token", "TELEGRAM_CHAT_ID": "chat-id"},
        clear=True,
    )
    def test_send_telegram_alert_sends_photo_when_image_url_provided(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}

        with patch(
            "app.services.channels.telegram_service.requests.post",
            return_value=response,
        ) as post_mock:
            result = send_telegram_alert(
                "Inventory alert",
                image_url="https://example.com/image.jpg",
            )

        self.assertTrue(result)
        post_mock.assert_called_once()
        self.assertEqual(
            post_mock.call_args.args[0],
            "https://api.telegram.org/botbot-token/sendPhoto",
        )
        self.assertEqual(
            post_mock.call_args.kwargs["data"],
            {
                "chat_id": "chat-id",
                "caption": "Inventory alert",
                "photo": "https://example.com/image.jpg",
            },
        )

    @patch.dict(
        "os.environ",
        {"TELEGRAM_BOT_TOKEN": "bot-token", "TELEGRAM_CHAT_ID": "chat-id"},
        clear=True,
    )
    def test_send_telegram_alert_falls_back_to_fallback_image_when_photo_send_fails(self):
        fallback_response = Mock()
        fallback_response.raise_for_status.return_value = None
        fallback_response.json.return_value = {"ok": True}

        with patch(
            "app.services.channels.telegram_service.requests.post",
            side_effect=[requests.RequestException("photo failed"), fallback_response],
        ) as post_mock:
            result = send_telegram_alert(
                "Inventory alert",
                image_url="https://example.com/image.jpg",
            )

        self.assertTrue(result)
        self.assertEqual(post_mock.call_count, 2)
        self.assertEqual(
            post_mock.call_args_list[0].args[0],
            "https://api.telegram.org/botbot-token/sendPhoto",
        )
        self.assertEqual(
            post_mock.call_args_list[1].args[0],
            "https://api.telegram.org/botbot-token/sendPhoto",
        )

    @patch.dict(
        "os.environ",
        {"TELEGRAM_BOT_TOKEN": "bot-token", "TELEGRAM_CHAT_ID": "chat-id"},
        clear=True,
    )
    def test_send_telegram_alert_uses_raw_image_reference_from_datasource(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}

        with patch(
            "app.services.channels.telegram_service.requests.post",
            return_value=response,
        ) as post_mock:
            result = send_telegram_alert(
                "Inventory alert",
                image_url="P-2211",
            )

        self.assertTrue(result)
        post_mock.assert_called_once()
        self.assertEqual(
            post_mock.call_args.args[0],
            "https://api.telegram.org/botbot-token/sendPhoto",
        )
        self.assertEqual(post_mock.call_args.kwargs["data"]["photo"], "P-2211")

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

    @patch.dict(
        "os.environ",
        {"TELEGRAM_BOT_TOKEN": "bot-token", "TELEGRAM_CHAT_ID": "chat-id"},
        clear=True,
    )
    def test_send_telegram_document_posts_expected_payload(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}

        document_path = Path("test_report.pdf")
        document_path.write_bytes(b"%PDF-1.4\n%test\n")
        try:
            with patch(
                "app.services.channels.telegram_service.requests.post",
                return_value=response,
            ) as post_mock:
                result = send_telegram_document(
                    document_path,
                    caption="Daily Report",
                )

            self.assertTrue(result)
            post_mock.assert_called_once()
            self.assertEqual(
                post_mock.call_args.args[0],
                "https://api.telegram.org/botbot-token/sendDocument",
            )
            self.assertEqual(
                post_mock.call_args.kwargs["data"],
                {"chat_id": "chat-id", "caption": "Daily Report"},
            )
            self.assertIn("document", post_mock.call_args.kwargs["files"])
        finally:
            document_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
