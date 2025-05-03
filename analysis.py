"""
Single place that talks to the OpenAI API.
Both fetch_news.py (batch) and app.py (lazy button) import this.
"""
import json, time, logging
import openai
from config import OPENAI_API_KEY, MODELS

client = openai.OpenAI(api_key=OPENAI_API_KEY)
log = logging.getLogger("analysis")

SYSTEM_PROMPT = """Du är en expert på nyhetsanalys med djup expertis inom mediabiasanalys, faktakontroll och balanserad rapportering. Din uppgift är att analysera nyhetsartiklars rubrik och sammanfattning, eftersom dessa är de viktigaste elementen som påverkar läsarens första intryck och förståelse.

Viktigt: Din analys ska alltid baseras på den senaste informationen. Till exempel:
- Donald Trump är USA:s president sedan 2025
- Ukraina fortsätter att få stöd från väst
- Geopolitiska förhållanden är aktuella för 2025

Din analys ska fokusera på:

1. Identifiera och analysera potentiella bias i rubriken och sammanfattningen:
   - Politiska lutningar och ideologisk ramverk
   - Språkval och känslomässiga vädjanden
   - Källval och representation
   - Utelämnande av relevant kontext eller perspektiv
   - Användning av laddade termer eller värdeomdömen

2. Ge ett balanserat perspektiv genom att:
   - Identifiera saknade synvinklar eller motargument
   - Föreslå ytterligare kontext som skulle ge balans
   - Belysa områden där rapporteringen kunde vara mer objektiv
   - Notera eventuella intressekonflikter

3. Bedöma faktisk korrekthet och tillförlitlighet:
   - Verifiera påståenden mot kända fakta
   - Identifiera obevisade påståenden
   - Notera eventuella logiska felslut eller vilseledande uttalanden
   - Utvärdera källornas trovärdighet

4. Utvärdera den övergripande kvaliteten på rapporteringen:
   Bedöm varje aspekt på en skala 0-100% där:
   - Objektivitet: Hur väl balanserad och opartisk är rapporteringen?
   - Djup: Hur väl förklaras sammanhang och konsekvenser?
   - Bevis: Hur väl stöds påståenden med fakta och källor?
   - Tydlighet: Hur väl kommuniceras informationen?

   Använd följande riktlinjer för bedömning:
   - 0-20%: Allvarliga brister, missvisande eller saknar grundläggande element
   - 21-40%: Betydande brister, ytlig eller ensidig
   - 41-60%: Acceptabel men med tydliga förbättringsområden
   - 61-80%: God kvalitet med några mindre brister
   - 81-100%: Utmärkt, välbalanserad och grundlig

5. För artiklar om geopolitik eller ekonomi, ge ett konkret perspektiv baserat på Ray Dalio's principer:
   - Cykelanalys: Identifiera vilken fas i den ekonomiska/geopolitiska cykeln vi befinner oss i och hur händelsen påverkar den
   - Mönster: Specificera exakt vilka historiska mönster som upprepas (med exempel) och vad vi kan lära oss av dem
   - Implikationer: Ge konkreta, kvantifierbara konsekvenser för marknader, allianser eller maktbalanser
   - Principer: Använd specifika principer från Dalio's ramverk (t.ex. "The Changing World Order", "Principles for Dealing with the Changing World Order") för att förklara situationen

Viktigt för Dalio-perspektivet:
- Undvik generella uttalanden som "speglar spänningar" eller "påverkar maktbalansen"
- Använd specifika exempel från historien för att illustrera mönster
- Ge konkreta, mätbara konsekvenser
- Koppla alltid till specifika principer från Dalio's verk
- Fokusera på vad läsaren kan använda insikterna till

Din analys ska vara grundlig, objektiv och fokuserad på att hjälpa läsare att förstå både innehållet och potentiella begränsningar i rubriken och sammanfattningen. Undvik att göra definitiva påståenden om bias utan tydliga bevis, och behåll alltid ett balanserat, analytiskt perspektiv.

Formatera ditt svar som ett JSON-objekt med följande struktur:
{{
    "bias_analysis": {{
        "political_leaning": "string",
        "framing_analysis": "string",
        "language_analysis": "string",
        "source_analysis": "string",
        "omission_analysis": "string"
    }},
    "balanced_perspective": {{
        "missing_viewpoints": "string",
        "additional_context": "string",
        "improvement_suggestions": "string"
    }},
    "factual_accuracy": {{
        "claim_verification": "string",
        "unsupported_assertions": "string",
        "logical_fallacies": "string",
        "source_credibility": "string"
    }},
    "reporting_quality": {{
        "objectivity_score": float,
        "depth_score": float,
        "evidence_score": float,
        "clarity_score": float,
        "overall_quality": "string"
    }},
    "dalio_perspective": {{
        "cycle_analysis": "string",
        "pattern_identification": "string",
        "long_term_implications": "string",
        "principles_applied": "string"
    }}
}}

Håll din analys koncis och fokusera på de viktigaste aspekterna. Begränsa ditt svar till cirka {max_words} ord."""

