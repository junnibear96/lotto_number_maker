from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from tqdm import tqdm
from urllib3.util.retry import Retry

try:
	from dotenv import load_dotenv
except Exception:  # pragma: no cover
	load_dotenv = None  # type: ignore[assignment]

from app.models.base import Base
from app.models.lotto_result import LottoResult


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

	return os.getenv("DATABASE_URL", "sqlite:///./app.db")


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
	parser.add_argument("--max", dest="max_draw_no", type=int, default=1170)
	parser.add_argument("--timeout", dest="timeout_seconds", type=float, default=10.0)
	parser.add_argument("--retries", dest="retries", type=int, default=3)
	parser.add_argument("--backoff", dest="backoff", type=float, default=0.3)
	parser.add_argument("--skip-existing", action="store_true", help="Skip draws already fully imported")
	args = parser.parse_args(argv)

	logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

	engine = create_engine(_get_database_url(), pool_pre_ping=True, future=True)
	Base.metadata.create_all(bind=engine)
	session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

	http = _build_http_session(retries=args.retries, backoff_factor=args.backoff)

	imported = 0
	with session_factory() as db:
		for draw_no in tqdm(range(args.min_draw_no, args.max_draw_no + 1), desc="Importing"):
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

