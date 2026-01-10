import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float


class Base(DeclarativeBase):
    pass


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=True)  # keep as ISO string for MVP simplicity
    total: Mapped[float] = mapped_column(Float, nullable=False)
    tax: Mapped[float] = mapped_column(Float, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False)

    # Always store UTC ISO timestamp string
    created_at: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

