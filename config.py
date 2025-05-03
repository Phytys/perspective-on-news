"""
Configuration settings for the application.
Values can be overridden by environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Analysis settings
MAX_WORDS = int(os.getenv("MAX_WORDS", "70"))  # Max words in analysis sections
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "600"))  # Max tokens for OpenAI API
ANALYSE_LIMIT = int(os.getenv("ANALYSE_LIMIT", "1"))  # Default articles to analyze per site

# News fetching settings
NEWS_PER_SITE = int(os.getenv("NEWS_PER_SITE", "10"))  # Headlines to fetch per site
NEWS_SUMMARY_LEN = int(os.getenv("NEWS_SUMMARY_LEN", "70"))  # Max words in news summary

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///balanced_news.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Flask settings
FLASK_ENV = os.getenv("FLASK_ENV", "development")
SECRET_KEY = os.getenv("SECRET_KEY", "dev") 