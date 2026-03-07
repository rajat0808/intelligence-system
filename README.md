# Inventory Intelligence Platform

FastAPI service for inventory aging intelligence, transfer guidance, risk scoring, and multi-channel alert delivery (Telegram/WhatsApp), with automatic daily PDF reporting.

## What This System Does

- Ingests inventory updates from Excel (`daily_update.xlsx`) automatically or on demand.
- Computes aging status per item (`HEALTHY`, `TRANSFER`, `RR_TT`, `VERY_DANGER`).
- Computes danger level (`EARLY`, `HIGH`, `CRITICAL`) from lifecycle age.
- Generates alert candidates using rule-based danger + ML risk thresholds.
- Sends alerts via Telegram and optional WhatsApp.
- Generates a daily PDF report (`daily_alert_report.pdf`) with 50 alerts and product images.
- Hosts a dashboard, search APIs, product APIs, ML APIs, and webhook endpoints.

## Tech Stack

- Python 3.10+
- FastAPI + Uvicorn
- SQLAlchemy
- SQLite (default)
- OpenPyXL (Excel ingestion)
- Scikit-learn + Joblib (ML model)
- Pillow + ReportLab (image/PDF reporting)
- Requests (Telegram)

## Project Structure

```text
app/
  core/          # rules, security, logging, constants, scheduler helpers
  database/      # SQLAlchemy engine/session/base
  models/        # ORM models
  routers/       # API routes
  schemas/       # request/response schemas
  services/      # alerting, notifications, ingestion, reporting, ML
  scheduler/     # durable daily scheduler
  templates/     # dashboard/login HTML
  static/        # CSS/JS/images
scripts/         # operational scripts (start/stop/import/scheduler/report)
datasource/      # Excel input files + templates + report JSON samples
tests/           # test suite
```

## Quick Start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

Start server:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_server.ps1
```

Stop server:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop_server.ps1
```

Direct Uvicorn run (alternative):

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

## First URLs

- Health: `http://127.0.0.1:8000/health`
- Dashboard: `http://127.0.0.1:8000/dashboard/`
- Login: `http://127.0.0.1:8000/login`

## Configuration

Configuration is read from environment variables and `.env` (unless `IIP_DISABLE_DOTENV=1`).

### Core

- `APP_NAME`
- `ENVIRONMENT` (`local` or `production`)
- `DATABASE_URL` (default `sqlite:///./inventory.db`)
- `LOG_LEVEL`, `LOG_JSON`

### Security and Auth

- API/JWT
  - `FOUNDER_API_KEY`
  - `API_KEYS` (comma-separated)
  - `API_KEY_HEADER`
  - `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_AUDIENCE`, `JWT_ISSUER`, `JWT_REQUIRED`
- Dashboard session/login
  - `DASHBOARD_USERNAME`
  - `DASHBOARD_PASSWORD` OR `DASHBOARD_PASSWORD_HASH` + `DASHBOARD_PASSWORD_SALT`
  - `DASHBOARD_PBKDF2_ROUNDS`
  - `DASHBOARD_SESSION_SECRET`
  - `DASHBOARD_SESSION_COOKIE`

Auth behavior:

- If no API keys/JWT are configured, API key auth is effectively open.
- If keys/JWT are configured, protected endpoints require valid auth.
- Dashboard login is required only when dashboard credentials are configured.

### Notifications

- Telegram
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `TELEGRAM_ALERT_TEMPLATE` (optional, include `{message}`)
  - `TELEGRAM_FALLBACK_IMAGE` (default `/static/sindh-logo.png`)
- WhatsApp
  - `WHATSAPP_API_URL`
  - `WHATSAPP_ACCESS_TOKEN`
  - `WHATSAPP_MEDIA_BASE_URL`
  - `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
  - `WHATSAPP_DEFAULT_COUNTRY_CODE`
  - `WHATSAPP_NOTIFICATIONS_ENABLED`
- Alert recipients
  - `FOUNDER_PHONE`
  - `CO_FOUNDER_PHONE`
- Legacy prefix mode
  - `ALERT_MESSAGE_PREFIX=#` (optional, prepends `#` to outgoing messages)

### Alert and ML Controls

