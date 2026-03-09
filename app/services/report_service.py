import logging
from io import BytesIO
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import unquote, urlsplit

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
from app.services.channels.telegram_service import send_telegram_document

logger = logging.getLogger(__name__)

DEFAULT_REPORT_NAME = "daily_alert_report.pdf"
ALERTS_PER_PDF = 50
MAX_REPORTS_PER_DAY = 0
_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
_DEFAULT_FALLBACK_IMAGE = STATIC_DIR / "sindh-logo.png"
_PAGE_WIDTH, _PAGE_HEIGHT = letter
_PAGE_MARGIN = 36
_ROW_HEIGHT = 130
_ROW_GAP = 10
_ROW_PADDING = 8
_IMAGE_WIDTH = 122
_IMAGE_HEIGHT = 108
_AGING_BADGE_STYLES = {
    "HEALTHY": ("#DCFCE7", "#166534"),
    "TRANSFER": ("#FEF08A", "#854D0E"),
    "RR_TT": ("#FED7AA", "#9A3412"),
    "VERY_DANGER": ("#FECACA", "#991B1B"),
}
_DEFAULT_AGING_BADGE_STYLE = ("#E5E7EB", "#374151")
_AGING_STATUS_SEVERITY = {
    "HEALTHY": 0,
    "TRANSFER": 1,
    "RR_TT": 2,
    "VERY_DANGER": 3,
}


def _format_currency(value: Any) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value or "N/A")
    return "Rs {:,.0f}".format(amount)


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _format_quantity(value: Any) -> str:
    quantity = _safe_float(value, default=0.0)
    if quantity.is_integer():
        return str(int(quantity))
    return "{:.2f}".format(quantity).rstrip("0").rstrip(".")


def _group_style_key(style_code: Any, fallback_title: Any = "") -> str:
    style_text = str(style_code or "").strip()
    if style_text:
        return style_text.casefold()
    fallback_text = str(fallback_title or "").strip()
    return fallback_text.casefold()


def _format_group_store_label(store_id: Any, store_name: Any) -> str:
    store_id_value = str(store_id).strip() if store_id is not None else ""
    store_name_value = str(store_name or "").strip()
    if store_id_value == "1" or store_name_value.casefold() == "store 1":
        return "HEAD OFFICE"

    label = "Store {}".format(store_id if store_id is not None else "N/A")
    if store_name_value:
        label = "{} ({})".format(label, store_name_value)
    return label


def _format_store_distribution(
    store_quantities: Mapping[str, float],
    *,
    max_entries: int = 3,
) -> str:
    ordered_items = sorted(
        store_quantities.items(),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )
    if not ordered_items:
        return "Store N/A"
    parts = [
        "{}: {}".format(store_label, _format_quantity(quantity))
        for store_label, quantity in ordered_items[:max_entries]
    ]
    remaining = len(ordered_items) - max_entries
    if remaining > 0:
        parts.append("+{} more".format(remaining))
    return "; ".join(parts)


