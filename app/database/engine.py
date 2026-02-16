import logging
import sqlite3

from sqlalchemy import create_engine, event, text

from app.config import Settings, get_settings


settings: Settings = get_settings()
logger = logging.getLogger(__name__)

is_sqlite = settings.DATABASE_URL.lower().startswith("sqlite")
connect_args = {}
if is_sqlite:
    connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
            except sqlite3.DatabaseError:
                pass
        finally:
            cursor.close()


_SQLITE_COLUMN_DEFAULTS = {
    "stores": {
        "city": "TEXT NOT NULL DEFAULT ''",
    },
    "products": {
        "supplier_name": "TEXT NOT NULL DEFAULT ''",
        "mrp": "REAL NOT NULL DEFAULT 0",
        "department_name": "TEXT NOT NULL DEFAULT ''",
        "price": "REAL NOT NULL DEFAULT 0",
        "created_at": "DATETIME NOT NULL DEFAULT '1970-01-01 00:00:00'",
        "last_price_update": "DATETIME",
    },
    "inventory": {
        "current_price": "REAL NOT NULL DEFAULT 0",
    },
}

_SQLITE_POST_ADD_UPDATES = {
    ("products", "created_at"): (
        "UPDATE products SET created_at = CURRENT_TIMESTAMP "
        "WHERE created_at = '1970-01-01 00:00:00'"
    ),
}


def ensure_sqlite_schema():
    if not is_sqlite:
        return
    with engine.connect() as conn:
        with conn.begin():
            products_exists = False
            added_columns = []
            for table_name, columns in _SQLITE_COLUMN_DEFAULTS.items():
                # noinspection SqlNoDataSourceInspection
                existing_rows = conn.execute(
                    text(f"PRAGMA table_info({table_name})")
                ).mappings()
                existing = {row["name"] for row in existing_rows}
                if not existing:
                    continue
                if table_name == "products":
                    products_exists = True
                for column_name, ddl in columns.items():
                    if column_name in existing:
                        continue
                    # noinspection SqlNoDataSourceInspection
                    conn.execute(
                        text(
                            "ALTER TABLE {} ADD COLUMN {} {}".format(
                                table_name,
                                column_name,
                                ddl,
                            )
                        )
                    )
                    added_columns.append((table_name, column_name))
            for table_name, column_name in added_columns:
                update_stmt = _SQLITE_POST_ADD_UPDATES.get(
                    (table_name, column_name)
                )
                if update_stmt:
                    # noinspection SqlNoDataSourceInspection
                    conn.execute(text(update_stmt))
            # Enforce unique (store_id, style_code) at the database level.
            # Note: this will fail if duplicates already exist within a store.
            if products_exists:
                has_store_style_unique = False
                indexes = conn.execute(
                    text("PRAGMA index_list(products)")
                ).mappings().all()
                for index in indexes:
                    if not index.get("unique"):
                        continue
                    index_name = index.get("name")
                    if not index_name:
                        continue
                    columns = [
                        row["name"]
                        for row in conn.execute(
                            text('PRAGMA index_info("{}")'.format(index_name.replace('"', '""')))
                        ).mappings()
                    ]
                    if columns == ["store_id", "style_code"]:
                        has_store_style_unique = True
                    if columns == ["style_code"]:
                        try:
                            conn.execute(
                                text(
                                    'DROP INDEX IF EXISTS "{}"'.format(
                                        index_name.replace('"', '""')
                                    )
                                )
                            )
                        except sqlite3.DatabaseError:
                            logger.warning(
                                "Unable to drop legacy unique index %s on products.style_code.",
                                index_name,
                            )
                duplicate = conn.execute(
                    text(
                        "SELECT store_id, style_code FROM products "
                        "GROUP BY store_id, style_code HAVING COUNT(*) > 1 LIMIT 1"
                    )
                ).fetchone()
                if duplicate:
                    logger.warning(
                        "Skipping unique index on products(store_id, style_code) due to duplicates."
                    )
                elif not has_store_style_unique:
                    conn.execute(
                        text(
                            "CREATE UNIQUE INDEX IF NOT EXISTS "
                            "idx_products_store_style_unique ON products(store_id, style_code)"
                        )
                    )
