import importlib

from app.models.alert import Alert
from app.models.daily_snapshot import DailySnapshot
from app.models.delivery_logs import DeliveryLog
from app.models.inventory import Inventory
from app.models.job_log import JobLog
from app.models.lifecycle import LifecycleHistory
from app.models.price_history import PriceHistory
from app.models.product import Product
from app.models.risk_log import RiskLog
from app.models.sales import Sales
from app.models.stores import Store


def import_all_models() -> None:
    for module_name in (
        "app.models.alert",
        "app.models.daily_snapshot",
        "app.models.delivery_logs",
        "app.models.inventory",
        "app.models.job_log",
        "app.models.lifecycle",
        "app.models.price_history",
        "app.models.product",
        "app.models.risk_log",
        "app.models.sales",
        "app.models.stores",
    ):
        importlib.import_module(module_name)


__all__ = [
    "Alert",
    "DailySnapshot",
    "DeliveryLog",
    "Inventory",
    "JobLog",
    "LifecycleHistory",
    "PriceHistory",
    "Product",
    "RiskLog",
    "Sales",
    "Store",
    "import_all_models",
]
