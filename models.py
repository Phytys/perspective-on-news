"""
DB schema (SQLite) + session factory
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime,
    create_engine, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker

DB_URI = "sqlite:///balanced_news.db"

Base = declarative_base()
engine = create_engine(DB_URI, echo=False, future=True)
Session = sessionmaker(bind=engine)


class Article(Base):
    __tablename__ = "articles"

    id          = Column(Integer, primary_key=True)
    site        = Column(String(20),  nullable=False)      # svt / aftonbladet / expressen
    title       = Column(String(300), nullable=False)
    summary     = Column(Text)
    url         = Column(String(600), nullable=False)
    fetched_at  = Column(DateTime, default=datetime.utcnow)

    balanced_title     = Column(String(300))
    balanced_summary   = Column(Text)
    bias_score         = Column(Float)         # -1 = left … +1 = right
    bias_label         = Column(String(20))
    bias_explanation   = Column(Text)          # short “why” sentence
    openai_tokens      = Column(Integer)       # cost accounting

    __table_args__ = (UniqueConstraint("site", "url", name="uix_site_url"),)


def init_db() -> None:
    """Create tables if they don’t exist."""
    Base.metadata.create_all(engine)
