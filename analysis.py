"""
Single place that talks to the OpenAI API.
Both fetch_news.py (batch) and app.py (lazy button) import this.
"""
import json, os, time, logging
from dotenv import load_dotenv
import openai

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
log = logging.getLogger("analysis")

_SYSTEM_PROMPT_TEMPLATE = """You are a neutral Swedish media analyst.
For each article (title + summary) return strict JSON with keys:
balanced_title, balanced_summary (≤{max_words} words),
bias_score (-1..1), bias_label, bias_explanation (1–2 sentences)."""


def analyse_article(article: dict,
                    *,
                    max_words: int = 70,
                    max_tokens: int = 600,
                    model: str | None = None) -> dict:
    """
    article: {"title": "...", "summary": "..."}
    returns dict + key 'tokens' (prompt+completion)
    """
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(max_words=max_words)
    model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    tries = 0
    while tries < 3:
        tries += 1
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": json.dumps(article, ensure_ascii=False)},
                ],
                max_tokens=max_tokens,
                temperature=0.2,
            )
            raw  = resp.choices[0].message.content
            data = json.loads(raw)
            data["tokens"] = resp.usage.total_tokens
            return data
        except Exception as e:
            log.warning("OpenAI error (try %d/3): %s", tries, e)
            time.sleep(2 ** tries)

    # all retries failed → return empty shell
    return {
        "balanced_title": None,
        "balanced_summary": None,
        "bias_score": None,
        "bias_label": None,
        "bias_explanation": None,
        "tokens": 0,
    }
