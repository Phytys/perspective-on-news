# Balanced News

"Read the headline — and the *whole* story."

A news aggregator that fetches headlines from Swedish news sources, analyzes them for bias using OpenAI, and presents balanced perspectives to readers.

## How It Works

1. **News Collection**
   - Automatically fetches latest headlines from multiple Swedish news sources
   - Stores articles in a SQLite database
   - Implements rate limiting to prevent excessive API calls
   - Supports manual and scheduled updates

2. **AI Analysis**
   - Uses OpenAI's GPT models to analyze each article
   - Provides multiple perspectives on the news
   - Verifies factual claims
   - Assesses source credibility
   - Generates quality metrics

3. **User Interface**
   - Clean, responsive design
   - Article filtering by source
   - Search functionality
   - Interactive analysis display
   - Analytics dashboard

## Features

### News Aggregation
- Fetches latest headlines from multiple Swedish news sources
- Automatic updates every 15 minutes (configurable)
- Rate limiting to prevent API abuse
- Search functionality across titles and summaries

### AI-Powered Analysis
- Bias detection and analysis
- Balanced perspective generation
- Factual accuracy verification
- Source credibility assessment
- Historical context and implications
- Special analysis for economic/geopolitical news using Ray Dalio's principles

### Quality Metrics
Each article is evaluated on a 0-100% scale for:
- **Objectivity**: How balanced and impartial is the reporting?
- **Depth**: How well are context and consequences explained?
- **Evidence**: How well are claims supported with facts and sources?
- **Clarity**: How effectively is the information communicated?

### Analytics Dashboard
- Overview of news source quality
- Verification statistics
- Quality score trends
- Source comparison metrics

## Supported News Sources

- SVT
- Aftonbladet
- Expressen
- Dagens Nyheter
- Dagens

## Technical Details

### Architecture
- Flask web application
- SQLite database (PostgreSQL supported for production)
- OpenAI API integration
- Rate-limited news fetching
- Caching system for analysis results

### Key Components
- `app.py`: Main Flask application and API endpoints
- `fetch_news.py`: News collection and batch analysis
- `analysis.py`: OpenAI API wrapper and analysis logic
- `models.py`: Database schema and models
- `sources.py`: News source configurations
- `config.py`: Application settings

### API Endpoints
- `/`: Main page with all articles
- `/site/<site>`: Articles from specific source
- `/analytics`: Analytics dashboard
- `/api/analyse`: Trigger analysis for an article
- `/api/fetch-news`: Manual news update
- `/reset-analytics`: Reset analytics data
- `/reset-all`: Reset all data (requires admin password)

## Prerequisites

- Python 3.9+
- OpenAI API key
- SQLite (included) or PostgreSQL

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
| `OPENAI_MODEL` | Chat model | gpt-4.1 |

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
| `FETCH_COOLDOWN_MINUTES` | Minutes between fetches | 15 |
| `MAX_FETCHES_PER_DAY` | Maximum daily fetches | 24 |

### Database Settings
| Key | Description | Default |
|-----|-------------|---------|
| `DATABASE_URL` | Database connection URL | sqlite:///balanced_news.db |

### Flask Settings
| Key | Description | Default |
|-----|-------------|---------|
| `FLASK_ENV` | Environment | development |
| `SECRET_KEY` | Random string for Flask sessions | dev |
| `ADMIN_PASSWORD` | Password for admin functions | - |

## Usage

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

## Development

- Uses SQLite for local development
- Supports PostgreSQL for production
- Zero JavaScript frameworks
- Minimal, responsive design
- Dark mode support
- Mobile-first approach

## License

MIT License