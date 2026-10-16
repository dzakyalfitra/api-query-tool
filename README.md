# CRM API Explorer

Tool to query and explore the iLogo CRM API (`https://crm.ilogo.id/api/v1`).

## Setup

1. **Virtual Environment (`.venv`)**:
   Already created. To activate in PowerShell:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   *(Or run directly using `.\.venv\Scripts\python.exe`)*

2. **Configure Credentials in `.env`**:
   Open `.env` and fill in your actual credentials:
   ```env
   CRM_BASE_URL=https://crm.ilogo.id/api/v1
   CRM_APP_KEY=your_real_x_app_key
   CRM_SECRET_KEY=your_real_x_secret_key
   ```
   *(Note: `.env` is ignored by git to protect your keys).*

## Usage (Terminal)

Run the interactive terminal explorer:
```powershell
.\.venv\Scripts\python.exe main.py
```
or after activating `.venv`:
```powershell
python main.py
```

### Supported Endpoints
- **Organizations**: List (`/organizations`) & Details by ID (`/organizations/{id}`)
- **Clients**: List (`/clients`), Details (`/clients/{id}`), Purchases (`/clients/{id}/purchases`)
- **Sales**: List (`/sales`)
- **Products**: List (`/products`)
- **Leads**: List (`/leads`) & History by ID (`/leads/{id}/history`)
- **Deals**: List (`/deals`)
- **Custom**: Enter any path directly (e.g. `users`, `tasks`)

Each query lets you customize `per_page` (defaults to 25) and `page`, and optionally export the response to a JSON file.
