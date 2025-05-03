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

_SYSTEM_PROMPT_TEMPLATE = """Du är en erfaren svensk nyhetsanalytiker.
För varje artikel (rubrik + sammanfattning) returnera strikt JSON med följande struktur:

{{
    "main_facts": "Huvudfakta och påståenden från artikeln",
    "context": "Kort bakgrund och historisk kontext",
    "perspectives": "Olika perspektiv och synvinklar",
    "implications": "Konsekvenser och påverkan",
    "verification": {{
        "verified_claims": ["Lista av verifierade påståenden"],
        "corrected_claims": ["Lista av korrigerade påståenden med motbevis"]
    }},
    "sources": ["Källor för verifiering och kontext"]
}}

Håll varje sektion koncis (max {max_words} ord). Fokusera på att ge en nyanserad bild
som hjälper läsaren förstå hela sammanhanget. Korrigera felaktiga påståenden genom att
presentera motbevis, inte genom att direkt säga att de är fel."""


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
        "main_facts": None,
        "context": None,
        "perspectives": None,
        "implications": None,
        "verification": {
            "verified_claims": [],
            "corrected_claims": []
        },
        "sources": [],
        "tokens": 0,
    }
