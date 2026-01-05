"""Main lotto numbers for a draw."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LottoNumber(Base):
    """One of the 6 main numbers for a draw."""

    __tablename__ = "lotto_numbers"
    __table_args__ = (UniqueConstraint("draw_no", "position", name="uq_lotto_draw_position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draw_no: Mapped[int] = mapped_column(Integer, ForeignKey("lotto_draws.draw_no", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1..6
    number: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1..45
