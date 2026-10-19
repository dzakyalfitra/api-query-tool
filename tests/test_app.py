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

    @patch("crm_client.CRMClient.request")
    def test_entity_inspection_detection_and_drill_down(self, mock_request):
        """Verify that entity relations are detected and drill-down + breadcrumbs navigation works."""
        mock_resp_lead = MagicMock(status_code=200, reason="OK")
        mock_resp_lead.url = "https://crm.test/leads"
        mock_resp_lead.json.return_value = {
            "data": [{
                "id": 5283,
                "title": "BricsCAD Deal",
                "status": "Chatting",
                "customer": {"id": 6523, "name": "Shobron Zhuhri Mr"},
                "organization": {"id": 9842, "company_name": "SKS Listrik Kalimantan, PT"},
            }],
            "meta": {"current_page": 1, "last_page": 1, "total": 1, "per_page": 25},
        }

        mock_resp_org = MagicMock(status_code=200, reason="OK")
        mock_resp_org.url = "https://crm.test/organizations/9842"
        mock_resp_org.json.return_value = {
            "data": {
                "id": 9842,
                "company_name": "SKS Listrik Kalimantan, PT",
                "clients": [{"id": 6523, "pic_name": "Shobron Zhuhri Mr"}],
            }
        }

        mock_request.side_effect = [mock_resp_lead, mock_resp_org, mock_resp_lead]

        at = AppTest.from_file(APP_PATH, default_timeout=20)
        at.run()

        # Select Leads (List) and fetch
        at.sidebar.selectbox[0].select("Leads (List)")
        at.run()
        at.sidebar.button[0].click()
        at.run()

        self.assertEqual(at.session_state.selected_endpoint, "Leads (List)")

        # Find View Org #9842 button
        org_btns = [b for b in at.button if "View Org #9842" in b.label]
        self.assertTrue(len(org_btns) > 0)

        # Click drill down into organization
        org_btns[0].click()
        at.run()

        self.assertEqual(at.session_state.selected_endpoint, "Organization (Detail by ID)")
        self.assertEqual(at.session_state.org_id_input, "9842")
        self.assertEqual(len(at.session_state.nav_breadcrumbs), 1)

        # Verify breadcrumbs Back button exists and returns to Leads
        back_btns = [b for b in at.button if "Back to" in b.label]
        self.assertTrue(len(back_btns) > 0)
        back_btns[0].click()
        at.run()

        self.assertEqual(at.session_state.selected_endpoint, "Leads (List)")
        self.assertEqual(len(at.session_state.nav_breadcrumbs), 0)

    @patch("crm_client.CRMClient.request")
    def test_organization_detail_embedded_clients_drill_down(self, mock_request):
        """Verify that organization detail renders embedded clients and allows 1-click drill-down."""
        mock_resp_org = MagicMock(status_code=200, reason="OK")
        mock_resp_org.url = "https://crm.test/organizations/8066"
        mock_resp_org.json.return_value = {
            "data": {
                "id": 8066,
                "company_name": "Rifqi Com",
                "clients": [{"id": 5177, "pic_name": "Abdul Salam", "email": "as@test.com"}],
            }
        }

        mock_resp_cli = MagicMock(status_code=200, reason="OK")
        mock_resp_cli.url = "https://crm.test/clients/5177"
        mock_resp_cli.json.return_value = {
            "data": {
                "id": 5177,
                "pic_name": "Abdul Salam",
                "organization": {"id": 8066, "company_name": "Rifqi Com"},
            }
        }

        mock_request.side_effect = [mock_resp_org, mock_resp_cli]

        at = AppTest.from_file(APP_PATH, default_timeout=20)
        at.run()

        at.sidebar.selectbox[0].select("Organization (Detail by ID)")
        at.run()
        at.sidebar.button[0].click()
        at.run()

        # Find View Client #5177 button in associated clients list
        cli_btns = [b for b in at.button if "View Client #5177" in b.label]
        self.assertTrue(len(cli_btns) > 0)

        cli_btns[0].click()
        at.run()

        self.assertEqual(at.session_state.selected_endpoint, "Client (Detail by ID)")
        self.assertEqual(at.session_state.client_id_input, "5177")
        self.assertEqual(len(at.session_state.nav_breadcrumbs), 1)
    @patch("crm_client.CRMClient.request")
    def test_filter_by_industry_and_keyword(self, mock_request):
        """Verify that page-level industry and keyword filters narrow rows and offer filtered CSV download."""
        mock_resp = MagicMock(status_code=200, reason="OK")
        mock_resp.url = "https://crm.test/organizations"
        mock_resp.json.return_value = {
            "data": [
                {"id": 1, "company_name": "Bali Resort", "industry": "Hospitality", "city": "Denpasar"},
                {"id": 2, "company_name": "Bank Mega", "industry": "Banking", "city": "Jakarta"},
                {"id": 3, "company_name": "Tech Corp", "industry": "Technology", "city": "Bandung"},
            ],
            "meta": {"current_page": 1, "last_page": 2, "total": 6, "per_page": 3},
        }
        mock_request.return_value = mock_resp

        at = AppTest.from_file(APP_PATH, default_timeout=20)
        at.run()
        at.sidebar.button[0].click()
        at.run()

        # Total 3 initial rows
        self.assertEqual(len(at.dataframe[0].value), 3)

        # Select 'Hospitality' from Industry multiselect
        ind_ms = [m for m in at.multiselect if "Industry" in m.label][0]
        self.assertIn("Hospitality", ind_ms.options)
        ind_ms.select("Hospitality")
        at.run()

        # Filtered to 1 row
        self.assertEqual(len(at.dataframe[0].value), 1)
        self.assertEqual(at.dataframe[0].value.iloc[0]["company_name"], "Bali Resort")

        # Filtered CSV button is present
        dl_btns = [b for b in at.download_button if "Filtered CSV" in b.label]
        self.assertEqual(len(dl_btns), 1)

    @patch("crm_client.CRMClient.iter_pages")
    @patch("crm_client.CRMClient.request")
    def test_global_search_sync_and_filter(self, mock_request, mock_iter):
        """Verify that global scope syncs all pages into memory and filters across the complete dataset."""
        mock_resp = MagicMock(status_code=200, reason="OK")
        mock_resp.url = "https://crm.test/organizations"
        mock_resp.json.return_value = {
            "data": [{"id": 1, "company_name": "P1 Org", "industry": "Other"}],
            "meta": {"current_page": 1, "last_page": 2, "total": 2, "per_page": 1},
        }
        mock_request.return_value = mock_resp

        mock_iter.return_value = iter([
            ([{"id": 1, "company_name": "Hotel Bali", "industry": "Hospitality"}], {}, 1, 2),
            ([{"id": 2, "company_name": "Bank Central", "industry": "Banking"}], {}, 2, 2),
        ])

        at = AppTest.from_file(APP_PATH, default_timeout=20)
        at.run()
        at.sidebar.button[0].click()
        at.run()

        # Select Global Scope
        scope_radio = [r for r in at.radio if "Scope" in r.label or "scope" in r.key][0]
        scope_radio.set_value("🌐 All Records (Global)")
        at.run()

        # Trigger in-memory sync
        sync_btn = [b for b in at.button if "Sync All Records" in b.label][0]
        sync_btn.click()
        at.run()

        # Consolidated records
        self.assertEqual(len(at.dataframe[0].value), 2)

        # Filter by Hospitality
        ind_ms = [m for m in at.multiselect if "Industry" in m.label][0]
        ind_ms.select("Hospitality")
        at.run()

        self.assertEqual(len(at.dataframe[0].value), 1)
        self.assertEqual(at.dataframe[0].value.iloc[0]["company_name"], "Hotel Bali")

if __name__ == "__main__":
    unittest.main()
