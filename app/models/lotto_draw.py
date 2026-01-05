"""Lotto draw model.

Stores one row per draw. The six main numbers and bonus number are stored
in separate tables.
"""

from __future__ import annotations

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LottoDraw(Base):
    """A single lotto draw (draw number)."""

    __tablename__ = "lotto_draws"

    draw_no: Mapped[int] = mapped_column(Integer, primary_key=True)
