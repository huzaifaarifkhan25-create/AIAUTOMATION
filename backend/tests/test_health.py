import unittest

import httpx

from app.main import create_app
from app.settings import Settings

app = create_app(Settings())


class HealthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        )
        self.addAsyncCleanup(self.client.aclose)

    async def test_health_returns_ok(self):
        response = await self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(response.json(), {"status": "ok"})

    async def test_docs_serves_swagger_ui(self):
        response = await self.client.get("/docs")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("SwaggerUIBundle", response.text)
        self.assertIn("url: '/openapi.json'", response.text)

    async def test_openapi_documents_health(self):
        response = await self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        operation = schema["paths"]["/health"]["get"]
        self.assertIn("200", operation["responses"])
        self.assertEqual(schema["info"]["title"], "Med Spa Automation API")


if __name__ == "__main__":
    unittest.main()
