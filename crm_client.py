import os
import time
from typing import Any, Callable, Generator
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class CRMClient:
    def __init__(self, base_url: str = None, app_key: str = None, secret_key: str = None):
        self.base_url = (base_url or os.getenv("CRM_BASE_URL", "")).rstrip("/")
        self.app_key = app_key or os.getenv("CRM_APP_KEY", "")
        self.secret_key = secret_key or os.getenv("CRM_SECRET_KEY", "")
        self._session = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(self.get_headers())
        return self._session
    def is_configured(self) -> bool:
        """Check if base URL and API keys are set and not placeholder values."""
        if not self.base_url or not self.app_key or not self.secret_key:
            return False
        if "your_" in self.app_key.lower() or "your_" in self.secret_key.lower():
            return False
        return True

    def get_headers(self) -> dict:
        return {
            "X-App-Key": self.app_key,
            "X-Secret-Key": self.secret_key,
            "Accept": "application/json",
        }

    def request(self, endpoint: str, params: dict = None, timeout: int = 15) -> requests.Response:
        """Send a GET request to the CRM API using a persistent HTTP connection."""
        endpoint = endpoint.strip("/")
        url = f"{self.base_url}/{endpoint}"
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        return self.session.get(url, params=clean_params, timeout=timeout)

    def iter_pages(
        self,
        endpoint: str,
        params: dict = None,
        per_page: int = 100,
        max_pages: int = None,
        timeout: int = 20,
    ) -> Generator[tuple[list[dict], dict, int, int], None, None]:
        """
        Stream pages from a CRM endpoint one by one with rate-limit pacing and automatic retries.
        Yields (records_chunk, meta_dict, current_page, last_page).
        """
        page = 1
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        clean_params["per_page"] = max(1, min(int(per_page), 100))
        endpoint = endpoint.strip("/")
        url = f"{self.base_url}/{endpoint}"

        while True:
            clean_params["page"] = page

            # Retry loop for resilience (transient network errors or HTTP 429)
            resp = None
            for attempt in range(3):
                try:
                    resp = self.session.get(url, params=clean_params, timeout=timeout)
                    if resp.status_code == 429:
                        wait_time = int(resp.headers.get("Retry-After", 2 ** attempt))
                        time.sleep(wait_time)
                        continue
                    resp.raise_for_status()
                    break
                except requests.RequestException:
                    if attempt == 2:
                        raise
                    time.sleep(1.5 ** attempt)

            body = resp.json()
            data = body.get("data", [])
            meta = body.get("meta", {})
            last_page = max(1, int(meta.get("last_page", 1)))

            yield data, meta, page, last_page

            if page >= last_page or (max_pages is not None and page >= max_pages):
                break

            # Respect server rate-limit header (60 req/min)
            remaining = int(resp.headers.get("X-RateLimit-Remaining", 10))
            if remaining < 5:
                time.sleep(2.0)
            else:
                time.sleep(0.1)

            page += 1

    def fetch_all(
        self,
        endpoint: str,
        params: dict = None,
        per_page: int = 100,
        max_pages: int = None,
        timeout: int = 20,
        on_progress: Callable[[int, int, int, int | None], None] = None,
    ) -> tuple[list[dict], dict]:
        """
        Fetch all pages and aggregate records into a single list.
        Optional on_progress(current_page, last_page, current_records_count, total_records) callback.
        """
        all_records = []
        last_meta = {}
        for records, meta, cur_page, last_page in self.iter_pages(
            endpoint=endpoint,
            params=params,
            per_page=per_page,
            max_pages=max_pages,
            timeout=timeout,
        ):
            all_records.extend(records)
            last_meta = meta
            if on_progress:
                on_progress(cur_page, last_page, len(all_records), meta.get("total"))

        return all_records, last_meta

    # Specific Endpoints
    def get_organizations(self, per_page: int = 25, page: int = 1) -> requests.Response:
        return self.request("organizations", params={"per_page": per_page, "page": page})

    def get_organization(self, org_id: str | int, per_page: int = 25) -> requests.Response:
        return self.request(f"organizations/{org_id}", params={"per_page": per_page})

    def get_clients(self, per_page: int = 25, page: int = 1) -> requests.Response:
        return self.request("clients", params={"per_page": per_page, "page": page})

    def get_client(self, client_id: str | int) -> requests.Response:
        return self.request(f"clients/{client_id}")

    def get_client_purchases(self, client_id: str | int, per_page: int = 25, page: int = 1) -> requests.Response:
        return self.request(f"clients/{client_id}/purchases", params={"per_page": per_page, "page": page})

    def get_sales(self, per_page: int = 25, page: int = 1) -> requests.Response:
        return self.request("sales", params={"per_page": per_page, "page": page})

    def get_products(self, page: int = 1, per_page: int = 25) -> requests.Response:
        return self.request("products", params={"page": page, "per_page": per_page})

    def get_leads(self, per_page: int = 25, page: int = 1) -> requests.Response:
        return self.request("leads", params={"per_page": per_page, "page": page})

    def get_deals(self, per_page: int = 25, page: int = 1) -> requests.Response:
        return self.request("deals", params={"per_page": per_page, "page": page})

    def get_lead_history(self, lead_id: str | int) -> requests.Response:
        return self.request(f"leads/{lead_id}/history")
