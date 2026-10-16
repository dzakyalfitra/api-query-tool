import json
import os
import sys
import time
from crm_client import CRMClient


def clean_input(prompt: str) -> str:
    """Prompt user and strip whitespace and Windows BOM characters."""
    return input(prompt).strip().replace("﻿", "")


def get_int_input(prompt: str, default: int) -> int:
    """Prompt user for an integer, falling back to default on empty input or error."""
    val = clean_input(f"{prompt} [Default: {default}]: ")
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        print(f"  (Invalid number, using default: {default})")
        return default


def display_response(resp):
    """Format and print HTTP response details and JSON body."""
    print("\n" + "-" * 60)
    print(f"URL:    {resp.url}")
    print(f"Status: {resp.status_code} {resp.reason}")
    print("-" * 60)

    try:
        data = resp.json()
        formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
        print(formatted_json)
        return data
    except Exception:
        print(resp.text)
        return None


def maybe_save_output(data, endpoint_name: str):
    """Prompt the user if they'd like to save JSON output to a file."""
    if not data:
        return
    try:
        choice = clean_input("\nSave this output to a JSON file? (y/N): ").lower()
        if choice == "y":
            filename = f"{endpoint_name}_{int(time.time())}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Saved to: {os.path.abspath(filename)}")
    except (EOFError, KeyboardInterrupt):
        return


def main():
    client = CRMClient()

    while True:
        print("\n" + "=" * 60)
        print("                CRM API Terminal Explorer")
        print("=" * 60)
        print(f"Base URL: {client.base_url}")

        if client.is_configured():
            print("Auth:     [OK] X-App-Key and X-Secret-Key loaded from .env")
        else:
            print("Auth:     [!] WARNING: Real keys not set in .env")
            print("          Please edit .env with your real X-App-Key and X-Secret-Key!")

        print("\nSelect an endpoint to query:")
        print("  1. Organizations List        (GET /organizations)")
        print("  2. Organization Details      (GET /organizations/{id})")
        print("  3. Clients List              (GET /clients)")
        print("  4. Client Details            (GET /clients/{id})")
        print("  5. Client Purchases          (GET /clients/{id}/purchases)")
        print("  6. Sales List                (GET /sales)")
        print("  7. Products List             (GET /products)")
        print("  8. Leads List                (GET /leads)")
        print("  9. Deals List                (GET /deals)")
        print(" 10. Lead History              (GET /leads/{id}/history)")
        print(" 11. Custom Endpoint Path")
        print(" 12. Open Web Dashboard        (Streamlit)")
        print("  0. Exit")

        try:
            choice = clean_input("\nEnter choice (0-12): ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting. Happy querying!")
            sys.exit(0)

        if choice == "0":
            print("\nExiting. Happy querying!")
            sys.exit(0)

        try:
            resp = None
            endpoint_name = "output"

            if choice == "1":
                endpoint_name = "organizations"
                per_page = get_int_input("Enter per_page", default=25)
                page = get_int_input("Enter page", default=1)
                print("\nSending request...")
                resp = client.get_organizations(per_page=per_page, page=page)

            elif choice == "2":
                endpoint_name = "organization_detail"
                org_id = clean_input("Enter Organization ID [e.g. 8509]: ") or "8509"
                per_page = get_int_input("Enter per_page", default=25)
                print("\nSending request...")
                resp = client.get_organization(org_id=org_id, per_page=per_page)

            elif choice == "3":
                endpoint_name = "clients"
                per_page = get_int_input("Enter per_page", default=25)
                page = get_int_input("Enter page", default=1)
                print("\nSending request...")
                resp = client.get_clients(per_page=per_page, page=page)

            elif choice == "4":
                endpoint_name = "client_detail"
                client_id = clean_input("Enter Client ID [e.g. 6920]: ") or "6920"
                print("\nSending request...")
                resp = client.get_client(client_id=client_id)

            elif choice == "5":
                endpoint_name = "client_purchases"
                client_id = clean_input("Enter Client ID [e.g. 6920]: ") or "6920"
                per_page = get_int_input("Enter per_page", default=25)
                print("\nSending request...")
                resp = client.get_client_purchases(client_id=client_id, per_page=per_page)

            elif choice == "6":
                endpoint_name = "sales"
                per_page = get_int_input("Enter per_page", default=25)
                page = get_int_input("Enter page", default=1)
                print("\nSending request...")
                resp = client.get_sales(per_page=per_page, page=page)

            elif choice == "7":
                endpoint_name = "products"
                page = get_int_input("Enter page", default=1)
                per_page = get_int_input("Enter per_page", default=25)
                print("\nSending request...")
                resp = client.get_products(page=page, per_page=per_page)

            elif choice == "8":
                endpoint_name = "leads"
                per_page = get_int_input("Enter per_page", default=25)
                page = get_int_input("Enter page", default=1)
                print("\nSending request...")
                resp = client.get_leads(per_page=per_page, page=page)

            elif choice == "9":
                endpoint_name = "deals"
                per_page = get_int_input("Enter per_page", default=25)
                page = get_int_input("Enter page", default=1)
                print("\nSending request...")
                resp = client.get_deals(per_page=per_page, page=page)

            elif choice == "10":
                endpoint_name = "lead_history"
                lead_id = clean_input("Enter Lead ID [e.g. 36]: ") or "36"
                print("\nSending request...")
                resp = client.get_lead_history(lead_id=lead_id)

            elif choice == "11":
                custom_path = clean_input("Enter endpoint path (e.g. users or tasks): ")
                per_page = get_int_input("Enter per_page", default=25)
                page = get_int_input("Enter page", default=1)
                endpoint_name = custom_path.replace("/", "_")
                print("\nSending request...")
                resp = client.request(custom_path, params={"per_page": per_page, "page": page})

            elif choice == "12":
                print("\nLaunching Web Dashboard in your browser (Ctrl+C to return to menu)...")
                streamlit_exe = os.path.join(os.path.dirname(sys.executable), "streamlit.exe")
                if not os.path.exists(streamlit_exe):
                    streamlit_exe = "streamlit"
                try:
                    import subprocess
                    subprocess.run([streamlit_exe, "run", "app.py"])
                except KeyboardInterrupt:
                    print("\nDashboard stopped.")
                except Exception as e:
                    print(f"Error launching dashboard: {e}")
                continue

            else:
                print("Invalid choice, please select between 0 and 12.")
                continue

            if resp is not None:
                data = display_response(resp)
                maybe_save_output(data, endpoint_name)

        except KeyboardInterrupt:
            print("\nOperation cancelled.")
        except Exception as e:
            print(f"\n[Error occurred]: {e}")

        try:
            clean_input("\nPress Enter to return to menu...")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting. Happy querying!")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)
