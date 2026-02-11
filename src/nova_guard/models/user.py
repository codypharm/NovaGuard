from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import relationship

from nova_guard.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # Clerk ID
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    patients = relationship("Patient", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
