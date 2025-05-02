#!/usr/bin/env python3
from datetime import datetime
import json
from collections import defaultdict

from flask import Flask, render_template, jsonify, abort
from dotenv import load_dotenv

from models   import Session, Article, init_db
from analysis import analyse_article
from sources  import SITES           # ← dynamic registry

load_dotenv()
app = Flask(__name__)
app.config.from_prefixed_env()
init_db()

# ---------- helper ----------------------------------------------------
def site_exists(slug: str) -> bool:     # central truth
    return slug in SITES

# ---------- front page (all) -----------------------------------------
@app.route("/")
def index_all():
    sess = Session()
    arts = (
        sess.query(Article).order_by(Article.fetched_at.desc()).limit(30).all()
    )
    sess.close()
    return render_template("index.html",
        sites=SITES, current_site="all", articles=arts,
        now=datetime.utcnow())

# ---------- front page (single) --------------------------------------
@app.route("/site/<site>")
def index_site(site: str):
    if not site_exists(site):
        abort(404)
    sess = Session()
    arts = (
        sess.query(Article)
        .filter_by(site=site)
        .order_by(Article.fetched_at.desc()).limit(30).all()
    )
    sess.close()
    return render_template("index.html",
        sites=SITES, current_site=site, articles=arts,
        now=datetime.utcnow())

# ---------- analyse one article --------------------------------------
@app.post("/api/analyse/<int:aid>")
def api_analyse(aid: int):
    sess = Session()
    art = sess.get(Article, aid) or abort(404)
    if art.balanced_title:
        sess.close(); return jsonify({"status":"cached"})
    res = analyse_article({"title":art.title,"summary":art.summary},
                          max_words=70,max_tokens=600)
    for k,v in (
        ("balanced_title","balanced_title"),
        ("balanced_summary","balanced_summary"),
        ("bias_score","bias_score"),
        ("bias_label","bias_label"),
        ("bias_explanation","bias_explanation"),
    ):
        setattr(art, k, res[v])
    art.openai_tokens = res.get("tokens",0)
    sess.commit(); sess.close()
    return jsonify({"status":"ok",**res})

# ----------------------------------------------------------------------
# Analytics – average bias per outlet, plus sample size (robust)
# ----------------------------------------------------------------------
@app.route("/analytics")
def analytics():
    sess = Session()
    rows = (
        sess.query(Article.site, Article.bias_score)
        .filter(Article.bias_score.is_not(None))     # ← avoids NULL warning
        .all()
    )
    sums, counts = defaultdict(float), defaultdict(int)
    for site, score in rows:
        sums[site]   += float(score or 0)
        counts[site] += 1

    labels, avgs, tips = [], [], []
    for slug, meta in SITES.items():
        n = counts.get(slug, 0)
        if n:
            labels.append(meta["name"])
            avgs.append(round(sums[slug] / n, 3))
            tips.append(f"{n} articles")

    payload = {"labels": labels, "avgs": avgs, "tips": tips}
    sess.close()

    return render_template(
        "analytics.html",
        bias_data=payload,     # ← hand raw dict to Jinja
        sites=SITES,           # so nav renders
        now=datetime.utcnow(),
    )


# ---------- dev reset -------------------------------------------------
@app.post("/reset-analytics")
def reset_analytics():
    sess = Session()
    sess.query(Article).update(
        {Article.balanced_title:None, Article.balanced_summary:None,
         Article.bias_score:None, Article.bias_label:None,
         Article.bias_explanation:None, Article.openai_tokens:0})
    sess.commit(); sess.close(); return ("",204)

if __name__ == "__main__":
    app.run()
