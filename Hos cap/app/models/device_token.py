"""
DeviceToken model — stores FCM registration tokens.
Supports multiple tokens per user (multi-browser sessions).
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
        # index=True auto-creates ix_device_tokens_user_id — no need for explicit Index()
    )
    token = Column(String(512), nullable=False)
    ip_address = Column(String(45), nullable=True)  # Store IPv4 or IPv6 address
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="device_tokens")

    # Prevent duplicate tokens — same token cannot be registered twice
    __table_args__ = (
        UniqueConstraint("token", name="uq_device_token"),
    )

    def __repr__(self) -> str:
        return f"<DeviceToken id={self.id} user_id={self.user_id}>"
