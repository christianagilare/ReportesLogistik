import json
import unittest
from unittest.mock import MagicMock

from azure_devops.client import AzureDevOpsAPIError, AzureDevOpsClient


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class AzureDevOpsClientWiqlTests(unittest.TestCase):
    def setUp(self):
        self.client = AzureDevOpsClient(
            token="Basic token",
            base_url="https://dev.azure.com",
            org="lagcloud",
            project_id="proj-id",
        )
        self.client._make_request = MagicMock()

    def test_get_query_wiql_url_unchanged(self):
        self.client._make_request.return_value = _FakeResponse(
            {"_links": {"wiql": {"href": "https://dev.azure.com/wiql-exec"}}}
        )
        url = self.client.get_query_wiql_url("query-id")
        self.assertEqual(url, "https://dev.azure.com/wiql-exec")
        method, request_url = self.client._make_request.call_args[0][:2]
        self.assertEqual(method, "GET")
        self.assertEqual(
            request_url,
            "https://dev.azure.com/lagcloud/proj-id/_apis/wit/queries/query-id?api-version=7.0",
        )
        self.assertNotIn("$expand=wiql", request_url)

    def test_execute_wiql_still_gets_url(self):
        self.client._make_request.return_value = _FakeResponse(
            {"workItems": [{"id": 11}, {"id": 22}]}
        )
        ids = self.client.execute_wiql("https://dev.azure.com/wiql-exec")
        self.assertEqual(ids, [11, 22])
        method, request_url = self.client._make_request.call_args[0][:2]
        self.assertEqual(method, "GET")
        self.assertEqual(request_url, "https://dev.azure.com/wiql-exec")

    def test_get_query_wiql_expands_wiql_text(self):
        self.client._make_request.return_value = _FakeResponse({"wiql": "select [System.Id] from WorkItems"})
        wiql = self.client.get_query_wiql("query-id")
        self.assertEqual(wiql, "select [System.Id] from WorkItems")
        method, request_url = self.client._make_request.call_args[0][:2]
        self.assertEqual(method, "GET")
        self.assertIn("$expand=wiql", request_url)
        self.assertIn("api-version=7.0", request_url)

    def test_get_query_wiql_requires_text(self):
        self.client._make_request.return_value = _FakeResponse({"wiql": ""})
        with self.assertRaises(AzureDevOpsAPIError):
            self.client.get_query_wiql("query-id")

    def test_execute_wiql_query_posts_body(self):
        self.client._make_request.return_value = _FakeResponse(
            {"workItems": [{"id": 5}, {"id": 6}]}
        )
        wiql = "select [System.Id] from WorkItems"
        ids = self.client.execute_wiql_query(wiql)
        self.assertEqual(ids, [5, 6])
        args, kwargs = self.client._make_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(
            args[1],
            "https://dev.azure.com/lagcloud/proj-id/_apis/wit/wiql?api-version=7.0",
        )
        self.assertEqual(kwargs["json_data"], {"query": wiql})
        json.dumps(kwargs["json_data"])


if __name__ == "__main__":
    unittest.main()
