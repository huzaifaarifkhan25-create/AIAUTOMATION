import unittest

import httpx

from app.main import create_app
from app.settings import Settings

app = create_app(Settings())


class BusinessSearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        )
        self.addAsyncCleanup(self.client.aclose)

    async def test_med_spa_search_returns_normalized_mock_businesses(self):
        response = await self.client.post(
            "/businesses/search", json={"industry": "med spa", "location": "Islamabad"}
        )

        self.assertEqual(response.status_code, 200)
        businesses = response.json()
        self.assertEqual(len(businesses), 2)
        for business in businesses:
            self.assertEqual(
                set(business),
                {"name", "website", "phone", "address", "rating", "review_count"},
            )
            self.assertIn("Mock", business["name"])
            self.assertIn("Islamabad", business["address"])
        self.assertEqual(businesses[0]["rating"], 4.5)
        self.assertEqual(businesses[0]["review_count"], 120)
        self.assertIsNone(businesses[0]["phone"])
        for field in ("website", "phone", "rating", "review_count"):
            self.assertIsNone(businesses[1][field])

    async def test_aliases_case_and_surrounding_whitespace(self):
        for industry in (" MED SPA ", "Med Spas", "medspa", "MEDSPAS"):
            with self.subTest(industry=industry):
                response = await self.client.post(
                    "/businesses/search",
                    json={"industry": industry, "location": "  Lahore  "},
                )
                self.assertEqual(response.status_code, 200)
                businesses = response.json()
                self.assertEqual(len(businesses), 2)
                self.assertEqual(businesses[0]["address"], "Mock address, Lahore")

    async def test_unsupported_industry_returns_empty_list(self):
        response = await self.client.post(
            "/businesses/search", json={"industry": "dentist", "location": "Islamabad"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    async def test_invalid_requests_are_rejected(self):
        invalid_requests = [
            {},
            {"industry": "med spa"},
            {"location": "Islamabad"},
            {"industry": " ", "location": "Islamabad"},
            {"industry": "med spa", "location": " \t "},
            {"industry": 123, "location": "Islamabad"},
            {"industry": "med spa", "location": None},
            {"industry": "x" * 101, "location": "Islamabad"},
            {"industry": "med spa", "location": "x" * 201},
        ]
        for payload in invalid_requests:
            with self.subTest(payload=payload):
                response = await self.client.post("/businesses/search", json=payload)
                self.assertEqual(response.status_code, 422)
                self.assertTrue(response.json()["detail"])

    async def test_openapi_documents_search_contract(self):
        response = await self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        operation = schema["paths"]["/businesses/search"]["post"]
        self.assertTrue(operation["requestBody"]["required"])
        response_schema = operation["responses"]["200"]["content"]["application/json"][
            "schema"
        ]
        self.assertEqual(response_schema["type"], "array")
        self.assertEqual(response_schema["items"]["$ref"], "#/components/schemas/Business")


if __name__ == "__main__":
    unittest.main()
