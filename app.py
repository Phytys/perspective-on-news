#!/usr/bin/env python3
from datetime import datetime
import json
from collections import defaultdict
from flask import Flask, render_template, jsonify, abort
from dotenv import load_dotenv
from models   import Session, Article, init_db
from analysis import analyse_article
from sources  import SITES           # ← dynamic registry
from config   import MODELS

load_dotenv()
app = Flask(__name__)
app.config.from_prefixed_env()
init_db()

# Add custom Jinja filter
@app.template_filter('from_json')
def from_json(value):
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}

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
    res = analyse_article({"title":art.title,"summary":art.summary})
    
    # Update article with new analysis
    art.nuanced_perspective = json.dumps(res, ensure_ascii=False)
    
    # Extract verification data from factual_accuracy
    factual_accuracy = res.get("factual_accuracy", {})
    claim_verification = factual_accuracy.get("claim_verification", "")
    unsupported_assertions = factual_accuracy.get("unsupported_assertions", "")
    
    # Count verified and corrected claims
    art.verified_claims = len([line for line in claim_verification.split('\n') if line.strip()])
    art.corrected_claims = len([line for line in unsupported_assertions.split('\n') if line.strip()])
    
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
        sess.query(
            Article.site,
            Article.verified_claims,
            Article.corrected_claims,
            Article.nuanced_perspective,
            Article.analyzed_at
        )
        .filter(Article.nuanced_perspective.is_not(None))
        .all()
    )
    
    # Aggregate per site
    metrics = defaultdict(lambda: {
        "verified": 0,
        "corrected": 0,
        "total_articles": 0,
        "avg_objectivity": 0,
        "avg_depth": 0,
        "avg_evidence": 0,
        "avg_clarity": 0
    })
    
    for site, v, c, analysis_json, analyzed_at in rows:
        metrics[site]["verified"] += v or 0
        metrics[site]["corrected"] += c or 0
        metrics[site]["total_articles"] += 1
        
        # Parse analysis JSON to get quality scores
        try:
            analysis = json.loads(analysis_json)
            quality = analysis.get("reporting_quality", {})
            if quality:
                metrics[site]["avg_objectivity"] += quality.get("objectivity_score", 0) or 0
                metrics[site]["avg_depth"] += quality.get("depth_score", 0) or 0
                metrics[site]["avg_evidence"] += quality.get("evidence_score", 0) or 0
                metrics[site]["avg_clarity"] += quality.get("clarity_score", 0) or 0
        except (json.JSONDecodeError, TypeError):
            continue

    # Calculate averages
    for site in metrics:
        total = metrics[site]["total_articles"]
        if total > 0:
            # Scores are already in 0-1 range, just convert to percentage
            metrics[site]["avg_objectivity"] = min(100, max(0, round(metrics[site]["avg_objectivity"] / total, 1)))
            metrics[site]["avg_depth"] = min(100, max(0, round(metrics[site]["avg_depth"] / total, 1)))
            metrics[site]["avg_evidence"] = min(100, max(0, round(metrics[site]["avg_evidence"] / total, 1)))
            metrics[site]["avg_clarity"] = min(100, max(0, round(metrics[site]["avg_clarity"] / total, 1)))

    # Prepare data for chart
    labels, v_data, c_data = [], [], []
    for slug, meta in SITES.items():
        if slug in metrics:
            labels.append(meta["name"])
            v_data.append(metrics[slug]["verified"])
            c_data.append(metrics[slug]["corrected"])

    payload = {
        "labels": labels,
        "verified": v_data,
        "corrected": c_data,
        "metrics": {site: data for site, data in metrics.items()}
    }
    sess.close()

    return render_template(
        "analytics.html",
        verification_data=payload,
        sites=SITES,
        now=datetime.utcnow(),
    )


# ---------- dev reset -------------------------------------------------
@app.post("/reset-analytics")
def reset_analytics():
    sess = Session()
    sess.query(Article).update({
        # Old fields
        Article.balanced_title: None,
        Article.balanced_summary: None,
        Article.bias_score: None,
        Article.bias_label: None,
        Article.bias_explanation: None,
        # New fields
        Article.nuanced_perspective: None,
        Article.verified_claims: 0,
        Article.corrected_claims: 0,
        Article.analysis_sources: None,
        Article.analyzed_at: None,
        Article.last_updated_at: None,
        Article.openai_tokens: 0
    })
    sess.commit()
    sess.close()
    return ("", 204)

if __name__ == "__main__":
    app.run()
