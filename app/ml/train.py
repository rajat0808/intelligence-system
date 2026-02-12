from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import json
import sys

from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text

from app.core.dates import normalize_date
from app.database import engine as default_engine
from app.ml.features import build_feature_dict
from app.ml.model_io import save_model


def _load_rows(engine, query, params=None):
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row) for row in result.mappings()]


def _load_sales(engine):
    # noinspection SqlNoDataSourceInspection
    return _load_rows(
        engine,
        """
        SELECT store_id, product_id, sale_date, quantity_sold
        FROM sales
        """,
    )


def _load_daily_snapshots(engine):
    # noinspection SqlNoDataSourceInspection
    return _load_rows(
        engine,
        """
        SELECT
            ds.snapshot_date,
            ds.store_id,
            ds.product_id,
            ds.age_days,
            ds.quantity,
            ds.cost_price,
            ds.mrp,
            p.category,
            p.department_name,
            p.supplier_name,
            i.current_price,
            i.lifecycle_start_date
        FROM daily_snapshots ds
        JOIN products p ON p.id = ds.product_id
        LEFT JOIN inventory i
            ON i.store_id = ds.store_id AND i.product_id = ds.product_id
        """,
    )


def _load_inventory(engine):
    # noinspection SqlNoDataSourceInspection
    return _load_rows(
        engine,
        """
        SELECT
            i.store_id,
            i.product_id,
            i.quantity,
            i.cost_price,
            i.current_price,
            i.lifecycle_start_date,
            p.category,
            p.department_name,
            p.supplier_name,
            p.mrp
        FROM inventory i
        JOIN products p ON p.id = i.product_id
        """,
    )


def _build_sales_index(sales_rows):
    index = {}
    for row in sales_rows:
        sale_date = normalize_date(row.get("sale_date"))
        if sale_date is None:
            continue
        key = (row.get("store_id"), row.get("product_id"))
        quantity = row.get("quantity_sold") or 0
        data = index.setdefault(key, {"dates": [], "quantities": []})
        data["dates"].append(sale_date)
        data["quantities"].append(max(0, int(quantity)))

    for key, data in index.items():
        paired = sorted(zip(data["dates"], data["quantities"]), key=lambda item: item[0])
        dates = []
        prefix = [0]
        running = 0
        for sale_date, qty in paired:
            dates.append(sale_date)
            running += qty
            prefix.append(running)
        index[key] = {"dates": dates, "prefix": prefix}
    return index


def _sum_sales(index, key, start_date, end_date):
    data = index.get(key)
    if not data:
        return 0
    dates = data["dates"]
    prefix = data["prefix"]
    left = bisect_left(dates, start_date)
    right = bisect_right(dates, end_date)
    return prefix[right] - prefix[left]


def _recent_sales_keys(sales_rows, start_date, end_date):
    keys = set()
    for row in sales_rows:
        sale_date = normalize_date(row.get("sale_date"))
        if sale_date is None:
            continue
        if sale_date < start_date or sale_date > end_date:
            continue
        if (row.get("quantity_sold") or 0) <= 0:
            continue
        keys.add((row.get("store_id"), row.get("product_id")))
    return keys


def _append_training_row(features, labels, dates, row, label, as_of_date, age_days=None):
    features.append(
        build_feature_dict(
            category=row.get("category"),
            quantity=row.get("quantity"),
            cost_price=row.get("cost_price"),
            lifecycle_start_date=row.get("lifecycle_start_date"),
            as_of_date=as_of_date,
            age_days=age_days,
            current_price=row.get("current_price"),
            mrp=row.get("mrp"),
            department_name=row.get("department_name"),
            supplier_name=row.get("supplier_name"),
            store_id=row.get("store_id"),
        )
    )
    labels.append(label)
    dates.append(as_of_date)


def _build_training_set(rows, *, label_fn, as_of_fn, age_days_fn=None):
    features = []
    labels = []
    dates = []
    for row in rows:
        as_of_date = as_of_fn(row)
        if as_of_date is None:
            continue
        label = label_fn(row, as_of_date)
        if label is None:
            continue
        age_days = age_days_fn(row) if age_days_fn else None
        _append_training_row(
            features,
            labels,
            dates,
            row,
            label,
            as_of_date,
            age_days=age_days,
        )
    return features, labels, dates


