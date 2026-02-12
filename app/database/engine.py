import sqlite3

from sqlalchemy import create_engine, event, text

from app.config import Settings, get_settings


settings: Settings = get_settings()

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
    },
    "inventory": {
        "current_price": "REAL NOT NULL DEFAULT 0",
    },
}


def ensure_sqlite_schema():
    if not is_sqlite:
        return
    with engine.connect() as conn:
        with conn.begin():
            for table_name, columns in _SQLITE_COLUMN_DEFAULTS.items():
                # noinspection SqlNoDataSourceInspection
                existing_rows = conn.execute(
                    text(f"PRAGMA table_info({table_name})")
                ).mappings()
                existing = {row["name"] for row in existing_rows}
                if not existing:
                    continue
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
