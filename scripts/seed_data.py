import argparse
from datetime import date, timedelta

from sqlalchemy import delete, select

from app.core.logging import setup_logging
from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.stores import Store


def parse_args():
    parser = argparse.ArgumentParser(description="Seed sample inventory data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing data before seeding.",
    )
    return parser.parse_args()


def main():
    setup_logging()
    args = parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()

    db = SessionLocal()
    try:
        if args.reset:
            db.execute(delete(Inventory))
            db.execute(delete(Product))
            db.execute(delete(Store))
            db.commit()

        has_store = db.execute(select(Store.id).limit(1)).first()
        if has_store:
            print("Seed skipped: stores already exist.")
            return

        stores = [
            Store(id=101, name="SINDH Flagship", city="Karachi"),
            Store(id=102, name="SINDH North", city="Lahore"),
        ]
        db.add_all(stores)
        db.flush()

        products = [
            Product(
                store_id=101,
                style_code="DRS-1001",
                barcode="DRS-1001",
                article_name="Silk Dress",
                category="dress",
                department_name="Womenswear",
                supplier_name="SINDH",
                mrp=7200.0,
            ),
            Product(
                store_id=102,
                style_code="SR-2002",
                barcode="SR-2002",
                article_name="Classic Saree",
                category="saree",
                department_name="Ethnic",
                supplier_name="SINDH",
                mrp=9800.0,
            ),
        ]
        db.add_all(products)
        db.flush()

        inventories = [
            Inventory(
                store_id=101,
                product_id=products[0].id,
                quantity=18,
                cost_price=4100.0,
                current_price=6800.0,
                lifecycle_start_date=date.today() - timedelta(days=140),
            ),
            Inventory(
                store_id=102,
                product_id=products[1].id,
                quantity=10,
                cost_price=5600.0,
                current_price=8900.0,
                lifecycle_start_date=date.today() - timedelta(days=220),
            ),
        ]
        db.add_all(inventories)
        db.commit()
        print("Seed data created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
