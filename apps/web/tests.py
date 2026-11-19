"""Frontend uzatish view'lari uchun testlar."""

from django.test import SimpleTestCase
from django.urls import reverse


class FrontendServingTests(SimpleTestCase):
    def test_index_serves_spa_shell(self):
        response = self.client.get(reverse("web:index"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn('id="app"', content)
        self.assertIn("/assets/js/app.js", content)
        self.assertIn("/assets/css/styles.css", content)

    def test_css_and_js_are_served(self):
        for asset, content_type in (
            ("css/styles.css", "text/css"),
            ("js/app.js", "text/javascript"),
        ):
            with self.subTest(asset=asset):
                response = self.client.get(
                    reverse("web:asset", args=[asset])
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(content_type, response["Content-Type"])

    def test_path_traversal_is_blocked(self):
        response = self.client.get(
            reverse("web:asset", args=["../config/settings.py"])
        )
        self.assertEqual(response.status_code, 404)

    def test_missing_asset_returns_404(self):
        response = self.client.get(
            reverse("web:asset", args=["js/yoq.js"])
        )
        self.assertEqual(response.status_code, 404)

    def test_only_get_is_allowed(self):
        response = self.client.post(reverse("web:index"))
        self.assertEqual(response.status_code, 405)
