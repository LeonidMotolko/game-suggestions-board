import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("suggestions.id", ondelete="CASCADE"), nullable=False
    )
    vote_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "up" или "down"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "suggestion_id", name="unique_user_suggestion_vote"),
    )