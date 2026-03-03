import unittest

from app.services.whatsapp_service import (
    build_payload,
    build_template_payload,
    resolve_media_url,
    validate_api_url,
)


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
            "738-886-3677",
            "https://inventory.example.com/static/images/DRS-1001.jpg",
        )
        self.assertEqual(payload["messaging_product"], "whatsapp")
        self.assertEqual(payload["to"], "7388863677")
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
            "7388863677",
            "https://inventory.example.com/static/images/DRS-1001.jpg",
        )
        self.assertEqual(payload["to"], "7388863677")
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

    def test_graph_template_payload_with_image_and_body_fields(self):
        payload = build_template_payload(
            api_url="https://graph.facebook.com/v19.0/123/messages",
            phone="738-886-3677",
            template_name="inventory_transfer_alert",
            language_code="en",
            store_id="S-101",
            category="Kids Wear",
            department="Apparel",
            transfer_to="Store 205",
            aging_system_rule="Aging > 45 days",
            image_url="https://inventory.example.com/static/images/S-101.jpg",
        )

        self.assertEqual(payload["messaging_product"], "whatsapp")
        self.assertEqual(payload["to"], "7388863677")
        self.assertEqual(payload["type"], "template")
        self.assertEqual(payload["template"]["name"], "inventory_transfer_alert")
        self.assertEqual(payload["template"]["language"]["code"], "en")

        components = payload["template"]["components"]
        self.assertEqual(components[0]["type"], "header")
        self.assertEqual(components[0]["parameters"][0]["type"], "image")
        self.assertEqual(
            components[0]["parameters"][0]["image"]["link"],
            "https://inventory.example.com/static/images/S-101.jpg",
        )
        self.assertEqual(components[1]["type"], "body")
        self.assertEqual(
            [parameter["text"] for parameter in components[1]["parameters"]],
            ["S-101", "Kids Wear", "Apparel", "Store 205", "Aging > 45 days"],
        )

    def test_graph_template_payload_without_image_uses_body_only(self):
        payload = build_template_payload(
            api_url="https://graph.facebook.com/v19.0/123/messages",
            phone="7388863677",
            template_name="inventory_transfer_alert",
            language_code="en",
            store_id="S-101",
            category="Kids Wear",
            department="Apparel",
            transfer_to="Store 205",
            aging_system_rule="Aging > 45 days",
            image_url=None,
        )

        components = payload["template"]["components"]
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0]["type"], "body")
        self.assertEqual(
            [parameter["text"] for parameter in components[0]["parameters"]],
            ["S-101", "Kids Wear", "Apparel", "Store 205", "Aging > 45 days"],
        )

    def test_template_payload_rejects_non_graph_url(self):
        with self.assertRaises(ValueError):
            build_template_payload(
                api_url="https://api.internal.local/whatsapp/send",
                phone="7388863677",
                template_name="inventory_transfer_alert",
                language_code="en",
                store_id="S-101",
                category="Kids Wear",
                department="Apparel",
                transfer_to="Store 205",
                aging_system_rule="Aging > 45 days",
                image_url=None,
            )


if __name__ == "__main__":
    unittest.main()
