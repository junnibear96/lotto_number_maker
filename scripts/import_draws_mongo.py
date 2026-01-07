"""Import official lotto draw results into MongoDB.

This is the MongoDB equivalent of `retrieve numbers.py`.

Usage (PowerShell):
  $env:DB_BACKEND = 'mongo'
  $env:MONGODB_URI = 'mongodb://localhost:27017'
  $env:MONGODB_DB = 'lotto_number_maker'
  C:/Users/junse/projects/lotto_number_maker/.venv/Scripts/python.exe scripts/import_draws_mongo.py

Options:
  --min 1
  --max 1170   (default: auto-detect latest)
  --skip-existing
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from typing import Any

import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


def _build_http_session(retries: int, backoff_factor: float) -> requests.Session:
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _fetch_draw(http: requests.Session, draw_no: int, timeout_seconds: float) -> tuple[list[int], int]:
    url = f"https://smok95.github.io/lotto/results/{draw_no}.json"
    resp = http.get(url, timeout=timeout_seconds)
    resp.raise_for_status()
    payload: dict[str, Any] = resp.json()

    numbers = payload.get("numbers")
    bonus = payload.get("bonus_no")

    if not isinstance(numbers, list) or len(numbers) != 6:
        raise ValueError(f"Invalid numbers for draw {draw_no}: {numbers}")
    if not isinstance(bonus, int):
        raise ValueError(f"Invalid bonus for draw {draw_no}: {bonus}")

    nums = [int(n) for n in numbers]
    nums.sort()
    return nums, int(bonus)


def _draw_exists(http: requests.Session, draw_no: int, timeout_seconds: float) -> bool:
    url = f"https://smok95.github.io/lotto/results/{draw_no}.json"
    resp = http.get(url, timeout=timeout_seconds)

    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False

    resp.raise_for_status()
    return True


def _find_latest_draw_no(http: requests.Session, timeout_seconds: float, *, start_hint: int = 1170) -> int:
    if start_hint < 1:
        start_hint = 1

    if not _draw_exists(http, 1, timeout_seconds=timeout_seconds):
        raise RuntimeError("Lotto data source returned 404 for draw 1")

    low = 1
    high = start_hint

    if _draw_exists(http, high, timeout_seconds=timeout_seconds):
        low = high
        while True:
            next_high = high * 2
            if next_high > 100_000:
                raise RuntimeError("Failed to find upper bound for latest draw (cap exceeded)")
            high = next_high
            if not _draw_exists(http, high, timeout_seconds=timeout_seconds):
                break
            low = high

    lo = low
    hi = high
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if _draw_exists(http, mid, timeout_seconds=timeout_seconds):
            lo = mid
        else:
            hi = mid

    return lo


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch lotto numbers and upsert into MongoDB")
    parser.add_argument("--min", dest="min_draw_no", type=int, default=1)
    parser.add_argument(
        "--max",
        dest="max_draw_no",
        type=int,
        default=None,
        help="Max draw number (default: auto-detect latest)",
    )
    parser.add_argument("--timeout", dest="timeout_seconds", type=float, default=10.0)
    parser.add_argument("--retries", dest="retries", type=int, default=3)
    parser.add_argument("--backoff", dest="backoff", type=float, default=0.3)
    parser.add_argument("--mongo-uri", dest="mongo_uri", type=str, default=None)
    parser.add_argument("--mongo-db", dest="mongo_db", type=str, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    mongo_uri = args.mongo_uri or "mongodb://localhost:27017"
    mongo_db = args.mongo_db or "lotto_number_maker"

    http = _build_http_session(retries=args.retries, backoff_factor=args.backoff)
    max_draw_no = int(args.max_draw_no) if args.max_draw_no is not None else _find_latest_draw_no(
        http,
        timeout_seconds=float(args.timeout_seconds),
        start_hint=1170,
    )

    if args.min_draw_no < 1:
        raise SystemExit("--min must be >= 1")
    if max_draw_no < args.min_draw_no:
        raise SystemExit(f"--max ({max_draw_no}) must be >= --min ({args.min_draw_no})")

    logger.info("MongoDB: %s (db=%s)", mongo_uri, mongo_db)
    logger.info("Import range: %s..%s", args.min_draw_no, max_draw_no)

    client = MongoClient(mongo_uri)
    db = client[mongo_db]
    col = db["lotto_numbers"]

    # Make draw_no unique.
    try:
        col.create_index("draw_no", unique=True)
    except PyMongoError:
        logger.exception("Failed to create index; continuing")

    imported = 0
    for draw_no in range(int(args.min_draw_no), int(max_draw_no) + 1):
        if args.skip_existing:
            if col.find_one({"draw_no": int(draw_no)}, {"_id": 1}) is not None:
                continue

        numbers, bonus = _fetch_draw(http, int(draw_no), timeout_seconds=float(args.timeout_seconds))

        doc = {
            "draw_no": int(draw_no),
            "number1": int(numbers[0]),
            "number2": int(numbers[1]),
            "number3": int(numbers[2]),
            "number4": int(numbers[3]),
            "number5": int(numbers[4]),
            "number6": int(numbers[5]),
            "bonus_number": int(bonus),
        }

        col.update_one({"draw_no": int(draw_no)}, {"$set": doc}, upsert=True)
        imported += 1

        if imported % 100 == 0:
            logger.info("Imported %s draws...", imported)

    logger.info("Imported %s draws", imported)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