- `ML_ALERT_THRESHOLD`
- `ML_ALERT_HIGH_THRESHOLD`
- `ML_ALERT_CRITICAL_THRESHOLD`
- `ML_MODEL_PATH`
- `ML_MODEL_METADATA_PATH`
- `ALERT_MIN_CAPITAL_VALUE`
- `ALERT_COOLDOWN_DAYS`
- `ALERT_MAX_PER_RECIPIENT_PER_RUN`
- `ALERT_ALWAYS_SEND`
- `LOW_STOCK_ALERT_THRESHOLD`

### Excel Auto-Import

- `EXCEL_AUTO_IMPORT`
- `EXCEL_DATASOURCE_DIR`
- `EXCEL_POLL_SECONDS`
- `EXCEL_IMPORT_SHEETS`
- `EXCEL_DAILY_UPDATE_SHEET_ALIASES`
- `EXCEL_CREATE_MISSING_STORES`

### Scheduler

- `SCHEDULER_ENABLED`
- `SCHEDULER_RUN_AFTER`
- `SCHEDULER_POLL_SECONDS`
- `SCHEDULER_HEARTBEAT_SECONDS`
- `SCHEDULER_STALE_SECONDS`
- `SCHEDULER_RETRY_SECONDS`
- `SCHEDULER_MAX_RETRIES`
- `SCHEDULER_TZ` (`local` or `utc`)
- `SCHEDULER_RUN_ON_STARTUP`

## Data Ingestion

### Excel Entry Points

- Auto-import watcher reads new/updated `.xlsx` files in `datasource/`.
- Manual import endpoint: `POST /ingest/excel`
- Manual import script: `scripts/import_excel.py`

### Main Workbook

Use:

- `datasource/daily_update_template.xlsx`
- save a working file as `datasource/daily_update.xlsx`

Expected `daily_update` columns:

- `store_id`
- `supplier_name`
- `stock_days`
- `style_code`
- `department_name`
- `category_name` (mapped to `category`)
- `item_mrp` (mapped to `mrp`)
- `image` (optional)

### Image Handling

- Place images in `app/static/images/`.
- Image column can be filename, relative path, absolute path, or URL.
- Embedded Excel images are extracted and stored automatically.
- If image is missing, importer tries matching by `style_code`/`barcode`.

## Aging and Danger Logic

### Aging Status (`classify_status`)

- `dress` and `dress material`
  - `<= 90`: `HEALTHY`
  - `<= 180`: `TRANSFER`
  - `<= 365`: `RR_TT`
  - `> 365`: `VERY_DANGER`
- `lehenga` (including variants like `LEHENGA BRIDAL`)
  - `<= 250`: `HEALTHY`
  - `<= 365`: `TRANSFER`
  - `> 365`: `VERY_DANGER`
- `saree`
  - `<= 365`: `HEALTHY`
  - `> 365`: `VERY_DANGER`

Unknown categories fall back to default category rules where `classify_status_with_default` is used in alert flow.

### Danger Level (`danger_level`)

- `>= 180 days`: `EARLY`
- `>= 250 days`: `HIGH`
- `>= 365 days`: `CRITICAL`

Danger level is separate from aging status.

### Transfer Hint

Transfer hints are computed by comparing same style across peer stores and selecting the best destination by:

- best status (`HEALTHY` preferred),
- lower age,
- lower quantity.

If no peer store has that style:  
`Transfer Hint: No peer-store data for this style yet.`

## Alert Pipeline

Triggered by:

- Rule-based danger (`RULE-HIGH`/`RULE-CRITICAL`), or
- ML thresholds (`ML-RISK-ELEVATED/HIGH/CRITICAL`)

Alert text includes:

- Category
- Department
- Style code
- Store
- Stock days / Age
- Aging status
- Capital locked
- Transfer hint

Dedup/cooldown:

- unique by day + type + category + recipient phone
- cooldown with `ALERT_COOLDOWN_DAYS`
- resend override with `force_resend=true` on `/alerts/run`

## Daily PDF Report

### Report Characteristics

- Output file: `daily_alert_report.pdf`
- Exactly 50 alerts per report (raises error if fewer)
- Layout:
  - text on left
  - image on right
  - clear spacing between alerts
  - automatic page breaks in same PDF
- Includes:
  - title
  - price/important data
  - store/source
  - stock days
  - aging status
  - transfer hint
  - image

### Generate with script

From DB:

```powershell
.\.venv\Scripts\python scripts\generate_daily_alert_report.py --output daily_alert_report.pdf
```

