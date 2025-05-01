Below is the complete contents of README.md — copy it as-is into the project root and commit.

markdown
Copy
Edit
# Balanced News – prototype v1
“Read the headline — and the *whole* story.”

This prototype fetches the ten latest news items from **SVT**, **Aftonbladet** and **Expressen**, stores them in SQLite, lets readers request an on-demand “balanced” rewrite plus bias-score via the OpenAI API, and shows everything through a Steve-Jobs-simple Flask UI.

---

## Folder layout

balanced_news/ ├── app.py # Flask UI + lazy /api/analyse/<id> ├── fetch_news.py # pulls headlines & (optional) batch analysis ├── analysis.py # single wrapper around the OpenAI Chat API ├── models.py # SQLAlchemy schema + Session factory ├── requirements.txt ├── .env.example # put your real key in .env (git-ignored) ├── templates/ │ └── index.html # minimal Jinja2 template └── static/ └── style.css # lightweight Jobs-ish styling

yaml
Copy
Edit

---

## Prerequisites

* Python 3.9 +
* An OpenAI API key (`sk-…`)
* Optional: `cron` or GitHub Actions for scheduled fetching

---

## Installation


git clone <repo-url> balanced_news
cd balanced_news
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # paste your real OPENAI_API_KEY
Environment variables (.env)
Key	Description
OPENAI_API_KEY	Required. Your secret key
OPENAI_MODEL	Chat model (default gpt-3.5-turbo)
FLASK_ENV	development enables auto-reload & verbose errors
SECRET_KEY	Any random string for Flask sessions

app.py reads these via app.config.from_prefixed_env().
analysis.py reads them with python-dotenv.

1 Fetching headlines
sql
Copy
Edit
usage: fetch_news.py [-h] [-n N] [--news-len N] [--balanced-len N]
                     [--max-tokens N] [--analyse]

optional arguments:
  -n, --per-site     headlines per site (default 10)
  --news-len         keep max N words from feed summary (default 70)
  --balanced-len     max words GPT may return (default 70)
  --max-tokens       hard cap for OpenAI call (default 600)
  --analyse          call OpenAI immediately (else only fetch headlines)
Typical dev loop
bash
Copy
Edit
# pull raw headlines only (no token cost)
python fetch_news.py --news-len 60

# pull AND pre-analyse everything (≈600 tokens ≈0.03 €)
python fetch_news.py --analyse --balanced-len 60 --max-tokens 400
CRON / GitHub Actions
cron
Copy
Edit
*/15 * * * * cd /srv/balanced_news && /usr/bin/python fetch_news.py >>logs/cron.log 2>&1
Add --analyse if you want the bias check to run automatically.

2 Running the Flask UI
bash
Copy
Edit
flask --app app.py run -r       # http://127.0.0.1:5000/
Shows the 30 most recent articles (10 per site).

Each card has a “Check balance” button if it hasn’t been analysed yet.

Clicking the button:

Sends /api/analyse/<id> (POST)

Triggers the OpenAI call (once per article, then cached)

Injects balanced title, summary & bias info into the card

How the OpenAI call works (analysis.py)
Prompt asks for

balanced_title – neutral factual rewrite

balanced_summary – ≤ N words, adds missing context

bias_score – float ∈ 
−
1
,
1
−1,1 (left → right)

bias_label – plain text label

bias_explanation – 1-2 sentences why

Retries: up to 3 with exponential back-off.

Returns a dict plus tokens, stored for cost tracking.

Database schema (models.py)
Column	Type	Notes
id	PK	
site	svt / aftonbladet / expressen	
title, summary, url	original headline & snippet	
balanced_title, balanced_summary	from GPT, nullable	
bias_score, bias_label, bias_explanation	sentiment & short why	
openai_tokens	prompt + completion tokens	
fetched_at	UTC timestamp	

Duplicate (site, url) combinations are blocked by a UNIQUE constraint.

Styling philosophy
Zero JS frameworks – just 9 lines of vanilla JS in the template.

Jobs-ish design – large type, lots of white space, dark-on-light, one accent colour (#0066cc).

Road-map
Async / batching – cut OpenAI latency & cost

PostgreSQL + Alembic – production-grade DB

User auth – saved lists, hide seen items

Bias trend graphs – bias over time per outlet (pgVector)

HTMX front-end – progressive enhancement

Pull requests welcome – have fun! ✨