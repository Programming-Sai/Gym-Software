# app/models/goals.py

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum,
    JSON,
    Boolean,
    TIMESTAMP,
    func,
)
from uuid import uuid4
from app.core.database import Base
from sqlalchemy.orm import relationship



class Exercise(Base):
    __tablename__ = "exercises"

    exercise_id = Column(String, primary_key=True, default=lambda: str(uuid4()))

    name = Column(String, nullable=False, unique=True)   # eg. Push Ups
    description = Column(Text, nullable=True)

    category = Column(
        Enum(
            "cardio",
            "strength",
            "mobility",
            "core",
            "flexibility",
            "other",
            name="exercise_categories",
        ),
        nullable=False,
    )

    measurement_type = Column(
        Enum(
            "reps",
            "seconds",
            "minutes",
            "meters",
            "calories",
            name="exercise_measurement_types",
        ),
        nullable=False,
    )

    media = Column(JSON, default=[])   # file_ids (videos/images)
    is_active = Column(Boolean, default=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)





class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    session_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    gym_id = Column(
        String,
        ForeignKey("gyms.gym_id", ondelete="SET NULL"),
        nullable=True,   # home workouts allowed
    )

    status = Column(
        Enum(
            "in_progress",
            "completed",
            "abandoned",
            name="workout_session_statuses",
        ),
        server_default="in_progress",
        nullable=False,
    )

    total_score = Column(Integer, nullable=True)  # optional aggregate

    started_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    ended_at = Column(TIMESTAMP, nullable=True)
    gym = relationship("Gym", back_populates="workout_sessions")







class SessionExercise(Base):
    __tablename__ = "session_exercises"

    session_exercise_id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    session_id = Column(
        String,
        ForeignKey("workout_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )

    exercise_id = Column(
        String,
        ForeignKey("exercises.exercise_id", ondelete="SET NULL"),
        nullable=False,
    )

    # expected target
    target = Column(JSON, nullable=True)
    # actual performance
    performed = Column(JSON, nullable=True)

    # normalized score (0–100 or platform-defined)
    score = Column(Integer, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
