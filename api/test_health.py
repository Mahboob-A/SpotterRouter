from django.test import SimpleTestCase


class HealthCheckEndpointTests(SimpleTestCase):
    def test_health_check_returns_ok_status(self) -> None:
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
