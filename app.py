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

# Add custom Jinja filter
@app.template_filter('from_json')
def from_json(value):
    return json.loads(value)

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
    now = datetime.utcnow()
    
    if art.nuanced_perspective:
        sess.close(); return jsonify({"status":"cached"})
    res = analyse_article({"title":art.title,"summary":art.summary},
                          max_words=70,max_tokens=600)
    
    # Update article with new analysis
    art.nuanced_perspective = json.dumps(res, ensure_ascii=False)
    art.verified_claims = len(res.get("verification", {}).get("verified_claims", []))
    art.corrected_claims = len(res.get("verification", {}).get("corrected_claims", []))
    art.analysis_sources = json.dumps(res.get("sources", []), ensure_ascii=False)
    art.analyzed_at = now
    art.last_updated_at = now
    
    # Keep old fields for backward compatibility
    art.balanced_title = res.get("main_facts", "")[:300]  # Truncate to match column size
    art.balanced_summary = res.get("context", "")
    art.bias_score = 0  # No longer used but keeping for compatibility
    art.bias_label = "nyanserad"
    art.bias_explanation = res.get("perspectives", "")
    art.openai_tokens = res.get("tokens", 0)
    
    sess.commit(); sess.close()
    return jsonify({"status":"ok", **res})

# ----------------------------------------------------------------------
# Analytics – verification metrics per outlet
# ----------------------------------------------------------------------
@app.route("/analytics")
def analytics():
    sess = Session()
    rows = (
        sess.query(Article.site, Article.verified_claims, Article.corrected_claims)
        .filter(Article.verified_claims.is_not(None))     # ← avoids NULL warning
        .all()
    )
    
    # Aggregate per site
    verified = defaultdict(int)
    corrected = defaultdict(int)
    for site, v, c in rows:
        verified[site] += v or 0
        corrected[site] += c or 0

    labels, v_data, c_data = [], [], []
    for slug, meta in SITES.items():
        if verified[slug] or corrected[slug]:
            labels.append(meta["name"])
            v_data.append(verified[slug])
            c_data.append(corrected[slug])

    payload = {
        "labels": labels,
        "verified": v_data,
        "corrected": c_data
    }
    sess.close()

    return render_template(
        "analytics.html",
        verification_data=payload,  # ← hand raw dict to Jinja
        sites=SITES,               # so nav renders
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
