#!/usr/bin/env python3
"""
Balanced News – Flask front-end with:
• Tabs per news-site  (/            and /site/<site>)
• Bias-analysis trigger           (/api/analyse/<id>)
• Analytics dashboard             (/analytics)
• Dev-only reset of analytics     (/reset-analytics  POST)
"""
from datetime import datetime
import json
from collections import defaultdict

from flask import Flask, render_template, jsonify, abort
from dotenv import load_dotenv

from models import Session, Article, init_db
from analysis import analyse_article

load_dotenv()

app = Flask(__name__)
app.config.from_prefixed_env()        # picks up SECRET_KEY, FLASK_ENV

init_db()

# ----------------------------------------------------------------------
# Front page – ALL outlets
# ----------------------------------------------------------------------
@app.route("/")
def index_all():
    sess = Session()
    articles = (
        sess.query(Article)
        .order_by(Article.fetched_at.desc())
        .limit(30)
        .all()
    )
    sess.close()
    return render_template(
        "index.html",
        articles=articles,
        now=datetime.utcnow(),
        current_site="all",
    )

# ----------------------------------------------------------------------
# Front page – SINGLE outlet
# ----------------------------------------------------------------------
@app.route("/site/<site>")
def index_site(site: str):
    if site not in ("svt", "aftonbladet", "expressen"):
        abort(404)
    sess = Session()
    articles = (
        sess.query(Article)
        .filter_by(site=site)
        .order_by(Article.fetched_at.desc())
        .limit(30)
        .all()
    )
    sess.close()
    return render_template(
        "index.html",
        articles=articles,
        now=datetime.utcnow(),
        current_site=site,
    )

# ----------------------------------------------------------------------
# AJAX: analyse one article on-demand
# ----------------------------------------------------------------------
@app.post("/api/analyse/<int:aid>")
def api_analyse(aid: int):
    sess = Session()
    art = sess.get(Article, aid) or abort(404)

    # cached already? 0 cost
    if art.balanced_title:
        sess.close()
        return jsonify({"status": "cached"})

    res = analyse_article(
        {"title": art.title, "summary": art.summary},
        max_words=70,
        max_tokens=600,
    )
    art.balanced_title     = res["balanced_title"]
    art.balanced_summary   = res["balanced_summary"]
    art.bias_score         = res["bias_score"]
    art.bias_label         = res["bias_label"]
    art.bias_explanation   = res["bias_explanation"]
    art.openai_tokens      = res.get("tokens", 0)
    sess.commit(); sess.close()
    return jsonify({"status": "ok", **res})

# ----------------------------------------------------------------------
# Analytics dashboard
# ----------------------------------------------------------------------
@app.route("/analytics")
def analytics():
    sess = Session()

    # -- average bias per outlet ----------
    rows = (
        sess.query(Article.site, Article.bias_score)
        .filter(Article.bias_score != None)
        .all()
    )
    per_site = defaultdict(list)
    for site, score in rows:
        per_site[site].append(score)
    avg_site = {s: sum(v) / len(v) for s, v in per_site.items() if v}

    # -- bias by article type (simple heuristic) ----------
    dom, foreign = [], []
    key_words = ("USA", "Ryssland", "Ukraina", "EU", "Nato", "Kina", "Iran")
    for title, score in (
        sess.query(Article.title, Article.bias_score)
        .filter(Article.bias_score != None)
        .all()
    ):
        (foreign if any(k in title for k in key_words) else dom).append(score)

    by_type = {
        "Domestic": sum(dom) / len(dom) if dom else 0,
        "Foreign" : sum(foreign) / len(foreign) if foreign else 0,
    }

    sess.close()
    return render_template(
        "analytics.html",
        avg_site=json.dumps(avg_site),
        by_type=json.dumps(by_type),
        now=datetime.utcnow(),
    )

# ----------------------------------------------------------------------
# DEV helper – wipe all GPT/bias data so you can re-tune
# ----------------------------------------------------------------------
@app.post("/reset-analytics")
def reset_analytics():
    sess = Session()
    sess.query(Article).update(
        {
            Article.balanced_title:    None,
            Article.balanced_summary:  None,
            Article.bias_score:        None,
            Article.bias_label:        None,
            Article.bias_explanation:  None,
            Article.openai_tokens:     0,
        }
    )
    sess.commit(); sess.close()
    return ("", 204)

# ----------------------------------------------------------------------
if __name__ == "__main__":
    # FLASK_ENV=development gives hot-reload; otherwise set debug=True
    app.run()
