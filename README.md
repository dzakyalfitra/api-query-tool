# CRM API Explorer

Tool to query and explore the iLogo CRM API (`https://crm.ilogo.id/api/v1`).

## Setup

1. **Virtual Environment (`.venv`)**:
   Already created. To activate in PowerShell:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Configure Credentials in `.env`**:
   Store your actual credentials in `.env`:
   ```env
   CRM_BASE_URL=https://crm.ilogo.id/api/v1
   CRM_APP_KEY=your_actual_x_app_key
   CRM_SECRET_KEY=your_actual_x_secret_key
   ```
   *(Note: `.env` is ignored by git to protect your keys).*

---

## 1. Web Dashboard (Recommended)

Launch the interactive web dashboard with table views, collapsible JSON tree, and 1-click export:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```
*(Or after activating `.venv`: `streamlit run app.py`)*

### Dashboard Features:
- **Interactive Tables**: Sort, filter, search, and resize columns on returned lists.
- **Collapsible JSON View**: Inspect nested response fields without terminal clutter.
- **1-Click Export**: Download any query result as formatted `.json` or `.csv`.
- **Configurable Pagination**: Adjust `per_page` (default: 25) and `page` in the sidebar.

---

## 2. Terminal Explorer

For quick testing without opening a browser:
```powershell
.\.venv\Scripts\python.exe main.py
```

### Supported Endpoints:
- **Organizations**: List (`/organizations`) & Details (`/organizations/{id}`)
- **Clients**: List (`/clients`), Details (`/clients/{id}`), Purchases (`/clients/{id}/purchases`)
- **Sales**: List (`/sales`)
- **Products**: List (`/products`)
- **Leads**: List (`/leads`) & History (`/leads/{id}/history`)
- **Deals**: List (`/deals`)
- **Custom Endpoint**: Query any custom path directly
