#!/usr/bin/env python3
"""
Add new columns for nuanced analysis
"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    try:
        # Connect to the database
        conn = sqlite3.connect('balanced_news.db')
        cursor = conn.cursor()
        
        # Create articles table if it doesn't exist
        logger.info("Creating articles table if it doesn't exist...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT UNIQUE NOT NULL,
            fetched_at DATETIME NOT NULL,
            balanced_title TEXT,
            balanced_summary TEXT,
            bias_score FLOAT,
            bias_label TEXT,
            bias_explanation TEXT,
            openai_tokens INTEGER DEFAULT 0,
            nuanced_perspective TEXT,
            verified_claims INTEGER DEFAULT 0,
            corrected_claims INTEGER DEFAULT 0,
            analysis_sources TEXT,
            analyzed_at DATETIME,
            last_updated_at DATETIME,
            elon_musk_perspective TEXT
        )
        """)
        
        # Add indices for common queries
        logger.info("Creating indices...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_site ON articles(site)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_fetched_at ON articles(fetched_at)")
        
        # Add elon_musk_perspective column if it doesn't exist
        logger.info("Adding elon_musk_perspective column if it doesn't exist...")
        try:
            cursor.execute("ALTER TABLE articles ADD COLUMN elon_musk_perspective TEXT")
            logger.info("Added elon_musk_perspective column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.info("elon_musk_perspective column already exists")
            else:
                raise
        
        # Commit changes
        conn.commit()
        logger.info("Migration completed successfully!")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("Columns already exist, skipping...")
        else:
            logger.error(f"Error during migration: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate() 