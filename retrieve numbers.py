from __future__ import annotations

import argparse
import logging
import os
import pathlib
from collections.abc import Sequence
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tqdm import tqdm
from urllib3.util.retry import Retry

try:
	from dotenv import load_dotenv
except Exception:  # pragma: no cover
	load_dotenv = None  # type: ignore[assignment]

from app.models.base import Base
from app.models.lotto_result import LottoResult
from app.config import resolve_database_url
from app.db import create_app_engine


logger = logging.getLogger(__name__)


def _build_http_session(retries: int, backoff_factor: float) -> requests.Session:
	"""Create a requests session with retry/backoff for transient network errors."""

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


def _get_database_url() -> str:
	"""Resolve DB URL from env, defaulting to the local SQLite db."""

	if load_dotenv is not None:
		load_dotenv()
		p = pathlib.Path(".env.local")
		if p.exists():
			load_dotenv(dotenv_path=p, override=True)

	return resolve_database_url()


def _fetch_draw(http: requests.Session, draw_no: int, timeout_seconds: float) -> tuple[list[int], int]:
	"""Fetch one draw's main numbers and bonus number."""

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

	return [int(n) for n in numbers], int(bonus)


def _draw_exists(http: requests.Session, draw_no: int, timeout_seconds: float) -> bool:
	"""Return True if the remote JSON for a draw exists."""

	url = f"https://smok95.github.io/lotto/results/{draw_no}.json"
	resp = http.get(url, timeout=timeout_seconds)

	# GitHub Pages returns 404 for missing draw files.
	if resp.status_code == 200:
		return True
	if resp.status_code == 404:
		return False

	resp.raise_for_status()
	return True


def _find_latest_draw_no(http: requests.Session, timeout_seconds: float, *, start_hint: int = 1170) -> int:
	"""Find the latest available draw number via exponential search + binary search."""

	if start_hint < 1:
		start_hint = 1

	# If even 1 doesn't exist, something is wrong with the data source.
	if not _draw_exists(http, 1, timeout_seconds=timeout_seconds):
		raise RuntimeError("Lotto data source returned 404 for draw 1")

	low = 1
	high = start_hint

	if _draw_exists(http, high, timeout_seconds=timeout_seconds):
		low = high
		# Exponential search for an upper bound that doesn't exist.
		while True:
			next_high = high * 2
			# Safety cap to avoid infinite loops if upstream behavior changes.
			if next_high > 100_000:
				raise RuntimeError("Failed to find upper bound for latest draw (cap exceeded)")
			high = next_high
			if not _draw_exists(http, high, timeout_seconds=timeout_seconds):
				break
			low = high
	else:
		# start_hint is already above the latest.
		pass

	# Now (low exists) and (high does not exist). Binary search for last existing.
	lo = low
	hi = high
	while lo + 1 < hi:
		mid = (lo + hi) // 2
		if _draw_exists(http, mid, timeout_seconds=timeout_seconds):
			lo = mid
		else:
			hi = mid

	return lo


def _draw_is_complete(db: Session, draw_no: int) -> bool:
	"""Return True if the draw already exists in lotto_results."""

	return db.get(LottoResult, draw_no) is not None


def upsert_draw(db: Session, draw_no: int, numbers: list[int], bonus: int) -> None:
	"""Insert/update a draw in a single wide table."""

	row = LottoResult(
		draw_no=draw_no,
		number1=numbers[0],
		number2=numbers[1],
		number3=numbers[2],
		number4=numbers[3],
		number5=numbers[4],
		number6=numbers[5],
		bonus_number=bonus,
	)

	# merge() does an upsert-like behavior based on primary key
	db.merge(row)


def main(argv: Sequence[str] | None = None) -> int:
	"""Import lotto draws into the database."""

	parser = argparse.ArgumentParser(description="Fetch lotto numbers and insert into DB tables")
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
	parser.add_argument(
		"--database-url",
		dest="database_url",
		type=str,
		default=None,
		help="Override DB connection string (e.g. sqlite:///./app.db)",
	)
	parser.add_argument(
		"--reset",
		action="store_true",
		help="Drop & recreate tables before importing (DANGEROUS)",
	)
	parser.add_argument("--skip-existing", action="store_true", help="Skip draws already fully imported")
	args = parser.parse_args(argv)

	logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

	database_url = str(args.database_url) if args.database_url else _get_database_url()
	engine = create_app_engine(database_url)
	if args.reset:
		Base.metadata.drop_all(bind=engine)
	Base.metadata.create_all(bind=engine)
	session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

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
	logger.info("Import range: %s..%s", args.min_draw_no, max_draw_no)

	imported = 0
	with session_factory() as db:
		for draw_no in tqdm(range(args.min_draw_no, max_draw_no + 1), desc="Importing"):
			if args.skip_existing and _draw_is_complete(db, draw_no):
				continue

			numbers, bonus = _fetch_draw(http, draw_no, timeout_seconds=args.timeout_seconds)
			upsert_draw(db, draw_no, numbers=numbers, bonus=bonus)
			db.commit()
			imported += 1

	logger.info("Imported %s draws", imported)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

