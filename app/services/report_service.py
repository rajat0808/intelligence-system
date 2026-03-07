import logging
from io import BytesIO
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image, ImageOps, UnidentifiedImageError
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.core.constants import PROJECT_ROOT, STATIC_DIR
from app.core.aging_rules import classify_status_with_default
from app.database import SessionLocal
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.stores import Store
from app.services.alert_service import build_transfer_hint
from app.services.channels.telegram_service import send_telegram_document

logger = logging.getLogger(__name__)

DEFAULT_REPORT_NAME = "daily_alert_report.pdf"
ALERTS_PER_PDF = 50
_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
_DEFAULT_FALLBACK_IMAGE = STATIC_DIR / "sindh-logo.png"
_PAGE_WIDTH, _PAGE_HEIGHT = letter
_PAGE_MARGIN = 36
_ROW_HEIGHT = 130
_ROW_GAP = 10
_ROW_PADDING = 8
_IMAGE_WIDTH = 122
_IMAGE_HEIGHT = 108


def _format_currency(value: Any) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value or "N/A")
    return "Rs {:,.0f}".format(amount)


def _format_site(store_id: Any, store_name: Any, store_city: Any) -> str:
    store_label = "Store {}".format(store_id if store_id is not None else "N/A")
    if str(store_name or "").strip():
        store_label = "{} ({})".format(store_label, str(store_name).strip())
    if str(store_city or "").strip():
        store_label = "{}, {}".format(store_label, str(store_city).strip())
    return store_label


def _coerce_alert(alert: Mapping[str, Any]) -> dict[str, str]:
    return {
        "title": str(alert.get("title") or "Unknown Product").strip(),
        "price": str(alert.get("price") or "N/A").strip(),
        "site": str(alert.get("site") or "Unknown Source").strip(),
        "store": str(alert.get("store") or "").strip(),
        "stock_days": str(alert.get("stock_days") or "").strip(),
        "aging_status": str(alert.get("aging_status") or "").strip(),
        "transfer_hint": str(alert.get("transfer_hint") or "").strip(),
        "image": str(alert.get("image") or "").strip(),
    }


def _normalize_alerts(
    alerts: Sequence[Mapping[str, Any]],
    *,
    expected_count: int = ALERTS_PER_PDF,
) -> list[dict[str, str]]:
    normalized_alerts = [_coerce_alert(alert) for alert in alerts]
    if len(normalized_alerts) < expected_count:
        raise ValueError(
            "Expected at least {} alerts, received {}.".format(
                expected_count,
                len(normalized_alerts),
            )
        )
    return normalized_alerts[:expected_count]


def _find_static_image_by_stem(image_value: str) -> Path | None:
    image_stem = Path(str(image_value or "").strip()).stem.strip()
    if not image_stem:
        return None

    images_dir = STATIC_DIR / "images"
    if not images_dir.exists():
        return None

    for extension in _IMAGE_EXTENSIONS:
        candidate = images_dir / "{}{}".format(image_stem, extension)
        if candidate.exists() and candidate.is_file():
            return candidate

    image_stem_lower = image_stem.lower()
    try:
        for image_path in images_dir.iterdir():
            if not image_path.is_file():
                continue
            if image_path.suffix.lower() not in _IMAGE_EXTENSIONS:
                continue
            if image_path.stem.lower() == image_stem_lower:
                return image_path
    except OSError:
        return None
    return None


def resolve_image_path(image_value: Any) -> Path | None:
    raw_value = str(image_value or "").strip()
    if not raw_value:
        return _DEFAULT_FALLBACK_IMAGE if _DEFAULT_FALLBACK_IMAGE.exists() else None

    normalized = raw_value.replace("\\", "/").strip()
    candidates: list[Path] = []

    if normalized.startswith("/static/"):
        candidates.append(PROJECT_ROOT / "app" / normalized.lstrip("/"))
    elif normalized.startswith("static/"):
        candidates.append(PROJECT_ROOT / "app" / normalized)
    elif normalized.startswith("images/"):
        candidates.append(STATIC_DIR / normalized.removeprefix("images/"))
    else:
        candidate = Path(raw_value)
        if candidate.is_absolute():
            candidates.append(candidate)
        else:
            candidates.append(PROJECT_ROOT / raw_value.lstrip("/\\"))
            candidates.append(STATIC_DIR / "images" / raw_value)

    for candidate_path in candidates:
        if candidate_path.exists() and candidate_path.is_file():
            return candidate_path

    matched_static_image = _find_static_image_by_stem(normalized)
    if matched_static_image is not None:
        return matched_static_image

    if _DEFAULT_FALLBACK_IMAGE.exists():
        return _DEFAULT_FALLBACK_IMAGE
    return None


