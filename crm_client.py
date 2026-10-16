import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class CRMClient:
    def __init__(self, base_url: str = None, app_key: str = None, secret_key: str = None):
        self.base_url = (base_url or os.getenv("CRM_BASE_URL", "https://crm.ilogo.id/api/v1")).rstrip("/")
        self.app_key = app_key or os.getenv("CRM_APP_KEY", "")
        self.secret_key = secret_key or os.getenv("CRM_SECRET_KEY", "")

    def is_configured(self) -> bool:
        """Check if API keys are set and not placeholder values."""
        if not self.app_key or not self.secret_key:
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
        """Send a GET request to the CRM API."""
        endpoint = endpoint.strip("/")
        url = f"{self.base_url}/{endpoint}"
        # Filter out None values in params
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        return requests.get(url, headers=self.get_headers(), params=clean_params, timeout=timeout)

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
