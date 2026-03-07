import logging
import os
from typing import Callable, Iterable

from app.services.channels.telegram_service import send_telegram_alert

logger = logging.getLogger(__name__)

ChannelSender = Callable[..., bool]
DispatchResult = dict[str, bool]

_CHANNEL_HANDLERS: dict[str, ChannelSender] = {
    "telegram": send_telegram_alert,
}


def _apply_message_prefix(message: str) -> str:
    prefix = str(os.getenv("ALERT_MESSAGE_PREFIX") or "").strip()
    if not prefix:
        return message
    if message.startswith(prefix):
        return message
    return "{} {}".format(prefix, message)


def _resolve_channels(channels: Iterable[str] | None) -> dict[str, ChannelSender]:
    if channels is None:
        return dict(_CHANNEL_HANDLERS)

    selected: dict[str, ChannelSender] = {}
    for channel_name in channels:
        normalized_name = str(channel_name or "").strip().lower()
        if not normalized_name:
            continue
        handler = _CHANNEL_HANDLERS.get(normalized_name)
        if handler is None:
            logger.warning("Unsupported notification channel '%s'.", normalized_name)
            continue
        selected[normalized_name] = handler
    return selected


def _dispatch_alert(
    message: str,
    channels: Iterable[str] | None = None,
    image_url: str | None = None,
) -> DispatchResult:
    message = _apply_message_prefix(str(message or "").strip())
    if not message:
        logger.warning("Notification dispatch skipped: message is empty.")
        return {}

    handlers = _resolve_channels(channels)
    if not handlers:
        logger.warning("No notification channels are configured for alert dispatch.")
        return {}

    dispatch_result: DispatchResult = {}
    for channel_name, channel_handler in handlers.items():
        try:
            try:
                dispatch_result[channel_name] = bool(
                    channel_handler(message, image_url=image_url)
                )
            except TypeError as exc:
                if "image_url" not in str(exc):
                    raise
                dispatch_result[channel_name] = bool(channel_handler(message))
        except Exception:  # pragma: no cover
            logger.exception(
                "Notification channel '%s' failed while sending alert.",
                channel_name,
            )
            dispatch_result[channel_name] = False
    return dispatch_result


def _normalize_product_name(product_name):
    value = str(product_name or "").strip()
    if value:
        return value
    return "Unknown Product"


def _coerce_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def send_low_stock_alert(
    product_name,
    current_stock,
    channels: Iterable[str] | None = None,
) -> DispatchResult:
    message = (
        "[LOW STOCK ALERT]\n"
        "Product: {}\n"
        "Current Stock: {}\n"
        "Action: Reorder or transfer stock."
    ).format(
        _normalize_product_name(product_name),
        current_stock,
    )
    return _dispatch_alert(message, channels=channels)


def send_inventory_alert(
    message: str,
    channels: Iterable[str] | None = None,
    image_url: str | None = None,
) -> DispatchResult:
    message_value = str(message or "").strip()
    if not message_value:
        logger.warning("Inventory alert skipped: message is empty.")
        return {}
    return _dispatch_alert(message_value, channels=channels, image_url=image_url)


def send_anomaly_alert(
    product_name,
    score,
    channels: Iterable[str] | None = None,
) -> DispatchResult:
    message = (
        "[ANOMALY ALERT]\n"
        "Product: {}\n"
        "Anomaly Score: {:.2f}\n"
        "Action: Review pricing, demand, and sell-through."
    ).format(
        _normalize_product_name(product_name),
        _coerce_float(score),
    )
    return _dispatch_alert(message, channels=channels)


def send_risk_alert(
    product_name,
    risk_score,
    channels: Iterable[str] | None = None,
) -> DispatchResult:
    message = (
        "[RISK ALERT]\n"
        "Product: {}\n"
        "Risk Score: {:.2f}\n"
        "Action: Prioritize mitigation for this SKU."
    ).format(
        _normalize_product_name(product_name),
        _coerce_float(risk_score),
    )
    return _dispatch_alert(message, channels=channels)


__all__ = [
    "send_low_stock_alert",
    "send_inventory_alert",
    "send_anomaly_alert",
    "send_risk_alert",
]
