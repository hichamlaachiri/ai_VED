import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, default="Director")
    credits_balance = Column(Integer, default=1000)  # 1 credit = $0.01
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    series = relationship("Series", back_populates="user", cascade="all, delete-orphan")
    ledger_entries = relationship("CreditLedger", back_populates="user", cascade="all, delete-orphan")


class CreditLedger(Base):
    __tablename__ = "credit_ledgers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # positive for deposit, negative for charge
    balance_after = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=False)
    meta_info = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="ledger_entries")


class Series(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    premise = Column(Text, nullable=False)
    logline = Column(Text, nullable=True)
    genre = Column(String(100), default="Micro-Drama Thriller")
    locked_lighting = Column(
        String(500),
        default="High-contrast cinematic neo-noir lighting, soft warm fill with subtle teal rim lights, 8k shallow depth of field",
    )
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="series")
    characters = relationship("Character", back_populates="series", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="series", cascade="all, delete-orphan")
    episodes = relationship("Episode", back_populates="series", cascade="all, delete-orphan")


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    name = Column(String(100), nullable=False)
    role_description = Column(String(255), nullable=False)
    visual_tags = Column(Text, nullable=False)
    portrait_image_url = Column(String(500), nullable=True)
    body_image_url = Column(String(500), nullable=True)
    default_screen_position = Column(String(20), default="LEFT")  # "LEFT" or "RIGHT"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    series = relationship("Series", back_populates="characters")


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    name = Column(String(150), nullable=False)
    visual_tags = Column(Text, nullable=False)
    angle_a_image_url = Column(String(500), nullable=True)  # Front angle
    angle_b_image_url = Column(String(500), nullable=True)  # Reverse angle
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    series = relationship("Series", back_populates="locations")


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    episode_number = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    premise = Column(Text, nullable=False)
    outline_summary = Column(Text, nullable=True)
    continuity_notes = Column(Text, nullable=True)
    status = Column(String(50), default="draft")  # draft, scripted, rendering, pass1_rendered, pass2_rendered, assembled
    final_video_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    series = relationship("Series", back_populates="episodes")
    shots = relationship("Shot", back_populates="episode", cascade="all, delete-orphan", order_by="Shot.shot_number")


class Shot(Base):
    __tablename__ = "shots"

    id = Column(Integer, primary_key=True, index=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=False)
    shot_number = Column(Integer, nullable=False)  # 1, 2, 3, 4
    beat_type = Column(String(50), nullable=False)  # Hook (0-15s), Escalation (15-30s), Turn (30-45s), Cliffhanger (45-60s)
    duration_sec = Column(Integer, default=15)

    # Director instructions
    camera_angle = Column(String(100), default="Angle A (Front)")
    camera_movement = Column(String(100), default="Slow push-in")
    spatial_blocking = Column(String(255), nullable=True)
    props_continuity = Column(Text, nullable=True)
    dialogue = Column(Text, nullable=True)
    dialogue_lines_json = Column(Text, nullable=True)  # Exact [{speaker, text, start_sec, end_sec}] JSON for Phase 4 SRT
    compiled_prompt = Column(Text, nullable=False)

    # Video Generation state
    pass1_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    pass1_video_url = Column(String(500), nullable=True)
    pass2_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    pass2_video_url = Column(String(500), nullable=True)

    # Omni multi-turn & fallback
    previous_interaction_id = Column(String(255), nullable=True)
    safety_retry_count = Column(Integer, default=0)
    last_error_message = Column(Text, nullable=True)

    # Final chosen clip for assembler
    selected_pass = Column(String(20), default="pass1")  # pass1 or pass2
    final_video_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    episode = relationship("Episode", back_populates="shots")
