import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from streamlit.testing.v1 import AppTest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))
class TestStreamlitApp(unittest.TestCase):
    def test_app_initial_render(self):
        """Verify the app boots headlessly without unhandled exceptions and sidebar controls render."""
        at = AppTest.from_file(APP_PATH, default_timeout=20)
        at.run()

        self.assertFalse(at.exception)
        # Verify sidebar selectbox exists
        self.assertTrue(len(at.sidebar.selectbox) > 0)
        self.assertEqual(at.sidebar.selectbox[0].value, "Organizations (List)")
        # Verify Fetch Data button exists
        fetch_btns = [b for b in at.sidebar.button if "Fetch" in b.label]
        self.assertTrue(len(fetch_btns) > 0)

    @patch("crm_client.CRMClient.request")
    def test_fetch_renders_table_and_metrics(self, mock_request):
        """Verify that fetching data renders metrics and DataFrame."""
        mock_resp = MagicMock(status_code=200, reason="OK")
        mock_resp.url = "https://crm.test/api/v1/organizations"
        mock_resp.json.return_value = {
            "data": [
                {"id": 1, "name": "Company A", "email": "a@test.com"},
                {"id": 2, "name": "Company B", "email": "b@test.com"},
            ],
            "meta": {"current_page": 1, "per_page": 25, "total": 2, "last_page": 1},
        }
        mock_request.return_value = mock_resp

        at = AppTest.from_file(APP_PATH, default_timeout=20)
        at.run()
        at.sidebar.button[0].click()  # Click Fetch Data
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.last_meta["status_code"], 200)
        self.assertEqual(at.session_state.last_meta["endpoint_path"], "organizations")
        self.assertTrue(len(at.dataframe) > 0)

    @patch("crm_client.CRMClient.request")
    def test_pagination_and_cache_cycle(self, mock_request):
        """Verify Next/Prev page navigation, 5-min session cache hits, and force refresh."""
        def fake_page_request(endpoint, params=None, timeout=15):
            p = (params or {}).get("page", 1)
            resp = MagicMock(status_code=200, reason="OK")
            resp.url = f"https://crm.test/{endpoint}?page={p}"
            resp.json.return_value = {
                "data": [{"id": p, "name": f"Org {p}"}],
                "meta": {"current_page": p, "per_page": 25, "total": 50, "last_page": 2},
            }
            return resp

        mock_request.side_effect = fake_page_request

        at = AppTest.from_file(APP_PATH, default_timeout=20)
        at.run()

        # 1. Fetch Page 1
        at.sidebar.button[0].click()
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page_number, 1)
        self.assertFalse(at.session_state.last_meta["from_cache"])
        self.assertEqual(mock_request.call_count, 1)

        # 2. Click Next -> Page 2
        next_btn = [b for b in at.button if "Next" in b.label][0]
        next_btn.click()
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page_number, 2)
        self.assertFalse(at.session_state.last_meta["from_cache"])
        self.assertEqual(mock_request.call_count, 2)

        # 3. Click Previous -> Page 1 (Must hit session cache)
        prev_btn = [b for b in at.button if "Previous" in b.label][0]
        prev_btn.click()
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page_number, 1)
        self.assertTrue(at.session_state.last_meta["from_cache"])
        self.assertEqual(mock_request.call_count, 2)  # Zero new API calls

        # 4. Click Refresh -> Force live reload from API
        refresh_btn = [b for b in at.button if "Refresh" in b.label][0]
        refresh_btn.click()
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page_number, 1)
        self.assertFalse(at.session_state.last_meta["from_cache"])
        self.assertEqual(mock_request.call_count, 3)

    @patch("crm_client.CRMClient.request")
    def test_endpoint_change_resets_state(self, mock_request):
        """Verify that selecting a different endpoint resets page number and previous response."""
        mock_resp = MagicMock(status_code=200, reason="OK")
        mock_resp.url = "https://crm.test/organizations"
        mock_resp.json.return_value = {
            "data": [{"id": 1}],
            "meta": {"current_page": 1, "last_page": 2, "total": 2},
        }
        mock_request.return_value = mock_resp

        at = AppTest.from_file(APP_PATH, default_timeout=20)
        at.run()
        at.sidebar.button[0].click()
        at.run()

        # Navigate to page 2
        next_btn = [b for b in at.button if "Next" in b.label][0]
        next_btn.click()
        at.run()
        self.assertEqual(at.session_state.page_number, 2)

        # Switch endpoint to Sales (List)
        at.sidebar.selectbox[0].select("Sales (List)")
        at.run()

        # State should be reset
        self.assertEqual(at.session_state.page_number, 1)
        self.assertIsNone(at.session_state.last_response)

    @patch("crm_client.CRMClient.request")
    @patch("crm_client.CRMClient.iter_pages")
    def test_bulk_export_stream(self, mock_iter_pages, mock_request):
        """Verify that multi-page bulk exporter executes generator stream and renders download buttons."""
        mock_resp = MagicMock(status_code=200, reason="OK")
        mock_resp.url = "https://crm.test/organizations"
        mock_resp.json.return_value = {
            "data": [{"id": 1}],
            "meta": {"current_page": 1, "last_page": 2, "total": 2, "per_page": 25},
        }
        mock_request.return_value = mock_resp

        mock_iter_pages.return_value = iter([
            ([{"id": 1, "name": "Bulk A"}], {"current_page": 1, "last_page": 2}, 1, 2),
            ([{"id": 2, "name": "Bulk B"}], {"current_page": 2, "last_page": 2}, 2, 2),
        ])

        at = AppTest.from_file(APP_PATH, default_timeout=20)
        at.run()
        at.sidebar.button[0].click()
        at.run()

        # Trigger bulk export
        bulk_btn = [b for b in at.button if "Fetch All Pages" in b.label][0]
        bulk_btn.click()
        at.run()

        self.assertFalse(at.exception)
        dl_buttons = [b.label for b in at.download_button if "All" in b.label]
        self.assertTrue(any("JSON" in b for b in dl_buttons))
        self.assertTrue(any("CSV" in b for b in dl_buttons))


if __name__ == "__main__":
    unittest.main()