def _coerce_alert(alert: Mapping[str, Any]) -> dict[str, str]:
    return {
        "title": str(alert.get("title") or "Unknown Product").strip(),
        "style_code": str(alert.get("style_code") or "").strip(),
        "quantity": str(alert.get("quantity") or "").strip(),
        "price": str(alert.get("price") or "N/A").strip(),
        "site": str(alert.get("site") or "Unknown Source").strip(),
        "store": str(alert.get("store") or "").strip(),
        "stock_days": str(alert.get("stock_days") or "").strip(),
        "cumulative_quantity": str(alert.get("cumulative_quantity") or "").strip(),
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
    selected_alerts = normalized_alerts[:expected_count]
    cumulative_totals: dict[str, float] = {}
    for alert in selected_alerts:
        group_key = str(alert.get("style_code") or alert.get("title") or "").strip()
        if not group_key:
            continue
        quantity_value = max(0.0, _safe_float(alert.get("quantity"), default=0.0))
        cumulative_totals[group_key] = cumulative_totals.get(group_key, 0.0) + quantity_value

    for alert in selected_alerts:
        group_key = str(alert.get("style_code") or alert.get("title") or "").strip()
        if not group_key:
            continue
        total_quantity = cumulative_totals.get(group_key, 0.0)
        if total_quantity > 0:
            alert["cumulative_quantity"] = _format_quantity(total_quantity)

    return selected_alerts


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


def _strip_query_and_fragment(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return ""
    cleaned = cleaned.split("?", 1)[0]
    cleaned = cleaned.split("#", 1)[0]
    return cleaned.strip()


def _extract_static_path_from_url(value: str) -> str | None:
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme not in {"http", "https"}:
        return None
    if not parsed.path:
        return None
    return unquote(parsed.path).strip()


def resolve_image_path(image_value: Any) -> Path | None:
    raw_value = str(image_value or "").strip()
    if not raw_value:
        return _DEFAULT_FALLBACK_IMAGE if _DEFAULT_FALLBACK_IMAGE.exists() else None

    normalized = raw_value.replace("\\", "/").strip()
    static_path = _extract_static_path_from_url(normalized)
    if static_path:
        normalized = static_path
    normalized = _strip_query_and_fragment(normalized)
    if not normalized:
        return _DEFAULT_FALLBACK_IMAGE if _DEFAULT_FALLBACK_IMAGE.exists() else None

    candidates: list[Path] = []

    if normalized.startswith("/static/"):
        candidates.append(PROJECT_ROOT / "app" / normalized.lstrip("/"))
    elif normalized.startswith("static/"):
        candidates.append(PROJECT_ROOT / "app" / normalized)
    elif normalized.startswith("images/"):
        candidates.append(STATIC_DIR / normalized.removeprefix("images/"))
    else:
        candidate = Path(normalized)
        if candidate.is_absolute():
            candidates.append(candidate)
        else:
            candidates.append(PROJECT_ROOT / normalized.lstrip("/\\"))
            candidates.append(STATIC_DIR / "images" / Path(normalized).name)

    for candidate_path in candidates:
        if candidate_path.exists() and candidate_path.is_file():
            return candidate_path

    matched_static_image = _find_static_image_by_stem(normalized)
    if matched_static_image is not None:
        return matched_static_image

    if _DEFAULT_FALLBACK_IMAGE.exists():
        return _DEFAULT_FALLBACK_IMAGE
    return None


def _has_non_fallback_image(image_value: Any) -> bool:
    image_path = resolve_image_path(image_value)
    if image_path is None:
        return False
    if _DEFAULT_FALLBACK_IMAGE.exists() and image_path == _DEFAULT_FALLBACK_IMAGE:
        return False
    return True


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


def _resolve_aging_badge_style(aging_status: str) -> tuple[str, str, str]:
    normalized_status = str(aging_status or "").strip().upper()
    if not normalized_status:
        return "N/A", *_DEFAULT_AGING_BADGE_STYLE
    badge_colors = _AGING_BADGE_STYLES.get(normalized_status, _DEFAULT_AGING_BADGE_STYLE)
    return normalized_status, badge_colors[0], badge_colors[1]


def _draw_aging_badge(
    pdf_canvas: canvas.Canvas,
    *,
    aging_status: str,
    x: float,
    y_baseline: float,
    max_width: float,
) -> float:
    status_label, background_color, text_color = _resolve_aging_badge_style(aging_status)
    badge_text = "Aging: {}".format(status_label)
    font_name = "Helvetica-Bold"
    font_size = 9
    max_text_width = max(20.0, max_width - 10.0)
    rendered_text = _truncate_line(
        badge_text,
        font_name=font_name,
        font_size=font_size,
        max_width=max_text_width,
    )
    badge_text_width = stringWidth(rendered_text, font_name, font_size)
    badge_width = min(max_width, badge_text_width + 10.0)
    badge_height = 12.0
    badge_y = y_baseline - 9.0

    pdf_canvas.setFillColor(colors.HexColor(background_color))
    pdf_canvas.roundRect(
        x,
        badge_y,
        badge_width,
        badge_height,
        3,
        stroke=0,
        fill=1,
    )
    pdf_canvas.setFillColor(colors.HexColor(text_color))
    pdf_canvas.setFont(font_name, font_size)
    pdf_canvas.drawString(x + 5.0, badge_y + 2.5, rendered_text)
    return y_baseline - 15.0


def _draw_text_block(
    pdf_canvas: canvas.Canvas,
    *,
    title: str,
    price: str,
    site: str,
    store: str = "",
    stock_days: str = "",
    cumulative_quantity: str = "",
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

    if stock_days or cumulative_quantity:
        stock_text = "Stock Days: {} | Cumulative Qty: {}".format(
            stock_days or "N/A",
            cumulative_quantity or "N/A",
        )
        for line in simpleSplit(stock_text, "Helvetica", 10, width)[:2]:
            pdf_canvas.drawString(x, text_y, line)
            text_y -= 12

    if aging_status:
        text_y = _draw_aging_badge(
            pdf_canvas,
            aging_status=aging_status,
            x=x,
            y_baseline=text_y,
            max_width=width,
        )

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
        cumulative_quantity=alert.get("cumulative_quantity", ""),
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


def _build_grouped_alerts_from_rows(rows: Sequence[Any], *, today: date) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    image_match_cache: dict[str, bool] = {}

    for row in rows:
        title = str(row.article_name or row.style_code or "Unknown Product").strip()
        style_code = str(row.style_code or "").strip()
        style_key = _group_style_key(style_code, title)
        if not style_key:
            continue

        quantity = max(0.0, _safe_float(row.quantity, default=0.0))
        lifecycle_start = row.lifecycle_start_date or today
        age_days = max(0, (today - lifecycle_start).days)
        aging_status = classify_status_with_default(row.category, age_days)
        image_value = str(row.image_url or row.style_code or "").strip()
        has_non_fallback_image = image_match_cache.get(image_value)
        if has_non_fallback_image is None:
            has_non_fallback_image = _has_non_fallback_image(image_value)
            image_match_cache[image_value] = has_non_fallback_image

        grouped_item = grouped.get(style_key)
        if grouped_item is None:
            grouped_item = {
                "title": title,
                "style_code": style_code or title,
                "mrp": _safe_float(row.mrp, default=0.0),
                "total_quantity": quantity,
                "max_age_days": age_days,
                "aging_status": aging_status,
                "image": image_value,
                "_has_non_fallback_image": bool(has_non_fallback_image),
                "_stores": {
                    _format_group_store_label(row.store_id, row.store_name): quantity
                },
            }
            grouped[style_key] = grouped_item
            continue

        grouped_item["total_quantity"] += quantity
        grouped_item["max_age_days"] = max(grouped_item["max_age_days"], age_days)

        current_severity = _AGING_STATUS_SEVERITY.get(
            str(grouped_item["aging_status"]).upper(),
            -1,
        )
        new_severity = _AGING_STATUS_SEVERITY.get(str(aging_status).upper(), -1)
        if new_severity > current_severity:
            grouped_item["aging_status"] = aging_status

        if grouped_item["mrp"] <= 0:
            grouped_item["mrp"] = _safe_float(row.mrp, default=0.0)

        if not grouped_item["_has_non_fallback_image"] and has_non_fallback_image:
            grouped_item["image"] = image_value
            grouped_item["_has_non_fallback_image"] = True

        store_label = _format_group_store_label(row.store_id, row.store_name)
        grouped_item["_stores"][store_label] = grouped_item["_stores"].get(store_label, 0.0) + quantity

    alerts: list[dict[str, Any]] = []
    for grouped_item in grouped.values():
        store_map = grouped_item.pop("_stores")
        stores_count = len(store_map)
        total_quantity = max(0.0, _safe_float(grouped_item["total_quantity"], default=0.0))
        aging_status = str(grouped_item["aging_status"] or "").upper()
        alerts.append(
            {
                "title": grouped_item["title"],
                "style_code": grouped_item["style_code"],
                "quantity": _format_quantity(total_quantity),
                "price": "{} | Qty {}".format(
                    _format_currency(grouped_item["mrp"]),
                    _format_quantity(total_quantity),
                ),
                "site": "Grouped across {} store{}".format(
                    stores_count,
                    "" if stores_count == 1 else "s",
                ),
                "store": _format_store_distribution(store_map),
                "stock_days": str(grouped_item["max_age_days"]),
                "cumulative_quantity": _format_quantity(total_quantity),
                "aging_status": aging_status or "N/A",
                "transfer_hint": "Same style matched across stores (case-insensitive).",
                "image": grouped_item["image"],
                "_has_non_fallback_image": grouped_item["_has_non_fallback_image"],
                "_stores_count": stores_count,
                "_severity": _AGING_STATUS_SEVERITY.get(aging_status, -1),
                "_total_quantity": total_quantity,
                "_max_age_days": grouped_item["max_age_days"],
            }
        )

    alerts.sort(
        key=lambda item: (
            bool(item.get("_has_non_fallback_image")),
            int(item.get("_severity", -1)),
            int(item.get("_stores_count", 0)),
            float(item.get("_total_quantity", 0.0)),
            int(item.get("_max_age_days", 0)),
        ),
        reverse=True,
    )

    for alert in alerts:
        alert.pop("_stores_count", None)
        alert.pop("_severity", None)
        alert.pop("_total_quantity", None)
        alert.pop("_max_age_days", None)
        alert.pop("_has_non_fallback_image", None)

    return alerts


def build_alerts_from_database(*, limit: int | None = ALERTS_PER_PDF) -> list[dict[str, str]]:
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

    grouped_alerts = _build_grouped_alerts_from_rows(rows, today=today)
    if limit is None:
        return grouped_alerts

    limit_value = int(limit)
    if limit_value <= 0:
        return grouped_alerts
    return grouped_alerts[:limit_value]


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


def _resolve_report_date_tag(report_date: date) -> str:
    return report_date.strftime("%Y%m%d")


def _resolve_daily_report_path(
    *,
    output_path: str | Path,
    report_date: date,
    report_index: int,
) -> Path:
    base_path = Path(output_path)
    if not base_path.is_absolute():
        base_path = PROJECT_ROOT / base_path

    suffix = base_path.suffix or ".pdf"
    stem = base_path.stem or "daily_alert_report"
    date_tag = _resolve_report_date_tag(report_date)
    file_name = "{}_{}_{}{}".format(stem, date_tag, report_index, suffix)
    return base_path.with_name(file_name)


def _list_existing_daily_report_indices(
    *,
    output_path: str | Path,
    report_date: date,
) -> set[int]:
    base_path = Path(output_path)
    if not base_path.is_absolute():
        base_path = PROJECT_ROOT / base_path

    date_tag = _resolve_report_date_tag(report_date)
    stem = base_path.stem or "daily_alert_report"
    suffix = base_path.suffix or ".pdf"
    prefix = "{}_{}_".format(stem, date_tag)

    if not base_path.parent.exists():
        return set()

    indices: set[int] = set()
    pattern = "{}*{}".format(prefix, suffix)
    for report_path in base_path.parent.glob(pattern):
        report_stem = report_path.stem
        if not report_stem.startswith(prefix):
            continue
        index_text = report_stem[len(prefix):].strip()
        if not index_text.isdigit():
            continue
        report_index = int(index_text)
        if report_index > 0:
            indices.add(report_index)
    return indices


def _normalize_reports_limit(max_reports_per_day: int | None) -> int | None:
    if max_reports_per_day is None:
        return None
    limit_value = int(max_reports_per_day)
    if limit_value <= 0:
        return None
    return limit_value


def create_and_send_daily_alert_reports(
    *,
    alerts: Sequence[Mapping[str, Any]] | None = None,
    output_path: str | Path = DEFAULT_REPORT_NAME,
    send_to_telegram: bool = False,
    expected_count: int = ALERTS_PER_PDF,
    max_reports_per_day: int = MAX_REPORTS_PER_DAY,
    report_date: date | None = None,
) -> dict[str, Any]:
    report_date_value = report_date or date.today()
    expected_count = max(1, int(expected_count))
    reports_limit = _normalize_reports_limit(max_reports_per_day)
    total_alert_limit = None if reports_limit is None else (expected_count * reports_limit)
    report_alerts = (
        list(alerts)
        if alerts is not None
        else build_alerts_from_database(limit=total_alert_limit)
    )

    available_report_count = len(report_alerts) // expected_count
    if available_report_count <= 0:
        raise ValueError(
            "Expected at least {} alerts, received {}.".format(
                expected_count,
                len(report_alerts),
            )
        )
    if reports_limit is not None:
        available_report_count = min(available_report_count, reports_limit)

    existing_indices = _list_existing_daily_report_indices(
        output_path=output_path,
        report_date=report_date_value,
    )
    if reports_limit is None:
        next_report_index = (max(existing_indices) + 1) if existing_indices else 1
        generation_plan = [
            (batch_index, next_report_index + batch_index - 1)
            for batch_index in range(1, available_report_count + 1)
        ]
        blocked_indices: set[int] = set()
    else:
        blocked_indices = {
            index for index in existing_indices if 1 <= index <= reports_limit
        }
        generation_plan = []
        for report_index in range(1, available_report_count + 1):
            if report_index in blocked_indices:
                continue
            generation_plan.append((report_index, report_index))

    reports: list[dict[str, Any]] = []
    for batch_index, report_index in generation_plan:
        start = (batch_index - 1) * expected_count
        end = start + expected_count
        alert_batch = report_alerts[start:end]
        if len(alert_batch) < expected_count:
            continue

        report_path = generate_daily_alert_report(
            alert_batch,
            output_path=_resolve_daily_report_path(
                output_path=output_path,
                report_date=report_date_value,
                report_index=report_index,
            ),
            expected_count=expected_count,
        )

        telegram_sent = False
        if send_to_telegram:
            telegram_sent = send_telegram_document(
                report_path,
                caption="Daily alert report #{} ({}/{}) ({} alerts)".format(
                    report_index,
                    batch_index,
                    available_report_count,
                    expected_count,
                ),
            )

        reports.append(
            {
                "path": str(report_path),
                "alerts": expected_count,
                "report_index": report_index,
                "sent_to_telegram": telegram_sent,
            }
        )

    skipped_reason = None
    if not reports and reports_limit is not None and blocked_indices:
        skipped_reason = "Daily PDF limit already reached for {}.".format(
            report_date_value.isoformat()
        )

    return {
        "date": report_date_value.isoformat(),
        "alerts_per_report": expected_count,
        "reports_limit": reports_limit if reports_limit is not None else 0,
        "available_reports": available_report_count,
        "existing_reports_today": len(existing_indices),
        "generated_reports": len(reports),
        "reports": reports,
        "skipped_reason": skipped_reason,
    }


def create_and_send_daily_alert_report(
    *,
    alerts: Sequence[Mapping[str, Any]] | None = None,
    output_path: str | Path = DEFAULT_REPORT_NAME,
    send_to_telegram: bool = False,
    expected_count: int = ALERTS_PER_PDF,
) -> dict[str, Any]:
    summary = create_and_send_daily_alert_reports(
        alerts=alerts,
        output_path=output_path,
        send_to_telegram=send_to_telegram,
        expected_count=expected_count,
        max_reports_per_day=1,
    )
    reports = summary.get("reports") or []
    if not reports:
        raise ValueError(
            "No daily PDF report was generated for {}.".format(summary.get("date"))
        )
    first_report = reports[0]

    return {
        "path": str(first_report["path"]),
        "alerts": int(first_report["alerts"]),
        "sent_to_telegram": bool(first_report["sent_to_telegram"]),
    }


__all__ = [
    "ALERTS_PER_PDF",
    "DEFAULT_REPORT_NAME",
    "MAX_REPORTS_PER_DAY",
    "build_alerts_from_database",
    "create_and_send_daily_alert_report",
    "create_and_send_daily_alert_reports",
    "generate_daily_alert_report",
    "resolve_image_path",
]