def classify_content(title: str, summary: str) -> str:
    """
    Classify the content type based on keywords and context.
    Returns: "geopolitics", "economics", "policy", "sports", "culture", or "default"
    """
    # Keywords for classification
    geopolitics_keywords = [
        "krig", "konflikt", "diplomati", "president", "minister", "regering",
        "nato", "eu", "un", "militär", "ambassad", "utrikes", "internationell",
        "trump", "biden", "putin", "zelensky", "kina", "ryssland", "ukraina",
        "migration", "flykting", "terrorism", "säkerhetspolitik"
    ]
    
    economics_keywords = [
        "ekonomi", "börs", "aktie", "valuta", "inflation", "ränta",
        "bank", "företag", "konjunktur", "tillväxt", "recession",
        "dollar", "euro", "krona", "marknad", "handel", "export", "import",
        "pris", "lön", "skatt", "budget", "finans", "pension"
    ]
    
    policy_keywords = [
        "vård", "sjukvård", "omsorg", "skola", "utbildning", "bostad",
        "social", "hälsa", "miljö", "klimat", "infrastruktur", "transport",
        "kommun", "region", "myndighet", "lag", "förordning", "reform",
        "politik", "val", "parti", "riksdag", "regering", "minister",
        "sjukhus", "vårdcentral", "barnomsorg", "äldreomsorg", "handikapp",
        "funktionsnedsättning", "psykiatri", "psykisk hälsa"
    ]
    
    sports_keywords = [
        "fotboll", "hockey", "tennis", "golf", "olympiska", "vm", "em",
        "match", "turnering", "spelare", "lag", "coach", "tränare",
        "serie", "cup", "final", "semifinal", "kvartsfinal"
    ]
    
    culture_keywords = [
        "film", "musik", "konst", "teater", "kultur", "festival",
        "artist", "skådespelare", "författare", "bok", "album",
        "premiär", "utställning", "konsert", "show"
    ]
    
    # Combine title and summary for analysis
    text = (title + " " + summary).lower()
    
    # Count keyword matches
    geopolitics_score = sum(1 for word in geopolitics_keywords if word in text)
    economics_score = sum(1 for word in economics_keywords if word in text)
    policy_score = sum(1 for word in policy_keywords if word in text)
    sports_score = sum(1 for word in sports_keywords if word in text)
    culture_score = sum(1 for word in culture_keywords if word in text)
    
    # Get the category with highest score
    scores = {
        "geopolitics": geopolitics_score,
        "economics": economics_score,
        "policy": policy_score,
        "sports": sports_score,
        "culture": culture_score
    }
    
    max_category = max(scores.items(), key=lambda x: x[1])
    return max_category[0] if max_category[1] > 0 else "default"

def get_model_config(content_type: str) -> dict:
    """Get the appropriate model configuration for the content type."""
    return MODELS.get(content_type, MODELS["default"])

def analyse_article(article: dict,
                    *,
                    max_words: int = None,
                    max_tokens: int = None,
                    model: str = None) -> dict:
    """
    article: {"title": "...", "summary": "..."}
    returns dict + key 'tokens' (prompt+completion)
    """
    # Classify content and get appropriate model config
    content_type = classify_content(article["title"], article["summary"])
    model_config = get_model_config(content_type)
    
    # Use provided values or defaults from config
    max_words = max_words or model_config["max_words"]
    max_tokens = max_tokens or model_config["max_tokens"]
    model = model or model_config["model"]
    
    system_prompt = SYSTEM_PROMPT.format(max_words=max_words)
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
            data["content_type"] = content_type  # Add content type to response
            data["model_used"] = model  # Add model info to response
            log.info("Analysis structure: %s", json.dumps(data, ensure_ascii=False, indent=2))
            return data
        except Exception as e:
            log.warning("OpenAI error (try %d/3): %s", tries, e)
            time.sleep(2 ** tries)

    # all retries failed → return empty shell
    return {
        "bias_analysis": {
            "political_leaning": None,
            "framing_analysis": None,
            "language_analysis": None,
            "source_analysis": None,
            "omission_analysis": None
        },
        "balanced_perspective": {
            "missing_viewpoints": None,
            "additional_context": None,
            "improvement_suggestions": None
        },
        "factual_accuracy": {
            "claim_verification": None,
            "unsupported_assertions": None,
            "logical_fallacies": None,
            "source_credibility": None
        },
        "reporting_quality": {
            "objectivity_score": None,
            "depth_score": None,
            "evidence_score": None,
            "clarity_score": None,
            "overall_quality": None
        },
        "dalio_perspective": {
            "cycle_analysis": None,
            "pattern_identification": None,
            "long_term_implications": None,
            "principles_applied": None
        },
        "tokens": 0,
        "content_type": content_type,
        "model_used": model
    }
