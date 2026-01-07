"""Migrate data from SQL (SQLAlchemy) to MongoDB.

Copies:
- `lotto_numbers` (draw_no, number1..6, bonus_number)
- `items` (id, name)

Usage (PowerShell):
  # source SQL
  setx DATABASE_URL "sqlite:///./app.db"

  # target Mongo
  setx MONGODB_URI "mongodb://localhost:27017"
  setx MONGODB_DB "lotto_number_maker"

  # run
  ./.venv/Scripts/python scripts/migrate_sql_to_mongo.py --skip-existing

Notes:
- This does NOT delete your SQL DB.
- Use `--drop-target` only if you want to clear Mongo collections first.
"""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence

from pymongo import MongoClient

from app.config import resolve_database_url
from app.db import create_app_engine


logger = logging.getLogger(__name__)


def _get_sql_url(arg: str | None) -> str:
    return str(arg or os.getenv("DATABASE_URL") or resolve_database_url())


def _get_mongo_uri(arg: str | None) -> str:
    return str(arg or os.getenv("MONGODB_URI") or "mongodb://localhost:27017")


def _get_mongo_db(arg: str | None) -> str:
    return str(arg or os.getenv("MONGODB_DB") or "lotto_number_maker")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate SQL data to MongoDB")
    parser.add_argument("--sql-url", dest="sql_url", type=str, default=None)
    parser.add_argument("--mongo-uri", dest="mongo_uri", type=str, default=None)
    parser.add_argument("--mongo-db", dest="mongo_db", type=str, default=None)
    parser.add_argument("--drop-target", action="store_true", help="Drop target collections before import")
    parser.add_argument("--skip-existing", action="store_true", help="Skip documents already present in Mongo")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    sql_url = _get_sql_url(args.sql_url)
    mongo_uri = _get_mongo_uri(args.mongo_uri)
    mongo_db_name = _get_mongo_db(args.mongo_db)

    logger.info("Source SQL: %s", sql_url)
    logger.info("Target Mongo: %s (db=%s)", mongo_uri, mongo_db_name)

    engine = create_app_engine(sql_url)

    # Import ORM models only for SQL read-side.
    from sqlalchemy.orm import sessionmaker

    from app.models.item import Item
    from app.models.lotto_result import LottoResult

    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    client = MongoClient(mongo_uri)
    db = client[mongo_db_name]

    lotto_col = db["lotto_numbers"]
    items_col = db["items"]
    counters_col = db["counters"]

    # Ensure indexes
    lotto_col.create_index("draw_no", unique=True)
    items_col.create_index("id", unique=True)

    if args.drop_target:
        logger.warning("Dropping target collections: lotto_numbers, items, counters")
        lotto_col.drop()
        items_col.drop()
        counters_col.drop()
        lotto_col = db["lotto_numbers"]
        items_col = db["items"]
        counters_col = db["counters"]
        lotto_col.create_index("draw_no", unique=True)
        items_col.create_index("id", unique=True)

    imported_lotto = 0
    imported_items = 0

    with SessionLocal() as session:
        # lotto_numbers
        draws = session.query(LottoResult).order_by(LottoResult.draw_no.asc()).all()
        logger.info("Found %d lotto draws in SQL", len(draws))
        for d in draws:
            draw_no = int(d.draw_no)
            if args.skip_existing and lotto_col.find_one({"draw_no": draw_no}, {"_id": 1}):
                continue
            doc = {
                "draw_no": draw_no,
                "number1": int(d.number1),
                "number2": int(d.number2),
                "number3": int(d.number3),
                "number4": int(d.number4),
                "number5": int(d.number5),
                "number6": int(d.number6),
                "bonus_number": int(d.bonus_number),
            }
            lotto_col.update_one({"draw_no": draw_no}, {"$set": doc}, upsert=True)
            imported_lotto += 1

        # items
        items = session.query(Item).order_by(Item.id.asc()).all()
        logger.info("Found %d items in SQL", len(items))
        max_item_id = 0
        for it in items:
            item_id = int(it.id)
            max_item_id = max(max_item_id, item_id)
            if args.skip_existing and items_col.find_one({"id": item_id}, {"_id": 1}):
                continue
            doc = {"id": item_id, "name": str(it.name)}
            items_col.update_one({"id": item_id}, {"$set": doc}, upsert=True)
            imported_items += 1

    # Ensure counter aligns with max id so subsequent creates don't conflict.
    if max_item_id > 0:
        counters_col.update_one(
            {"_id": "items"},
            {"$set": {"seq": int(max_item_id)}},
            upsert=True,
        )

    logger.info("Imported lotto draws: %d", imported_lotto)
    logger.info("Imported items: %d", imported_items)
    logger.info("Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
