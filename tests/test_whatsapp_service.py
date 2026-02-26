import unittest

from app.services.whatsapp_service import build_payload, resolve_media_url, validate_api_url


class WhatsAppServiceTest(unittest.TestCase):
    def test_resolve_media_url_keeps_absolute_url(self):
        media_url = resolve_media_url(
            "https://cdn.example.com/static/images/DRS-1001.jpg",
            "https://api.example.com",
        )
        self.assertEqual(media_url, "https://cdn.example.com/static/images/DRS-1001.jpg")

    def test_resolve_media_url_builds_absolute_url_from_relative_path(self):
        media_url = resolve_media_url(
            "/static/images/DRS-1001.jpg",
            "https://inventory.example.com/",
        )
        self.assertEqual(media_url, "https://inventory.example.com/static/images/DRS-1001.jpg")

    def test_graph_payload_uses_image_when_media_url_present(self):
        payload = build_payload(
            "https://graph.facebook.com/v19.0/123/messages",
            "Alert text",
            "+1 (555) 123-4567",
            "https://inventory.example.com/static/images/DRS-1001.jpg",
        )
        self.assertEqual(payload["messaging_product"], "whatsapp")
        self.assertEqual(payload["to"], "15551234567")
        self.assertEqual(payload["type"], "image")
        self.assertEqual(
            payload["image"]["link"],
            "https://inventory.example.com/static/images/DRS-1001.jpg",
        )
        self.assertEqual(payload["image"]["caption"], "Alert text")

    def test_non_graph_payload_includes_media_url(self):
        payload = build_payload(
            "https://api.internal.local/whatsapp/send",
            "Alert text",
            "15551234567",
            "https://inventory.example.com/static/images/DRS-1001.jpg",
        )
        self.assertEqual(payload["to"], "15551234567")
        self.assertEqual(payload["message"], "Alert text")
        self.assertEqual(
            payload["media_url"],
            "https://inventory.example.com/static/images/DRS-1001.jpg",
        )

    def test_validate_api_url_accepts_https(self):
        self.assertEqual(
            validate_api_url("https://graph.facebook.com/v19.0/123/messages"),
            "https://graph.facebook.com/v19.0/123/messages",
        )

    def test_validate_api_url_rejects_non_http_scheme(self):
        with self.assertRaises(RuntimeError):
            validate_api_url("file:///tmp/messages")


if __name__ == "__main__":
    unittest.main()