def _draw_image(
    pdf_canvas: canvas.Canvas,
    *,
    image_path: Path | None,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    if image_path is None:
        pdf_canvas.setFillColor(colors.HexColor("#F3F4F6"))
        pdf_canvas.rect(x, y, width, height, stroke=0, fill=1)
        pdf_canvas.setFillColor(colors.HexColor("#6B7280"))
        pdf_canvas.setFont("Helvetica", 8)
        pdf_canvas.drawCentredString(x + (width / 2), y + (height / 2), "No image")
        return

    try:
        with Image.open(image_path) as image_file:
            rgb_image = image_file.convert("RGB")
            fitted_image = ImageOps.fit(
                rgb_image,
                (int(width), int(height)),
                method=Image.Resampling.LANCZOS,
            )
            image_buffer = BytesIO()
            fitted_image.save(image_buffer, format="JPEG", quality=90)
            image_buffer.seek(0)
            pdf_canvas.drawImage(
                ImageReader(image_buffer),
                x,
                y,
                width=width,
                height=height,
                preserveAspectRatio=False,
                mask="auto",
            )
    except (OSError, UnidentifiedImageError, ValueError):
        logger.warning("Could not render image for PDF: %s", image_path)
        pdf_canvas.setFillColor(colors.HexColor("#F3F4F6"))
        pdf_canvas.rect(x, y, width, height, stroke=0, fill=1)
        pdf_canvas.setFillColor(colors.HexColor("#6B7280"))
        pdf_canvas.setFont("Helvetica", 8)
        pdf_canvas.drawCentredString(x + (width / 2), y + (height / 2), "Image error")


def _truncate_line(text: str, *, font_name: str, font_size: int, max_width: float) -> str:
    if stringWidth(text, font_name, font_size) <= max_width:
        return text
    truncated = text
    while truncated and stringWidth(truncated + "...", font_name, font_size) > max_width:
        truncated = truncated[:-1]
    return (truncated + "...") if truncated else "..."


def _draw_text_block(
    pdf_canvas: canvas.Canvas,
    *,
    title: str,
    price: str,
    site: str,
    store: str = "",
    stock_days: str = "",
    aging_status: str = "",
    transfer_hint: str = "",
    x: float,
    y_top: float,
    width: float,
) -> None:
    max_title_lines = 2
    title_lines = simpleSplit(title, "Helvetica-Bold", 11, width) or ["Unknown Product"]
    if len(title_lines) > max_title_lines:
        title_lines = title_lines[:max_title_lines]
        title_lines[-1] = _truncate_line(
            title_lines[-1],
            font_name="Helvetica-Bold",
            font_size=11,
            max_width=width,
        )

    text_y = y_top
    pdf_canvas.setFillColor(colors.HexColor("#111827"))
    pdf_canvas.setFont("Helvetica-Bold", 11)
    for line in title_lines:
        pdf_canvas.drawString(x, text_y, line)
        text_y -= 13

    pdf_canvas.setFont("Helvetica", 10)
    pdf_canvas.setFillColor(colors.HexColor("#1F2937"))
    for line in simpleSplit("Price/Data: {}".format(price), "Helvetica", 10, width)[:2]:
        pdf_canvas.drawString(x, text_y, line)
        text_y -= 12

    pdf_canvas.setFillColor(colors.HexColor("#374151"))
    source_text = site
    if store:
        source_text = "{} | {}".format(store, site)
    for line in simpleSplit("Store/Source: {}".format(source_text), "Helvetica", 10, width)[:2]:
        pdf_canvas.drawString(x, text_y, line)
        text_y -= 12

    if stock_days or aging_status:
        stock_text = "Stock Days: {} | Aging: {}".format(
            stock_days or "N/A",
            aging_status or "N/A",
        )
        for line in simpleSplit(stock_text, "Helvetica", 10, width)[:2]:
            pdf_canvas.drawString(x, text_y, line)
            text_y -= 12

    if transfer_hint:
        pdf_canvas.setFillColor(colors.HexColor("#4B5563"))
        for line in simpleSplit(
            "Transfer Hint: {}".format(transfer_hint),
            "Helvetica",
            9,
            width,
        )[:2]:
            pdf_canvas.drawString(x, text_y, line)
            text_y -= 12


def _draw_alert_row(
    pdf_canvas: canvas.Canvas,
    *,
    alert: Mapping[str, str],
    x: float,
    y_top: float,
    width: float,
    height: float,
) -> None:
    y_bottom = y_top - height

    pdf_canvas.setStrokeColor(colors.HexColor("#D1D5DB"))
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.roundRect(x, y_bottom, width, height, 4, stroke=1, fill=1)

    image_x = x + width - _ROW_PADDING - _IMAGE_WIDTH
    image_y = y_bottom + ((height - _IMAGE_HEIGHT) / 2)
    text_x = x + _ROW_PADDING
    text_width = width - (_IMAGE_WIDTH + (_ROW_PADDING * 3))
    text_y_top = y_top - _ROW_PADDING - 3

    _draw_text_block(
        pdf_canvas,
        title=alert["title"],
        price=alert["price"],
        site=alert["site"],
        store=alert.get("store", ""),
        stock_days=alert.get("stock_days", ""),
        aging_status=alert.get("aging_status", ""),
        transfer_hint=alert.get("transfer_hint", ""),
        x=text_x,
        y_top=text_y_top,
        width=text_width,
    )
    _draw_image(
        pdf_canvas,
        image_path=resolve_image_path(alert["image"]),
        x=image_x,
        y=image_y,
        width=_IMAGE_WIDTH,
        height=_IMAGE_HEIGHT,
    )


def build_alerts_from_database(*, limit: int = ALERTS_PER_PDF) -> list[dict[str, str]]:
    db = SessionLocal()
    today = date.today()
    try:
        rows = db.execute(
            select(
                Product.article_name.label("article_name"),
                Product.style_code.label("style_code"),
                Product.category.label("category"),
                Product.mrp.label("mrp"),
                Product.image_url.label("image_url"),
                Store.id.label("store_id"),
                Store.name.label("store_name"),
                Store.city.label("store_city"),
                Inventory.quantity.label("quantity"),
                Inventory.lifecycle_start_date.label("lifecycle_start_date"),
            )
            .join(Product, Product.id == Inventory.product_id)
            .outerjoin(Store, Store.id == Inventory.store_id)
            .order_by(Inventory.lifecycle_start_date.asc(), Inventory.quantity.desc())
        ).all()
    finally:
        db.close()

    style_store_index: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        style_code = str(row.style_code or "").strip()
        if not style_code:
            continue
        lifecycle_start = row.lifecycle_start_date or today
        age_days = max(0, (today - lifecycle_start).days)
        aging_status = classify_status_with_default(row.category, age_days)
        style_store_index.setdefault(style_code, []).append(
            {
                "store_id": row.store_id,
                "store_name": row.store_name,
                "store_city": row.store_city,
                "age_days": age_days,
                "status": aging_status,
                "quantity": row.quantity or 0,
            }
        )

    alerts: list[dict[str, str]] = []
    for row in rows:
        title = str(row.article_name or row.style_code or "Unknown Product").strip()
        quantity = row.quantity if row.quantity is not None else 0
        style_code = str(row.style_code or "").strip()
        lifecycle_start = row.lifecycle_start_date or today
        age_days = max(0, (today - lifecycle_start).days)
        aging_status = classify_status_with_default(row.category, age_days)
        transfer_hint = build_transfer_hint(style_code, style_store_index, row.store_id)

        alert_data = {
            "title": title,
            "price": "{} | Qty {}".format(_format_currency(row.mrp), quantity),
            "site": _format_site(row.store_id, row.store_name, row.store_city),
            "store": "Store {}".format(row.store_id if row.store_id is not None else "N/A"),
            "stock_days": str(age_days),
            "aging_status": str(aging_status),
            "transfer_hint": str(transfer_hint),
            "image": str(row.image_url or row.style_code or "").strip(),
        }
        alerts.append(alert_data)

    return alerts[:limit]


def generate_daily_alert_report(
    alerts: Sequence[Mapping[str, Any]],
    *,
    output_path: str | Path = DEFAULT_REPORT_NAME,
    expected_count: int = ALERTS_PER_PDF,
) -> Path:
    normalized_alerts = _normalize_alerts(alerts, expected_count=expected_count)

    report_path = Path(output_path)
    if not report_path.is_absolute():
        report_path = PROJECT_ROOT / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)

    pdf_canvas = canvas.Canvas(str(report_path), pagesize=letter)
    row_width = _PAGE_WIDTH - (_PAGE_MARGIN * 2)
    y_position = _PAGE_HEIGHT - _PAGE_MARGIN

    pdf_canvas.setTitle("Daily Alert Report")
    pdf_canvas.setAuthor("Inventory Intelligence Platform")

    for index, alert in enumerate(normalized_alerts, start=1):
        if y_position - _ROW_HEIGHT < _PAGE_MARGIN:
            pdf_canvas.showPage()
            y_position = _PAGE_HEIGHT - _PAGE_MARGIN

        _draw_alert_row(
            pdf_canvas,
            alert=alert,
            x=_PAGE_MARGIN,
            y_top=y_position,
            width=row_width,
            height=_ROW_HEIGHT,
        )
        y_position -= _ROW_HEIGHT + _ROW_GAP

    pdf_canvas.save()
    return report_path


def create_and_send_daily_alert_report(
    *,
    alerts: Sequence[Mapping[str, Any]] | None = None,
    output_path: str | Path = DEFAULT_REPORT_NAME,
    send_to_telegram: bool = False,
    expected_count: int = ALERTS_PER_PDF,
) -> dict[str, Any]:
    report_alerts = list(alerts) if alerts is not None else build_alerts_from_database(limit=expected_count)
    report_path = generate_daily_alert_report(
        report_alerts,
        output_path=output_path,
        expected_count=expected_count,
    )

    telegram_sent = False
    if send_to_telegram:
        telegram_sent = send_telegram_document(
            report_path,
            caption="Daily alert report ({} alerts)".format(expected_count),
        )

    return {
        "path": str(report_path),
        "alerts": expected_count,
        "sent_to_telegram": telegram_sent,
    }


__all__ = [
    "ALERTS_PER_PDF",
    "DEFAULT_REPORT_NAME",
    "build_alerts_from_database",
    "create_and_send_daily_alert_report",
    "generate_daily_alert_report",
    "resolve_image_path",
]
