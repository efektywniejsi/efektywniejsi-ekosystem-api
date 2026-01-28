import uuid
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BrandGuidelines(Base):
    __tablename__ = "brand_guidelines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column(unique=True, default="default")

    tone: Mapped[str] = mapped_column(default="")
    style: Mapped[str] = mapped_column(default="")
    target_audience: Mapped[str] = mapped_column(default="")
    unique_selling_proposition: Mapped[str] = mapped_column(default="")

    language: Mapped[str] = mapped_column(default="pl")
    avoid_phrases: Mapped[str] = mapped_column(default="")
    preferred_phrases: Mapped[str] = mapped_column(default="")

    company_description: Mapped[str] = mapped_column(default="")
    additional_instructions: Mapped[str] = mapped_column(default="")

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<BrandGuidelines(id={self.id}, name={self.name})>"