def build_training_data(engine, horizon_days, as_of_date=None):
    sales_rows = _load_sales(engine)
    if not sales_rows:
        raise ValueError("No sales data available to build outcome labels.")

    snapshot_rows = _load_daily_snapshots(engine)
    if snapshot_rows:
        sales_index = _build_sales_index(sales_rows)

        def snapshot_as_of(row):
            return normalize_date(row.get("snapshot_date"))

        def snapshot_label(row, as_of_value):
            key = (row.get("store_id"), row.get("product_id"))
            sold_qty = _sum_sales(
                sales_index,
                key,
                as_of_value,
                as_of_value + timedelta(days=horizon_days),
            )
            return 1 if sold_qty > 0 else 0

        features, labels, dates = _build_training_set(
            snapshot_rows,
            label_fn=snapshot_label,
            as_of_fn=snapshot_as_of,
            age_days_fn=lambda row: row.get("age_days"),
        )
        return features, labels, dates, "daily_snapshots+sales"

    inventory_rows = _load_inventory(engine)
    if not inventory_rows:
        raise ValueError("No inventory rows available for training.")

    as_of = normalize_date(as_of_date) or date.today()
    window_start = as_of - timedelta(days=horizon_days)
    recent_keys = _recent_sales_keys(sales_rows, window_start, as_of)

    def inventory_as_of(_row):
        return as_of

    def inventory_label(row, _as_of_date):
        key = (row.get("store_id"), row.get("product_id"))
        return 1 if key in recent_keys else 0

    features, labels, dates = _build_training_set(
        inventory_rows,
        label_fn=inventory_label,
        as_of_fn=inventory_as_of,
    )
    return features, labels, dates, "inventory+recent_sales"


def _split_data(labels, dates, test_size, random_state, use_time_split):
    indices = list(range(len(labels)))
    if use_time_split and dates and len(set(dates)) > 1:
        indices.sort(key=lambda idx: dates[idx])
        split_idx = max(1, int(len(indices) * (1 - test_size)))
        train_idx = indices[:split_idx]
        test_idx = indices[split_idx:]
        if not test_idx:
            test_idx = train_idx[-1:]
            train_idx = train_idx[:-1]
        return train_idx, test_idx

    try:
        train_idx, test_idx = train_test_split(
            indices,
            test_size=test_size,
            random_state=random_state,
            stratify=labels,
        )
    except ValueError:
        train_idx, test_idx = train_test_split(
            indices,
            test_size=test_size,
            random_state=random_state,
            stratify=None,
        )
    return train_idx, test_idx


def _compute_metrics(y_true, y_prob):
    y_pred = [1 if value >= 0.5 else 0 for value in y_prob]
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }

    if len(set(y_true)) > 1:
        metrics["roc_auc"] = roc_auc_score(y_true, y_prob)
        metrics["pr_auc"] = average_precision_score(y_true, y_prob)
        metrics["brier"] = brier_score_loss(y_true, y_prob)
        metrics["log_loss"] = log_loss(y_true, y_prob)
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None
        metrics["brier"] = None
        metrics["log_loss"] = None
    return metrics


def train_and_export(
    engine,
    *,
    horizon_days=30,
    test_size=0.2,
    random_state=42,
    use_time_split=True,
):
    features, labels, dates, source = build_training_data(
        engine, horizon_days=horizon_days
    )
    if len(features) < 10:
        raise ValueError("Not enough training rows (need at least 10).")

    class_counts = Counter(labels)
    if len(class_counts) < 2:
        raise ValueError("Need both positive and negative outcomes to train.")

    train_idx, test_idx = _split_data(
        labels, dates, test_size, random_state, use_time_split
    )
    x_train = [features[idx] for idx in train_idx]
    y_train = [labels[idx] for idx in train_idx]
    x_test = [features[idx] for idx in test_idx]
    y_test = [labels[idx] for idx in test_idx]

    pipeline = Pipeline(
        steps=[
            ("vectorizer", DictVectorizer(sparse=True)),
            ("scaler", StandardScaler(with_mean=False)),
            (
                "classifier",
                LogisticRegression(
                    solver="saga",
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    pipeline.fit(x_train, y_train)
    y_prob = pipeline.predict_proba(x_test)[:, 1]

    metrics = _compute_metrics(y_test, y_prob)
    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_source": source,
        "horizon_days": horizon_days,
        "row_count": len(features),
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "class_balance": dict(class_counts),
        "metrics": metrics,
    }

    model_path, metadata_path = save_model(pipeline, metadata)
    return {
        "model_path": str(model_path),
        "metadata_path": str(metadata_path),
        "metrics": metrics,
        "metadata": metadata,
    }


def _resolve_engine(database_url=None):
    if not database_url:
        return default_engine
    is_sqlite = database_url.lower().startswith("sqlite")
    connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
    return create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Train inventory risk ML model.")
    parser.add_argument("--database-url", dest="database_url", default=None)
    parser.add_argument("--horizon-days", dest="horizon_days", type=int, default=30)
    parser.add_argument("--test-size", dest="test_size", type=float, default=0.2)
    parser.add_argument("--random-state", dest="random_state", type=int, default=42)
    parser.add_argument(
        "--no-time-split",
        dest="no_time_split",
        action="store_true",
        help="Disable time-based split when snapshot dates exist.",
    )

    args = parser.parse_args(argv)
    engine = _resolve_engine(args.database_url)

    result = train_and_export(
        engine,
        horizon_days=args.horizon_days,
        test_size=args.test_size,
        random_state=args.random_state,
        use_time_split=not args.no_time_split,
    )

    print(json.dumps(result["metrics"], indent=2))
    print("Model saved to:", result["model_path"])
    print("Metadata saved to:", result["metadata_path"])


if __name__ == "__main__":
    main(sys.argv[1:])
