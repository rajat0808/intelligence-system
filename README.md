# Inventory Intelligence Platform

FastAPI service for tracking inventory risk, surfacing danger alerts, and sending notifications. It combines rules-based aging logic with a simple ML-style risk score to flag items that need attention.

## Features
- Store danger dashboard with capital at risk by store
- Search API with danger filters and alert-only views
- Nightly job that records daily snapshots and triggers alerts
- WhatsApp alert integration (configurable)
- SQLite by default, SQLAlchemy models throughout

## Project layout
- `main.py` - FastAPI app and route wiring
- `api/` - HTTP routes (dashboard, search, whatsapp)
- `intelligence/` - rule logic and decision engine
- `ml/` - heuristic risk scoring
- `models/` - SQLAlchemy models
- `scheduler/` - nightly job runner
- `services/` - alerting and integrations

## Quick start (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt

# Run from the repo root.
uvicorn app.main:app --reload
```

Then open:
- `http://localhost:8000/` for health
- `http://localhost:8000/dashboard/` for the dashboard

## Configuration
Settings load from environment variables or a `.env` file in the repo root.
Copy `.env.example` to `.env` and update values as needed.

Required for WhatsApp alerts:
- `WHATSAPP_API_URL`
- `WHATSAPP_ACCESS_TOKEN`
- `FOUNDER_PHONE`
- `CO_FOUNDER_PHONE`

Optional defaults (see `config.py`):
- `DATABASE_URL` (default: `sqlite:///./inventory.db`)
- `ML_ALERT_THRESHOLD` (default: `0.75`)
- `ENVIRONMENT`, `APP_NAME`, `FOUNDER_API_KEY`

## API endpoints
- `GET /` - service status
- `GET /dashboard/` - dashboard UI
- `GET /dashboard/store-danger-summary` - store-wise danger capital summary
- `GET /search/inventory` - search inventory
  - query params: `query`, `store_id`, `danger` (EARLY|HIGH|CRITICAL), `alert_only`
- `POST /whatsapp/send` - stub endpoint (echoes message)

## Database notes
The API expects these tables to be populated:
- `stores`
- `products`
- `inventory`

The dashboard uses `inventory` only. Search uses `products` + `inventory`.
Running the app creates tables automatically via `Base.metadata.create_all`, but you must insert data yourself.

## Excel import (auto)
The FastAPI app watches `datasource/` and auto-imports any new or updated `.xlsx` file.
- Drop or overwrite a workbook in `datasource/`.
- The importer waits for the file to be stable, then upserts rows.
- Files starting with `~$` are ignored.
- Keep the Excel file closed after saving so it can be read.
- The folder is created automatically if it does not exist.

Sheets (case-insensitive):
- `stores`: `id` (optional), `name`, `city`
- `products`: `id` (optional), `store_id`, `style_code`, `barcode`, `article_name`, `category`, `supplier_name`, `mrp`
- `inventory`: `id` (optional), `store_id`, `product_id`, `quantity`, `cost_price`, `current_price`, `lifecycle_start_date` (YYYY-MM-DD)

Template:
- Copy `datasource/daily_update_template.xlsx` to `datasource/daily_update.xlsx` and fill it daily.

Config (see `config.py`):
- `EXCEL_AUTO_IMPORT` (default: `true`)
- `EXCEL_DATASOURCE_DIR` (default: `datasource`)
- `EXCEL_POLL_SECONDS` (default: `10`)
- `EXCEL_IMPORT_SHEETS` (optional, comma-separated)

Manual run (optional):
```powershell
python scripts/import_excel.py --path .\datasource\daily_update.xlsx
```

## Nightly job
`scheduler/nightly_job.py` computes:
- aging status
- rule-based danger level
- decision engine output
- ML risk score

It writes a row to `daily_snapshots` and sends WhatsApp alerts for HIGH/CRITICAL or high ML risk, recording delivery logs in `delivery_logs`.

## ML risk scoring (heuristic)
The model in `ml/predict.py` is a lightweight heuristic that returns a 0..1 score based on age, stock value, and category. It is a placeholder you can replace with a trained model.
