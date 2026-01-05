"""Bonus number for a draw (stored separately from main numbers)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LottoBonus(Base):
    """Bonus number for a draw."""

    __tablename__ = "lotto_bonus_numbers"

    draw_no: Mapped[int] = mapped_column(Integer, ForeignKey("lotto_draws.draw_no", ondelete="CASCADE"), primary_key=True)
    number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
