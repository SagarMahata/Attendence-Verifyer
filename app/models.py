from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # "teacher" | "student"

    # JSON-encoded list of 128 floats produced by face-api.js on enrollment.
    face_descriptor = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    polls = relationship("Poll", back_populates="teacher", cascade="all, delete")
    attendances = relationship(
        "Attendance", back_populates="student", cascade="all, delete"
    )

    @property
    def has_face_enrolled(self) -> bool:
        return bool(self.face_descriptor)


class Poll(Base):
    """A single attendance session opened by a teacher for one class."""

    __tablename__ = "polls"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    subject = Column(String(150), nullable=False)

    # Teacher's location at the moment the poll was opened.
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius_m = Column(Float, default=100.0)

    # "Anywhere mode": teacher can waive the geofence check entirely.
    anywhere_mode = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    teacher = relationship("User", back_populates="polls")
    attendances = relationship(
        "Attendance", back_populates="poll", cascade="all, delete"
    )


class Attendance(Base):
    __tablename__ = "attendances"
    __table_args__ = (
        UniqueConstraint("poll_id", "student_id", name="uq_poll_student"),
    )

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("polls.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow)
    distance_m = Column(Float, nullable=True)
    face_match_distance = Column(Float, nullable=True)
    mode = Column(String(20), default="geo")  # "geo" | "anywhere"

    poll = relationship("Poll", back_populates="attendances")
    student = relationship("User", back_populates="attendances")
