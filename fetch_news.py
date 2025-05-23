#!/usr/bin/env python3
"""
Collect latest headlines (10 / site), optionally analyse with OpenAI,
store everything in SQLite.  Run manually or via cron/GitHub Action.
"""
from __future__ import annotations
import argparse, json, logging, os, random, sys, time
from datetime import datetime
from typing import Dict, List

import re, html, feedparser, requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from models import Session, Article, init_db
from analysis import analyse_article
from sources import SITES
from config import (
    NEWS_PER_SITE, NEWS_SUMMARY_LEN, MODELS, ANALYSE_LIMIT
)

load_dotenv()

# -----------------------------------------------------------------------------
log = logging.getLogger("fetch")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)


UA = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# -----------------------------------------------------------------------------
def truncate_words(txt: str, n: int) -> str:
    words = txt.split()
    return " ".join(words[:n]) + ("…" if len(words) > n else "")

# -----------------------------------------------------------------------------
CTRL_RE   = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")              # illegal control chars
BAD_AMPER = re.compile(r"&(?!(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);)")    # naked " & " breaks XML

def rss_top(site: str, n: int, news_len: int) -> list[dict]:
    """
    Download & sanitise RSS, then return [{title, summary, url}, …] (≤ n).
    Handles:
      • stray control bytes
      • undefined entities (&nbsp;/&aring;…)
      • naked " & " inside text or attributes
    Works even when feedparser sets bozo=True, as long as entries[] exist.
    """
    url = SITES[site]["rss"]
    raw = requests.get(url, timeout=10).content

    # 1) strip control bytes
    tmp = CTRL_RE.sub(b"", raw)

    # 2) decode → fix entities → re‑encode
    xml_str   = tmp.decode("utf-8", errors="ignore")
    xml_str   = BAD_AMPER.sub("&amp;", xml_str)          # fix naked &
    xml_str   = html.unescape(xml_str)                   # turn &aring; → å
    cleaned   = xml_str.encode("utf-8")

    # 3) parse
    feed = feedparser.parse(cleaned)
    if feed.bozo and not feed.entries:
        raise RuntimeError(feed.bozo_exception)

    # 4) build list
    items = []
    for entry in feed.entries[:n]:
        items.append(
            {
                "title": entry.get("title", "").strip(),
                "summary": truncate_words(
                    BeautifulSoup(entry.get("summary", ""), "html.parser")
                    .get_text(" ", strip=True),
                    news_len,
                ),
                "url": entry.get("link"),
            }
        )
    return items


