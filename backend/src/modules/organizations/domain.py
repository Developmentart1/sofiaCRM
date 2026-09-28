"""Organization ORM model. One tenant per row, no sharing."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Organization(Base):
    """Tenant root. All business rows reference organization_id."""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Mexico_City")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="MXN")
    locale: Mapped[str] = mapped_column(String(8), nullable=False, default="es-MX")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"Organization(id={self.id!r}, slug={self.slug!r})"

    @property
    def uuid(self) -> UUID:
        return UUID(self.id)
