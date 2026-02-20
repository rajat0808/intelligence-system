# Inventory Intelligence Platform

FastAPI service for tracking inventory risk, surfacing danger alerts, and sending notifications. It combines rules-based aging logic with a simple ML-style risk score to flag items that need attention.

## Features
- Store danger dashboard with capital at risk by store
- Search API with danger filters and alert-only views
- Inventory Search UI with thumbnail click-to-preview image popout
- Daily scheduler that records snapshots and triggers alerts
- WhatsApp alert integration (configurable)
- SQLite by default, SQLAlchemy models throughout

## Project layout
- `app/` - FastAPI application package
  - `main.py` - entrypoint and startup wiring
  - `core/` - logging, scheduler, security, constants
  - `database/` - engine, session, base
  - `models/` - SQLAlchemy models
  - `schemas/` - Pydantic request/response models
  - `routers/` - API routes (health, ingest, dashboard, search, ml, alerts, whatsapp)
  - `services/` - ingestion, ML, alerts, dashboard aggregation
  - `ml/` - feature engineering, training, evaluation
  - `templates/` - HTML templates
  - `static/` - CSS assets
- `scripts/` - seed data, scheduler runner, model retraining, excel import
- `tests/` - unit tests
- `docker/` - Dockerfile and compose

## Quick start (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt

# Run from the repo root.
uvicorn app.main:app --reload
```

Then open:
- `http://localhost:8000/health` for health
- `http://localhost:8000/dashboard/` for the dashboard

## Testing
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## Docker
```powershell
docker compose -f docker/docker-compose.yml up --build
```

## Packaging (optional)
```powershell
python -m pip install -e .
```

## Configuration
Settings load from environment variables or a `.env` file in the repo root.
Copy `.env.example` to `.env` and update values as needed.

Production requirements:
- Set `ENVIRONMENT=production`.
- Set `DASHBOARD_SESSION_SECRET` (or `JWT_SECRET`) to a stable value, otherwise dashboard
  sessions reset on every restart.

Required for WhatsApp alerts:
- `WHATSAPP_API_URL`
- `WHATSAPP_ACCESS_TOKEN`
- `FOUNDER_PHONE`
- `CO_FOUNDER_PHONE`

Optional for sending product images in alerts:
- `WHATSAPP_MEDIA_BASE_URL` (public base URL used to convert relative image paths like `/static/images/ABC.jpg` into absolute URLs)

WhatsApp Cloud API example:
```text
WHATSAPP_API_URL=https://graph.facebook.com/v19.0/<PHONE_NUMBER_ID>/messages
WHATSAPP_ACCESS_TOKEN=<ACCESS_TOKEN>
WHATSAPP_MEDIA_BASE_URL=https://your-domain.com
FOUNDER_PHONE=15551234567
CO_FOUNDER_PHONE=15551234568
```

Optional defaults (see `app/config.py`):
- `DATABASE_URL` (default: `sqlite:///./inventory.db`)
- `ML_ALERT_THRESHOLD` (default: `0.75`)
- `ENVIRONMENT`, `APP_NAME`, `FOUNDER_API_KEY`
- Dashboard login:
  - `DASHBOARD_USERNAME`
  - `DASHBOARD_PASSWORD` (plaintext) or `DASHBOARD_PASSWORD_HASH` + `DASHBOARD_PASSWORD_SALT`
  - `DASHBOARD_SESSION_SECRET`
- Scheduler: `SCHEDULER_ENABLED`, `SCHEDULER_RUN_AFTER`, `SCHEDULER_POLL_SECONDS`,
`SCHEDULER_HEARTBEAT_SECONDS`, `SCHEDULER_STALE_SECONDS`, `SCHEDULER_RETRY_SECONDS`,
`SCHEDULER_MAX_RETRIES`, `SCHEDULER_TZ`

## API endpoints
- `GET /health` - service status
- `GET /dashboard/` - dashboard UI
- `GET /dashboard/store-danger-summary` - store-wise danger capital summary
- `GET /search/inventory` - search inventory
  - query params: `query`, `department` (comma-separated), `store_id`, `danger` (EARLY|HIGH|CRITICAL), `alert_only`
