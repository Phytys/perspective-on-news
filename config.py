"""
Configuration settings for the application.
Values can be overridden by environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model configurations
MODELS = {
    "geopolitics": {
        "model": os.getenv("OPENAI_MODEL_GEOPOLITICS", "gpt-4.1"),
        "max_tokens": int(os.getenv("MAX_TOKENS_GEOPOLITICS", "4000")),
        "max_words": int(os.getenv("MAX_WORDS_GEOPOLITICS", "300"))
    },
    "economics": {
        "model": os.getenv("OPENAI_MODEL_ECONOMICS", "gpt-4.1"),
        "max_tokens": int(os.getenv("MAX_TOKENS_ECONOMICS", "4000")),
        "max_words": int(os.getenv("MAX_WORDS_ECONOMICS", "300"))
    },
    "policy": {
        "model": os.getenv("OPENAI_MODEL_POLICY", "gpt-4.1"),
        "max_tokens": int(os.getenv("MAX_TOKENS_POLICY", "4000")),
        "max_words": int(os.getenv("MAX_WORDS_POLICY", "300"))
    },
    "sports": {
        "model": os.getenv("OPENAI_MODEL_SPORTS", "gpt-4.1-nano"),
        "max_tokens": int(os.getenv("MAX_TOKENS_SPORTS", "2000")),
        "max_words": int(os.getenv("MAX_WORDS_SPORTS", "150"))
    },
    "culture": {
        "model": os.getenv("OPENAI_MODEL_CULTURE", "gpt-4.1-nano"),
        "max_tokens": int(os.getenv("MAX_TOKENS_CULTURE", "2000")),
        "max_words": int(os.getenv("MAX_WORDS_CULTURE", "150"))
    },
    "default": {
        "model": os.getenv("OPENAI_MODEL_DEFAULT", "gpt-4.1-mini"),
        "max_tokens": int(os.getenv("MAX_TOKENS_DEFAULT", "3000")),
        "max_words": int(os.getenv("MAX_WORDS_DEFAULT", "200"))
    }
}

# Analysis settings
ANALYSE_LIMIT = int(os.getenv("ANALYSE_LIMIT", "1"))  # Default articles to analyze per site

# News fetching settings
NEWS_PER_SITE = int(os.getenv("NEWS_PER_SITE", "10"))  # Headlines to fetch per site
NEWS_SUMMARY_LEN = int(os.getenv("NEWS_SUMMARY_LEN", "200"))  # Max words in news summary

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///balanced_news.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Flask settings
FLASK_ENV = os.getenv("FLASK_ENV", "development")
SECRET_KEY = os.getenv("SECRET_KEY")

# Admin settings
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")  # Required for admin actions 

# Export all config variables as a dict
config = {
    "FLASK_ENV": FLASK_ENV,
    "SECRET_KEY": SECRET_KEY,
    "DATABASE_URL": DATABASE_URL,
    "NEWS_PER_SITE": NEWS_PER_SITE,
    "NEWS_SUMMARY_LEN": NEWS_SUMMARY_LEN,
    "ANALYSE_LIMIT": ANALYSE_LIMIT,
    "MODELS": MODELS,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "ADMIN_PASSWORD": ADMIN_PASSWORD
} 