From JSON:

```powershell
.\.venv\Scripts\python scripts\generate_daily_alert_report.py --alerts-json datasource/alert_report_input_50.json --output daily_alert_report.pdf
```

Send report to Telegram:

```powershell
.\.venv\Scripts\python scripts\generate_daily_alert_report.py --send-telegram
```

### API PDF endpoint

- `GET /alerts/report/pdf`  
Returns the PDF file directly (`application/pdf`), no JSON body.

## API Reference

### Health

- `GET /health`

### Auth

- `GET /login`
- `POST /login`
- `POST /logout`

### Dashboard

- `GET /dashboard/`
- `GET /dashboard/store-danger-summary`
- `GET /dashboard/inventory-by-status`

### Search

- `GET /search/inventory`
  - query params: `query`, `department`, `store_id`, `danger`, `alert_only`

### Ingest

- `POST /ingest/excel`
  - body:
    ```json
    {
      "path": "datasource/daily_update.xlsx",
      "sheets": ["daily_update"],
      "dry_run": false
    }
    ```

### Alerts

- `POST /alerts/run`
  - query params:
    - `send_notifications=true|false`
    - `force_resend=true|false`
    - `generate_pdf_report=true|false`
    - `send_pdf_to_telegram=true|false`
- `GET /alerts/report/pdf`

### Products

- `GET /products/{style_code}?store_id=...`
- `POST /products/price`

### ML

- `POST /ml/predict`
- `GET /ml/status`
- `GET /ml/inventory`

### WhatsApp

- `POST /whatsapp/send`
- `POST /whatsapp/send-template`
- `GET /whatsapp/webhook`
- `POST /whatsapp/webhook`

## Common API Examples

### Run alerts without sending channels, but generate PDF

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/alerts/run?send_notifications=false&generate_pdf_report=true&send_pdf_to_telegram=false"
```

### Force resend (refresh messages with latest aging status text)

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/alerts/run?force_resend=true"
```

### Download PDF directly

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/alerts/report/pdf" -OutFile ".\\daily_alert_report.pdf"
```

## Scheduler Behavior

- Scheduler starts with app when `SCHEDULER_ENABLED=true`.
- Optional startup run if `SCHEDULER_RUN_ON_STARTUP=true`.
- Durable run state tracked in `job_logs`.
- Retries stale/failed runs with backoff.
- Runs alert workflow + PDF report generation.

Standalone scheduler:

```powershell
.\.venv\Scripts\python scripts\run_scheduler.py
```

One run and exit:

```powershell
.\.venv\Scripts\python scripts\run_scheduler.py --run-once
```

## ML Training

Train or retrain model:

```powershell
.\.venv\Scripts\python -m app.ml.train --horizon-days 30
# or
.\.venv\Scripts\python scripts\retrain_model.py --horizon-days 30
```

Artifacts:

- `app/ml/artifacts/inventory_risk_model.joblib`
- `app/ml/artifacts/inventory_risk_metadata.json`

## Development Commands

Run tests:

```powershell
$env:IIP_DISABLE_DOTENV="1"
.\.venv\Scripts\python -m pytest
```

Lint:

```powershell
.\.venv\Scripts\python -m ruff check app scripts tests
```

## Docker

```powershell
docker compose -f docker/docker-compose.yml up --build
```

## Troubleshooting

### "Why are 2 tests skipped?"

`tests/test_predict_risk.py` intentionally skips two heuristic-monotonic tests when a trained model is available.  
Run with `-rs` to show skip reasons:

```powershell
.\.venv\Scripts\python -m pytest -rs
```

### "Alert showed no aging status"

Use latest code and rerun with:

```powershell
POST /alerts/run?force_resend=true
```

### "Transfer Hint says no peer-store data"

That style exists only in one store, so no peer destination is available for comparison.

### "PDF endpoint returns error about 50 alerts"

The report enforces exactly 50 alerts. Ensure inventory dataset can produce at least 50 rows.

## Production Notes

- Set `ENVIRONMENT=production`.
- Set stable `DASHBOARD_SESSION_SECRET` (or `JWT_SECRET`).
- Configure real credentials/tokens for Telegram/WhatsApp.
- Ensure `WHATSAPP_MEDIA_BASE_URL` points to a public host if sending image links.
- Keep `.env` out of source control.

## License

MIT (`LICENSE`).

