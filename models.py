"""
DB schema (SQLite/PostgreSQL) + session factory
"""
from datetime import datetime
import os
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime,
    create_engine, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

# Use DATABASE_URL from Heroku, fallback to SQLite for local dev
DB_URI = os.getenv("DATABASE_URL", "sqlite:///balanced_news.db")
if DB_URI.startswith("postgres://"):  # Heroku uses postgres:// but SQLAlchemy needs postgresql://
    DB_URI = DB_URI.replace("postgres://", "postgresql://", 1)

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=engine)


class Article(Base):
    __tablename__ = "articles"

    id          = Column(Integer, primary_key=True)
    site        = Column(String,  nullable=False)      # svt / aftonbladet / expressen
    title       = Column(String, nullable=False)
    summary     = Column(Text)
    url         = Column(String, nullable=False)
    fetched_at  = Column(DateTime, default=datetime.utcnow)

    balanced_title     = Column(String)
    balanced_summary   = Column(Text)
    bias_score         = Column(Float)         # -1 = left … +1 = right
    bias_label         = Column(String)
    bias_explanation   = Column(Text)          # short "why" sentence
    
    nuanced_perspective = Column(Text)         # Structured analysis in Swedish
    verified_claims     = Column(Integer, default=0)      # Count of verified claims
    corrected_claims    = Column(Integer, default=0)      # Count of corrected claims
    analysis_sources    = Column(Text)         # JSON array of sources
    analyzed_at         = Column(DateTime)     # When the analysis was performed
    last_updated_at     = Column(DateTime)     # When the analysis was last updated
    elon_musk_perspective = Column(Text)       # Elon Musk's perspective on the news
    
    openai_tokens      = Column(Integer, default=0)       # cost accounting

    __table_args__ = (UniqueConstraint("site", "url", name="uix_site_url"),)


def init_db() -> None:
    """Create tables if they don't exist."""
    Base.metadata.create_all(engine)
