import os
import sys
import unittest
from unittest.mock import MagicMock, call, patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crm_client import CRMClient


class TestCRMClient(unittest.TestCase):
    def setUp(self):
        self.client = CRMClient(
            base_url="https://crm.test/api/v1",
            app_key="test_app_key",
            secret_key="test_secret_key",
        )

    def test_is_configured_valid(self):
        self.assertTrue(self.client.is_configured())

    def test_is_configured_invalid(self):
        unconfigured = CRMClient(base_url="", app_key="your_app_key", secret_key="")
        self.assertFalse(unconfigured.is_configured())

        placeholder = CRMClient(base_url="https://crm.test", app_key="your_key", secret_key="real_key")
        self.assertFalse(placeholder.is_configured())

    def test_get_headers(self):
        headers = self.client.get_headers()
        self.assertEqual(headers["X-App-Key"], "test_app_key")
        self.assertEqual(headers["X-Secret-Key"], "test_secret_key")
        self.assertEqual(headers["Accept"], "application/json")

    @patch("requests.Session.get")
    def test_request_cleans_params_and_url(self, mock_get):
        mock_resp = MagicMock(status_code=200)
        mock_get.return_value = mock_resp

        resp = self.client.request("/organizations/", params={"page": 1, "empty": None, "per_page": 25})
        self.assertEqual(resp, mock_resp)

        expected_url = "https://crm.test/api/v1/organizations"
        mock_get.assert_called_once_with(
            expected_url,
            params={"page": 1, "per_page": 25},
            timeout=15,
        )

    @patch("time.sleep", return_value=None)
    @patch("requests.Session.get")
    def test_iter_pages_pagination_multi_page(self, mock_get, mock_sleep):
        resp_p1 = MagicMock(status_code=200, headers={"X-RateLimit-Remaining": "50"})
        resp_p1.json.return_value = {
            "data": [{"id": 1, "name": "Org 1"}],
            "meta": {"current_page": 1, "per_page": 100, "total": 2, "last_page": 2},
        }

        resp_p2 = MagicMock(status_code=200, headers={"X-RateLimit-Remaining": "49"})
        resp_p2.json.return_value = {
            "data": [{"id": 2, "name": "Org 2"}],
            "meta": {"current_page": 2, "per_page": 100, "total": 2, "last_page": 2},
        }

        mock_get.side_effect = [resp_p1, resp_p2]

        pages = list(self.client.iter_pages("organizations", per_page=100))
        self.assertEqual(len(pages), 2)

        # Page 1 checks
        data_p1, meta_p1, cur_1, last_1 = pages[0]
        self.assertEqual(len(data_p1), 1)
        self.assertEqual(data_p1[0]["id"], 1)
        self.assertEqual(cur_1, 1)
        self.assertEqual(last_1, 2)

        # Page 2 checks
        data_p2, meta_p2, cur_2, last_2 = pages[1]
        self.assertEqual(len(data_p2), 1)
        self.assertEqual(data_p2[0]["id"], 2)
        self.assertEqual(cur_2, 2)
        self.assertEqual(last_2, 2)

    @patch("time.sleep", return_value=None)
    @patch("requests.Session.get")
    def test_iter_pages_per_page_capped_at_100(self, mock_get, mock_sleep):
        resp = MagicMock(status_code=200, headers={"X-RateLimit-Remaining": "50"})
        resp.json.return_value = {"data": [], "meta": {"last_page": 1, "current_page": 1}}
        mock_get.return_value = resp

        list(self.client.iter_pages("organizations", per_page=250))
        call_params = mock_get.call_args[1]["params"]
        self.assertEqual(call_params["per_page"], 100)

    @patch("time.sleep", return_value=None)
    @patch("requests.Session.get")
    def test_iter_pages_retry_on_429(self, mock_get, mock_sleep):
        resp_429 = MagicMock(status_code=429, headers={"Retry-After": "1"})
        resp_200 = MagicMock(status_code=200, headers={"X-RateLimit-Remaining": "50"})
        resp_200.json.return_value = {
            "data": [{"id": 10}],
            "meta": {"current_page": 1, "last_page": 1, "total": 1},
        }
        mock_get.side_effect = [resp_429, resp_200]

        records, meta = self.client.fetch_all("organizations")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], 10)
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_with(1)

    @patch("time.sleep", return_value=None)
    @patch("requests.Session.get")
    def test_iter_pages_max_pages_limit(self, mock_get, mock_sleep):
        def fake_page(url, params=None, timeout=20):
            p = params.get("page", 1)
            resp = MagicMock(status_code=200, headers={"X-RateLimit-Remaining": "50"})
            resp.json.return_value = {
                "data": [{"id": p}],
                "meta": {"current_page": p, "last_page": 10, "total": 10},
            }
            return resp

        mock_get.side_effect = fake_page

        pages = list(self.client.iter_pages("organizations", max_pages=2))
        self.assertEqual(len(pages), 2)
        self.assertEqual(mock_get.call_count, 2)

    @patch("time.sleep", return_value=None)
    @patch("requests.Session.get")
    def test_fetch_all_aggregation_and_callback(self, mock_get, mock_sleep):
        resp_p1 = MagicMock(status_code=200, headers={"X-RateLimit-Remaining": "50"})
        resp_p1.json.return_value = {
            "data": [{"id": 1}, {"id": 2}],
            "meta": {"current_page": 1, "last_page": 2, "total": 3},
        }

        resp_p2 = MagicMock(status_code=200, headers={"X-RateLimit-Remaining": "50"})
        resp_p2.json.return_value = {
            "data": [{"id": 3}],
            "meta": {"current_page": 2, "last_page": 2, "total": 3},
        }
        mock_get.side_effect = [resp_p1, resp_p2]

        progress_calls = []

        def on_prog(cur, last, count, total):
            progress_calls.append((cur, last, count, total))

        records, meta = self.client.fetch_all("organizations", on_progress=on_prog)
        self.assertEqual(len(records), 3)
        self.assertEqual(records, [{"id": 1}, {"id": 2}, {"id": 3}])
        self.assertEqual(progress_calls, [(1, 2, 2, 3), (2, 2, 3, 3)])

    @patch("requests.Session.get")
    def test_endpoint_wrappers(self, mock_get):
        mock_resp = MagicMock(status_code=200)
        mock_get.return_value = mock_resp

        self.client.get_organizations(per_page=50, page=2)
        mock_get.assert_called_with("https://crm.test/api/v1/organizations", params={"per_page": 50, "page": 2}, timeout=15)

        self.client.get_client(1234)
        mock_get.assert_called_with("https://crm.test/api/v1/clients/1234", params={}, timeout=15)

        self.client.get_client_purchases(1234, per_page=10, page=1)
        mock_get.assert_called_with("https://crm.test/api/v1/clients/1234/purchases", params={"per_page": 10, "page": 1}, timeout=15)


if __name__ == "__main__":
    unittest.main()
