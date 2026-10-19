# CRM API Explorer

Tool to query and explore the CRM API.

---

## Quick Start (Easiest)

Simply double-click **`run.bat`** (or run `.\run.bat` in terminal):

```text
======================================================
              CRM API Explorer Launcher
======================================================

  [1] Web Dashboard (Default - opens in browser)
  [2] Terminal Explorer
  [0] Exit

Select an option [Default: 1]:
```

- **Press Enter** (or type `1`): Launches the Streamlit Web Dashboard in your browser.
- **Type `2`**: Launches the interactive Terminal Explorer.

---

## Configuration (`.env`)

Credentials are automatically loaded from `.env`:
```env
CRM_BASE_URL=https://your-crm-domain.com/api/v1
CRM_APP_KEY=your_actual_x_app_key
CRM_SECRET_KEY=your_actual_x_secret_key
```
*(Note: `.env` is ignored by git to protect your keys).*

---

## 1. Web Dashboard Features (`app.py`)

- **Interactive Tables**: Sort, filter, search, and resize columns on returned lists.
- **🔗 Entity Deep Inspector & Breadcrumbs**: Click through linked entities (`🏢 Organizations`, `👤 Clients`, `🛍️ Purchases`, `📜 Lead Histories`) directly without manual copy-pasting or losing navigation context.
- **Collapsible JSON Tree**: Inspect nested response fields without terminal clutter.
- **1-Click Export**: Download any query result as formatted `.json` or `.csv`.
- **Configurable Pagination**: Adjust `per_page` (default: 25) and `page` in the sidebar or use table buttons.
Manual command:
```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

---

## 2. Terminal Explorer (`main.py`)

For quick command-line querying without opening a browser:
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
- **Option 12**: Launch the Web Dashboard directly from within the terminal

---

## 3. Running Automated Tests

Run the zero-dependency test suite (17 unit and headless integration tests):
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
Tests run hermetically in $<2$ seconds without burning API rate limits.
