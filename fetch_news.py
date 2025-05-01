#!/usr/bin/env python3
"""
Collect latest headlines (10 / site), optionally analyse with OpenAI,
store everything in SQLite.  Run manually or via cron/GitHub Action.
"""
from __future__ import annotations
import argparse, json, logging, os, random, sys, time
from datetime import datetime
from typing import Dict, List

import feedparser, requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from models import Session, Article, init_db
from analysis import analyse_article

load_dotenv()

# -----------------------------------------------------------------------------
log = logging.getLogger("fetch")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)

# --- news sources ------------------------------------------------------------
SITES: Dict[str, Dict[str, str]] = {
    "svt": {
        "rss":  "https://www.svt.se/nyheter/rss.xml",
        "html": "https://www.svt.se/nyheter/",
    },
    "aftonbladet": {
        "rss":  "https://rss.aftonbladet.se/rss2/small/pages/sections/senastenytt/",
        "html": "https://www.aftonbladet.se/nyheter/",
    },
    "expressen": {
        "rss":  "https://feeds.expressen.se/nyheter/",
        "html": "https://www.expressen.se/",
    },
}

UA = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# -----------------------------------------------------------------------------
def truncate_words(txt: str, n: int) -> str:
    words = txt.split()
    return " ".join(words[:n]) + ("…" if len(words) > n else "")

# -----------------------------------------------------------------------------
def rss_top(site: str, n: int, news_len: int) -> List[Dict]:
    feed = feedparser.parse(SITES[site]["rss"])
    if feed.bozo:
        raise RuntimeError(feed.bozo_exception)
    return [
        {
            "title": entry.title,
            "summary": truncate_words(
                BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True),
                news_len,
            ),
            "url": entry.link,
        }
        for entry in feed.entries[:n]
    ]


def html_top(site: str, n: int, news_len: int) -> List[Dict]:
    r = requests.get(
        SITES[site]["html"],
        headers={
            "User-Agent": random.choice(UA),
            "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.5",
        },
        timeout=10,
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for art in soup.find_all("article"):
        if len(items) >= n:
            break
        h = art.find(["h2", "h3"])
        if not h:
            continue
        items.append(
            {
                "title": h.get_text(strip=True),
                "summary": "",                     # plain front pages often lack summary
                "url": h.find("a")["href"] if h.find("a") else SITES[site]["html"],
            }
        )
    # truncate summary if set later
    for it in items:
        it["summary"] = truncate_words(it["summary"], news_len)
    return items


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
    p.add_argument("-n", "--per-site",   type=int, default=10,  help="headlines per site")
    p.add_argument("--news-len",         type=int, default=70,  help="max words kept from feed summary")
    p.add_argument("--balanced-len",     type=int, default=70,  help="max words GPT may return")
    p.add_argument("--max-tokens",       type=int, default=600, help="OpenAI max_tokens (cost cap)")
    p.add_argument("--analyse", action="store_true",
                   help="call OpenAI right away (otherwise only fetch headlines)")
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
        for art in items:
            # skip duplicates
            if session.query(Article).filter_by(site=site, url=art["url"]).first():
                continue

            if args.analyse:
                analysis = analyse_article(
                    art,
                    max_words=args.balanced_len,
                    max_tokens=args.max_tokens,
                )
                analysed += 1
                tokens   += analysis.get("tokens", 0)
            else:
                analysis = {
                    "balanced_title": None,
                    "balanced_summary": None,
                    "bias_score": None,
                    "bias_label": None,
                    "bias_explanation": None,
                    "tokens": 0,
                }

            row = Article(
                site=site,
                title=art["title"],
                summary=art["summary"],
                url=art["url"],
                fetched_at=datetime.utcnow(),
                balanced_title   = analysis["balanced_title"],
                balanced_summary = analysis["balanced_summary"],
                bias_score       = analysis["bias_score"],
                bias_label       = analysis["bias_label"],
                bias_explanation = analysis["bias_explanation"],
                openai_tokens    = analysis["tokens"],
            )
            session.add(row)
            session.commit()
            log.debug("Saved: %s | %s", site, art["title"][:60])

    session.close()
    log.info(
        "Pulled %d headlines | analysed %d | tokens %d (≈ %.2f SEK)",
        pulled, analysed, tokens, tokens * 0.006  # 0.6 öre / token @ gpt-3.5
    )


if __name__ == "__main__":
    main()
