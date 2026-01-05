"""Lotto results stored in one wide table.

Columns:
- draw_no (PK)
- number1..number6
- bonus_number
"""

from __future__ import annotations

from sqlalchemy import Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LottoResult(Base):
    """One row per draw with 6 numbers + bonus."""

    __tablename__ = "lotto_numbers"

    draw_no: Mapped[int] = mapped_column(Integer, primary_key=True)

    number1: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    number2: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    number3: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    number4: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    number5: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    number6: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    bonus_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