- `POST /ingest/excel` - trigger Excel import; body: `{"path":"datasource/daily_update.xlsx","sheets":["daily_update"],"dry_run":false}`
- `GET /products/{style_code}` - product detail with current price, days active, and price history
- `POST /products/price` - upsert product price by style code (creates if missing)
- `POST /whatsapp/send` - send a WhatsApp message; body: `{"message":"...","phone":"15551234567","image_url":"https://.../item.jpg"}`
- `POST /ml/predict` - ML risk score; body: `{"category":"dress","quantity":10,"item_mrp":4500,"lifecycle_start_date":"2025-01-01"}`
- `GET /ml/inventory` - ML risk scores from datasource (filters: `store_id`, `product_id`, `category`, `min_risk`, `limit`)
- `POST /alerts/run` - run alert workflow using datasource (query: `send_notifications=true|false`)

## Database notes
The API expects these tables to be populated:
- `stores`
- `products`
- `inventory`
- `job_logs` (scheduler state and crash recovery)

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
- `daily_update`: `store_id`, `supplier_name`, `stock_days`, `style_code`, `department_name`, `category_name`, `item_mrp`, `image` (optional)
- `stores`: `id` (optional), `name`, `city`
- `products`: `id` (optional), `store_id`, `style_code`, `barcode`, `article_name`, `category`, `department_name` (optional), `supplier_name`, `image` (optional), `mrp`
- `inventory`: `id` (optional), `store_id`, `product_id`, `quantity`, `item_mrp`, `current_price`, `lifecycle_start_date` (YYYY-MM-DD)

Images:
- Place product images in `app/static/images/` (e.g. `ABC123.jpg`).
- If `image` is blank, the importer auto-matches by `style_code` or `barcode` to a file in `app/static/images/`.
- If `image` is provided, it can be a filename like `ABC123.jpg` (no URL required).
- Embedded images in the `image` column are extracted on import and saved to `app/static/images/`.

Dashboard image preview:
- In **Inventory Search**, click a thumbnail in the **Image** column to open a larger preview.
- Close preview by clicking outside the image, pressing `Esc`, or using the close button.

Template:
- Copy `datasource/daily_update_template.xlsx` to `datasource/daily_update.xlsx` and fill it daily.

Config (see `app/config.py`):
- `EXCEL_AUTO_IMPORT` (default: `true`)
- `EXCEL_DATASOURCE_DIR` (default: `datasource`)
- `EXCEL_POLL_SECONDS` (default: `10`)
- `EXCEL_IMPORT_SHEETS` (optional, comma-separated)
- `EXCEL_DAILY_UPDATE_SHEET_ALIASES` (optional, comma-separated)
- `EXCEL_CREATE_MISSING_STORES` (default: `false`)

Manual run (optional):
```powershell
python scripts/import_excel.py --path .\datasource\daily_update.xlsx
```

Seed sample data (optional):
```powershell
python scripts/seed_data.py
```

## Daily scheduler
The scheduler runs as a standalone process (separate from FastAPI) and persists state in `job_logs`:
```powershell
python scripts/run_scheduler.py
```

Crash recovery: the scheduler records each run in `job_logs`, updates heartbeats while running, and retries
stale or failed runs with backoff while preventing duplicate executions.

The job runs once per day after `SCHEDULER_RUN_AFTER` and computes:
- aging status
- rule-based danger level
- decision engine output
- ML risk score

It writes to `daily_snapshots`, logs ML output in `risk_logs`, and records alert delivery in `alerts`.

## ML risk scoring (trained)
`app/ml/predict.py` uses a trained classifier when a model file is present, falling back to the heuristic only if no model is available.

Training sources:
- `daily_snapshots` + `sales` (preferred): labels items that sell within a future horizon.
- `inventory` + recent `sales` (fallback): labels items sold in the last horizon window.

Train and export a model:
```powershell
python -m app.ml.train --horizon-days 30
# or: python scripts/retrain_model.py --horizon-days 30
```

This writes:
- `app/ml/artifacts/inventory_risk_model.joblib` (model)
- `app/ml/artifacts/inventory_risk_metadata.json` (metrics and training metadata)

Override paths with:
- `ML_MODEL_PATH`
- `ML_MODEL_METADATA_PATH`
