import logging
import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings


app_settings: Settings = get_settings()
logger = logging.getLogger(__name__)

_SQLITE_BUSY_TIMEOUT_SECONDS = 30
_SQLITE_BUSY_TIMEOUT_MS = _SQLITE_BUSY_TIMEOUT_SECONDS * 1000

_db_url = make_url(app_settings.DATABASE_URL)
is_sqlite = _db_url.get_backend_name() == "sqlite"
is_sqlite_memory = False
if is_sqlite:
    sqlite_db = _db_url.database
    is_sqlite_memory = sqlite_db in (None, "", ":memory:")
    if not is_sqlite_memory and _db_url.query.get("mode") == "memory":
        is_sqlite_memory = True

connect_args = {}
engine_kwargs: dict[str, object] = dict(pool_pre_ping=True)
if is_sqlite:
    connect_args = {"check_same_thread": False, "timeout": _SQLITE_BUSY_TIMEOUT_SECONDS}
    if is_sqlite_memory:
        engine_kwargs.update(poolclass=StaticPool)

engine = create_engine(
    app_settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
            if not is_sqlite_memory:
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
        "image_url": "TEXT",
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


def _escape_sqlite_identifier(value: str) -> str:
    return value.replace('"', '""')


def _get_sqlite_columns(conn, table_name: str):
    escaped_table = _escape_sqlite_identifier(table_name)
    # noinspection SqlNoDataSourceInspection
    result = conn.exec_driver_sql(
        f'PRAGMA table_info("{escaped_table}")'
    ).mappings()
    return {row["name"] for row in result}


def _get_sqlite_index_columns(conn, index_name: str):
    escaped_index = _escape_sqlite_identifier(index_name)
    # noinspection SqlNoDataSourceInspection
    result = conn.exec_driver_sql(
        f'PRAGMA index_info("{escaped_index}")'
    ).mappings()
    return [row["name"] for row in result]


def _has_store_style_unique(columns):
    if len(columns) != 2:
        return False
    return set(columns) == {"store_id", "style_code"}


def ensure_sqlite_schema():
    if not is_sqlite:
        return
    with engine.connect() as conn:
        products_exists = False
        added_columns = []
        with conn.begin():
            for table_name, columns in _SQLITE_COLUMN_DEFAULTS.items():
                existing = _get_sqlite_columns(conn, table_name)
                if not existing:
                    continue
                if table_name == "products":
                    products_exists = True
                for column_name, ddl in columns.items():
                    if column_name in existing:
                        continue
                    escaped_table = _escape_sqlite_identifier(table_name)
                    escaped_column = _escape_sqlite_identifier(column_name)
                    # noinspection SqlNoDataSourceInspection
                    conn.exec_driver_sql(
                        f'ALTER TABLE "{escaped_table}" ADD COLUMN "{escaped_column}" {ddl}'
                    )
                    added_columns.append((table_name, column_name))
            for table_name, column_name in added_columns:
                update_stmt = _SQLITE_POST_ADD_UPDATES.get(
                    (table_name, column_name)
                )
                if update_stmt:
                    # noinspection SqlNoDataSourceInspection
                    conn.exec_driver_sql(update_stmt)

        if not products_exists:
            return

        has_store_style_unique = False
        with conn.begin():
            # noinspection SqlNoDataSourceInspection
            indexes = conn.exec_driver_sql(
                "PRAGMA index_list(products)"
            ).mappings().all()

            for index in indexes:
                if not index.get("unique"):
                    continue
                index_name = index.get("name")
                if not index_name:
                    continue
                columns = _get_sqlite_index_columns(conn, index_name)
                if _has_store_style_unique(columns):
                    has_store_style_unique = True
                if columns == ["style_code"]:
                    origin = index.get("origin")
                    if origin in {"pk", "u"}:
                        logger.warning(
                            "Legacy unique constraint on products.style_code (%s) "
                            "cannot be dropped automatically. "
                            "Rebuild the table to remove it.",
                            index_name,
                        )
                        continue
                    try:
                        with conn.begin_nested():
                            escaped_index = _escape_sqlite_identifier(index_name)
                            # noinspection SqlNoDataSourceInspection
                            conn.exec_driver_sql(
                                f'DROP INDEX IF EXISTS "{escaped_index}"'
                            )
                    except SQLAlchemyError:
                        logger.warning(
                            "Unable to drop legacy unique index %s on products.style_code.",
                            index_name,
                        )

            # noinspection SqlNoDataSourceInspection
            duplicate = conn.exec_driver_sql(
                "SELECT store_id, style_code FROM products "
                "GROUP BY store_id, style_code HAVING COUNT(*) > 1 LIMIT 1"
            ).fetchone()
            if duplicate:
                logger.warning(
                    "Skipping unique index on products(store_id, style_code) due to duplicates."
                )
            elif not has_store_style_unique:
                # noinspection SqlNoDataSourceInspection
                conn.exec_driver_sql(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "idx_products_store_style_unique ON products(store_id, style_code)"
                )
