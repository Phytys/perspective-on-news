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
        "max_tokens": int(os.getenv("MAX_TOKENS_GEOPOLITICS", "3000")),
        "max_words": int(os.getenv("MAX_WORDS_GEOPOLITICS", "200"))
    },
    "economics": {
        "model": os.getenv("OPENAI_MODEL_ECONOMICS", "gpt-4.1"),
        "max_tokens": int(os.getenv("MAX_TOKENS_ECONOMICS", "3000")),
        "max_words": int(os.getenv("MAX_WORDS_ECONOMICS", "200"))
    },
    "policy": {
        "model": os.getenv("OPENAI_MODEL_POLICY", "gpt-4.1"),
        "max_tokens": int(os.getenv("MAX_TOKENS_POLICY", "3000")),
        "max_words": int(os.getenv("MAX_WORDS_POLICY", "200"))
    },
    "sports": {
        "model": os.getenv("OPENAI_MODEL_SPORTS", "gpt-4.1-nano"),
        "max_tokens": int(os.getenv("MAX_TOKENS_SPORTS", "1000")),
        "max_words": int(os.getenv("MAX_WORDS_SPORTS", "70"))
    },
    "culture": {
        "model": os.getenv("OPENAI_MODEL_CULTURE", "gpt-4.1-nano"),
        "max_tokens": int(os.getenv("MAX_TOKENS_CULTURE", "1000")),
        "max_words": int(os.getenv("MAX_WORDS_CULTURE", "70"))
    },
    "default": {
        "model": os.getenv("OPENAI_MODEL_DEFAULT", "gpt-4.1-mini"),
        "max_tokens": int(os.getenv("MAX_TOKENS_DEFAULT", "1500")),
        "max_words": int(os.getenv("MAX_WORDS_DEFAULT", "100"))
    }
}

# Analysis settings
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