def html_top(site: str, n: int, news_len: int) -> List[Dict]:
    """
    Fallback scraping for sites whose front page is server‑rendered.
    """
    url = SITES[site]["html"]
    r = requests.get(
        url,
        headers={
            "User-Agent": random.choice(UA),
            "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.5",
        },
        timeout=10,
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    stories = []

    if site == "dagens":
        for a in soup.select("a.front__article-link")[:n]:
                stories.append(
                    {
                        "title": a.get_text(strip=True),
                        "summary": "",
                        "url": "https://dagens.se" + a["href"],   # ← absolute
                    }
                )

    else:  # generic <article><h2> fallback
        for art in soup.find_all("article"):
            if len(stories) >= n:
                break
            h = art.find(["h2", "h3"])
            if not h:
                continue
            stories.append(
                {
                    "title": h.get_text(strip=True),
                    "summary": "",
                    "url": h.find("a")["href"] if h.find("a") else url,
                }
            )

    # Trim words if we filled summary later
    for s in stories:
        s["summary"] = truncate_words(s["summary"], news_len)
    return stories[:n]


def collect_news(n: int, news_len: int) -> Dict[str, List[Dict]]:
    """Return dict {site: [articles…]}"""
    all_sites = {}
    for site in SITES:
        try:
            all_sites[site] = rss_top(site, n, news_len)
            log.info("%s: %d from RSS", site, len(all_sites[site]))
        except Exception as e:
            log.warning("%s RSS failed (%s). Falling back to HTML.", site, e)
            try:
                all_sites[site] = html_top(site, n, news_len)
                log.info("%s: %d from HTML", site, len(all_sites[site]))
            except Exception as ee:
                log.error("%s HTML failed (%s).", site, ee)
                all_sites[site] = []
    return all_sites

# -----------------------------------------------------------------------------
def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fetch & optionally analyse Swedish headlines.")
    p.add_argument("-n", "--per-site",   type=int, default=NEWS_PER_SITE,
                   help=f"headlines per site (default: {NEWS_PER_SITE})")
    p.add_argument("--news-len",         type=int, default=NEWS_SUMMARY_LEN,
                   help=f"max words kept from feed summary (default: {NEWS_SUMMARY_LEN})")
    p.add_argument("--balanced-len",     type=int, default=MODELS["default"]["max_words"],
                   help=f"max words GPT may return (default: {MODELS['default']['max_words']})")
    p.add_argument("--max-tokens",       type=int, default=MODELS["default"]["max_tokens"],
                   help=f"OpenAI max_tokens (default: {MODELS['default']['max_tokens']})")
    p.add_argument("--analyse", action="store_true",
                   help="call OpenAI right away (otherwise only fetch headlines)")
    p.add_argument("--analyse-limit", type=int, default=ANALYSE_LIMIT,
                   help=f"max articles to analyse per site (default: {ANALYSE_LIMIT})")
    return p

# -----------------------------------------------------------------------------
def main() -> None:
    args = build_cli().parse_args()
    init_db()
    session = Session()

    pulled = analysed = tokens = 0
    news = collect_news(args.per_site, args.news_len)

    for site, items in news.items():
        pulled += len(items)
        site_analysed = 0  # Track how many articles we've analyzed for this site
        for art in items:
            # Check if article exists and needs analysis
            existing = session.query(Article).filter_by(site=site, url=art["url"]).first()
            if existing:
                if args.analyse and not existing.nuanced_perspective and site_analysed < args.analyse_limit:
                    # Article exists but needs analysis
                    analysis = analyse_article(
                        art,
                        max_words=args.balanced_len,
                        max_tokens=args.max_tokens,
                    )
                    analysed += 1
                    site_analysed += 1
                    tokens += analysis.get("tokens", 0)
                    
                    # Update existing article with analysis
                    now = datetime.utcnow()
                    existing.nuanced_perspective = json.dumps(analysis, ensure_ascii=False)
                    existing.verified_claims = len(analysis.get("verification", {}).get("verified_claims", []))
                    existing.corrected_claims = len(analysis.get("verification", {}).get("corrected_claims", []))
                    existing.analysis_sources = json.dumps(analysis.get("sources", []), ensure_ascii=False)
                    existing.analyzed_at = now
                    existing.last_updated_at = now
                    
                    # Legacy fields
                    existing.balanced_title = analysis.get("main_facts", "")[:300]
                    existing.balanced_summary = json.dumps(analysis.get("context", {}), ensure_ascii=False)
                    existing.bias_score = 0
                    existing.bias_label = "nyanserad"
                    existing.bias_explanation = json.dumps(analysis.get("perspectives", {}), ensure_ascii=False)
                    existing.openai_tokens = analysis.get("tokens", 0)
                    
                    session.commit()
                continue
            
            if args.analyse and site_analysed < args.analyse_limit:
                analysis = analyse_article(
                    art,
                    max_words=args.balanced_len,
                    max_tokens=args.max_tokens,
                )
                analysed += 1
                site_analysed += 1
                tokens += analysis.get("tokens", 0)
                
                # Store nuanced analysis results
                now = datetime.utcnow()
                row = Article(
                    site=site,
                    title=art["title"],
                    summary=art["summary"],
                    url=art["url"],
                    fetched_at=now,
                    # New fields
                    nuanced_perspective=json.dumps(analysis, ensure_ascii=False),
                    verified_claims=len(analysis.get("verification", {}).get("verified_claims", [])),
                    corrected_claims=len(analysis.get("verification", {}).get("corrected_claims", [])),
                    analysis_sources=json.dumps(analysis.get("sources", []), ensure_ascii=False),
                    analyzed_at=now,
                    last_updated_at=now,
                    # Legacy fields
                    balanced_title=analysis.get("main_facts", "")[:300],
                    balanced_summary=json.dumps(analysis.get("context", {}), ensure_ascii=False),
                    bias_score=0,
                    bias_label="nyanserad",
                    bias_explanation=json.dumps(analysis.get("perspectives", {}), ensure_ascii=False),
                    openai_tokens=analysis.get("tokens", 0),
                )
            else:
                row = Article(
                    site=site,
                    title=art["title"],
                    summary=art["summary"],
                    url=art["url"],
                    fetched_at=datetime.utcnow(),
                    # Initialize new fields as None/0
                    nuanced_perspective=None,
                    verified_claims=0,
                    corrected_claims=0,
                    analysis_sources=None,
                    analyzed_at=None,
                    last_updated_at=None,
                    # Legacy fields
                    balanced_title=None,
                    balanced_summary=None,
                    bias_score=None,
                    bias_label=None,
                    bias_explanation=None,
                    openai_tokens=0,
                )

            session.add(row)
            session.commit()
            log.debug("Saved: %s | %s", site, art["title"][:60])

    # Keep only the 1000 most recent articles
    try:
        # Get the ID of the 1000th most recent article
        oldest_article = session.query(Article.id).order_by(Article.fetched_at.desc()).offset(1000).first()
        if oldest_article:
            # Delete all articles older than the 1000th most recent
            session.query(Article).filter(Article.id < oldest_article[0]).delete()
            session.commit()
            log.info("Deleted articles older than the 1000 most recent")
    except Exception as e:
        log.error("Error while cleaning up old articles: %s", e)
        session.rollback()

    session.close()
    log.info(
        "Pulled %d headlines | analysed %d | tokens %d (≈ %.2f SEK)",
        pulled, analysed, tokens, tokens * 0.006  # 0.6 öre / token @ gpt-3.5
    )


if __name__ == "__main__":
    main()
