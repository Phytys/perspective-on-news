# Balanced News

"Read the headline — and the *whole* story."

A news aggregator that fetches headlines from Swedish news sources, analyzes them for bias using OpenAI, and presents balanced perspectives to readers.

## Features

- Fetches latest headlines from multiple Swedish news sources
- Uses OpenAI to analyze bias and provide balanced rewrites
- Simple, clean UI inspired by Steve Jobs' design philosophy
- Bias analytics dashboard
- Caches analysis results to minimize API costs

## Supported News Sources

- SVT
- Aftonbladet
- Expressen
- Dagens Nyheter
- Dagens

## Prerequisites

- Python 3.9+
- OpenAI API key (`sk-...`)

## Installation

1. Clone the repository:
```bash
git clone <repo-url> balanced_news
cd balanced_news
```

2. Set up virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

## Configuration

The following environment variables can be set in `.env`:

### OpenAI Settings
| Key | Description | Default |
|-----|-------------|---------|
| `OPENAI_API_KEY` | Required. Your OpenAI API key | - |
| `OPENAI_MODEL` | Chat model | gpt-3.5-turbo |

### Analysis Settings
| Key | Description | Default |
|-----|-------------|---------|
| `MAX_WORDS` | Max words in analysis sections | 70 |
| `MAX_TOKENS` | Max tokens for OpenAI API | 600 |
| `ANALYSE_LIMIT` | Default articles to analyze per site | 1 |

### News Fetching Settings
| Key | Description | Default |
|-----|-------------|---------|
| `NEWS_PER_SITE` | Headlines to fetch per site | 10 |
| `NEWS_SUMMARY_LEN` | Max words in news summary | 70 |

### Database Settings
| Key | Description | Default |
|-----|-------------|---------|
| `DATABASE_URL` | Database connection URL | sqlite:///balanced_news.db |

### Flask Settings
| Key | Description | Default |
|-----|-------------|---------|
| `FLASK_ENV` | Environment | development |
| `SECRET_KEY` | Random string for Flask sessions | dev |

## Usage

### Fetching News

```bash
# Fetch headlines only (no OpenAI cost)
python fetch_news.py --news-len 60

# Fetch and analyze headlines
python fetch_news.py --analyse --balanced-len 60 --max-tokens 400

# Customize number of articles to analyze
python fetch_news.py --analyse --analyse-limit 3
```

### Running the Web Interface

```bash
flask --app app.py run -r
```

Visit http://127.0.0.1:5000/ to see the latest articles.

### Scheduled Updates

Add to crontab for automatic updates:
```bash
*/15 * * * * cd /path/to/balanced_news && python fetch_news.py >> logs/cron.log 2>&1
```

## Project Structure

```
balanced_news/
├── app.py              # Flask UI + API endpoints
├── fetch_news.py       # News fetching + batch analysis
├── analysis.py         # OpenAI API wrapper
├── models.py          # Database schema
├── sources.py         # News source configurations
├── config.py          # Configuration settings
├── requirements.txt
├── .env.example
├── templates/
│   ├── index.html     # Main page template
│   └── analytics.html # Analytics dashboard
└── static/
    └── style.css      # Minimal styling
```

## Development

- Uses SQLite for local development
- Supports PostgreSQL for production
- Zero JavaScript frameworks
- Minimal, responsive design

## License

MIT License