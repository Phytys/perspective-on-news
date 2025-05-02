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
- Nyheter24
- Dagens
- Omni

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

## Environment Variables

| Key | Description |
|-----|-------------|
| `OPENAI_API_KEY` | Required. Your OpenAI API key |
| `OPENAI_MODEL` | Chat model (default: gpt-3.5-turbo) |
| `FLASK_ENV` | Set to 'development' for auto-reload |
| `SECRET_KEY` | Random string for Flask sessions |

## Usage

### Fetching News

```bash
# Fetch headlines only (no OpenAI cost)
python fetch_news.py --news-len 60

# Fetch and analyze headlines
python fetch_news.py --analyse --balanced-len 60 --max-tokens 400
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