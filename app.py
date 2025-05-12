#!/usr/bin/env python3
from datetime import datetime, timedelta
import json
from collections import defaultdict
from flask import Flask, render_template, jsonify, abort, request
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from models   import Session, Article, init_db
from analysis import analyse_article
from sources  import SITES           # ← dynamic registry
from config   import MODELS, ADMIN_PASSWORD, FLASK_ENV, config  # Add config import
from fetch_news import collect_news, NEWS_PER_SITE, NEWS_SUMMARY_LEN  # Import fetch functions
from sqlalchemy import or_, func
import logging
import os

load_dotenv()
app = Flask(__name__)
app.config.from_prefixed_env()

# Basic security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# Security headers - configured for both dev and prod
Talisman(app,
    force_https=FLASK_ENV == 'production',  # Only force HTTPS in production
    strict_transport_security=FLASK_ENV == 'production',  # Only HSTS in production
    session_cookie_secure=FLASK_ENV == 'production',  # Only secure cookies in production
    content_security_policy={
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data: https:",
        'connect-src': "'self'",
    },
    feature_policy={
        'geolocation': "'none'",
        'camera': "'none'",
        'microphone': "'none'",
    }
)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', 
                         sites=SITES,
                         now=datetime.utcnow()), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html', 
                         sites=SITES,
                         now=datetime.utcnow()), 500

# Rate limiting - only in production
if FLASK_ENV == 'production':
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=os.getenv("REDIS_URL"),
        storage_options={"ssl_cert_reqs": None}  # Disable SSL verification for Heroku Redis
    )

    # Add rate limits to API endpoints
    def rate_limit(limit):
        return limiter.limit(limit)
else:
    # Dummy decorator for development
    def rate_limit(limit):
        def decorator(f):
            return f
        return decorator

init_db()

# Rate limiting constants
FETCH_COOLDOWN_MINUTES = 15  # Minimum minutes between fetches
MAX_FETCHES_PER_DAY = 24     # Maximum fetches per day

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

def check_fetch_limits() -> tuple[bool, str]:
    """Check if we can fetch news based on rate limits.
    Returns (can_fetch, message)"""
    sess = Session()
    try:
        # Get the most recent fetch
        latest_fetch = (
            sess.query(Article.fetched_at)
            .order_by(Article.fetched_at.desc())
            .first()
        )
        
        if latest_fetch:
            # Check cooldown period
            cooldown = timedelta(minutes=FETCH_COOLDOWN_MINUTES)
            if datetime.utcnow() - latest_fetch[0] < cooldown:
                remaining = cooldown - (datetime.utcnow() - latest_fetch[0])
                return False, f"Vänta {int(remaining.total_seconds() / 60)} minuter innan nästa uppdatering"
            
            # Check daily limit
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_fetches = (
                sess.query(func.count(Article.id))
                .filter(Article.fetched_at >= today_start)
                .scalar()
            )
            
            if today_fetches >= MAX_FETCHES_PER_DAY:
                return False, f"Maximalt antal uppdateringar ({MAX_FETCHES_PER_DAY}) för idag har nåtts"
        
        return True, "OK"
    finally:
        sess.close()

# ---------- front page (all) -----------------------------------------
@app.route("/")
def index_all():
    query = request.args.get('q', '').strip()
    sess = Session()
    
    if query:
        # Search in title and summary
        arts = (
            sess.query(Article)
            .filter(or_(
                Article.title.ilike(f'%{query}%'),
                Article.summary.ilike(f'%{query}%')
            ))
            .order_by(Article.fetched_at.desc())
            .limit(30)
            .all()
        )
    else:
        arts = (
            sess.query(Article)
            .order_by(Article.fetched_at.desc())
            .limit(30)
            .all()
        )
    
    sess.close()
    return render_template("index.html",
        sites=SITES, current_site="all", articles=arts,
        now=datetime.utcnow(), search_query=query, config=config)

# ---------- front page (single) --------------------------------------
@app.route("/site/<site>")
def index_site(site: str):
    if not site_exists(site):
        abort(404)
    
    query = request.args.get('q', '').strip()
    sess = Session()
    
    if query:
        # Search in title and summary for specific site
        arts = (
            sess.query(Article)
            .filter_by(site=site)
            .filter(or_(
                Article.title.ilike(f'%{query}%'),
                Article.summary.ilike(f'%{query}%')
            ))
            .order_by(Article.fetched_at.desc())
            .limit(30)
            .all()
        )
    else:
        arts = (
            sess.query(Article)
            .filter_by(site=site)
            .order_by(Article.fetched_at.desc())
            .limit(30)
            .all()
        )
    
    sess.close()
    return render_template("index.html",
        sites=SITES, current_site=site, articles=arts,
        now=datetime.utcnow(), search_query=query, config=config)

# ---------- analyse one article --------------------------------------
@app.route('/api/analyse', methods=['POST'])
@rate_limit("30 per hour")
def api_analyse():
    try:
        data = request.get_json()
        article_id = data.get('article_id')
        
        if not article_id:
            return jsonify({'error': 'No article ID provided'}), 400
            
        sess = Session()
        article = sess.query(Article).get(article_id)
        if not article:
            sess.close()
            return jsonify({'error': 'Article not found'}), 404
            
        # Get analysis from OpenAI
        analysis = analyse_article({"title": article.title, "summary": article.summary})
        
        # Update article with analysis results
        article.bias_analysis = json.dumps(analysis.get('bias_analysis', {}), ensure_ascii=False)
        article.balanced_perspective = json.dumps(analysis.get('balanced_perspective', {}), ensure_ascii=False)
        article.factual_accuracy = json.dumps(analysis.get('factual_accuracy', {}), ensure_ascii=False)
        article.reporting_quality = json.dumps(analysis.get('reporting_quality', {}), ensure_ascii=False)
        article.dalio_perspective = json.dumps(analysis.get('dalio_perspective', {}), ensure_ascii=False)
        
        # Count verifications and corrections
        claim_verification = analysis['factual_accuracy']['claim_verification']
        unsupported_assertions = analysis['factual_accuracy']['unsupported_assertions']
        
        # Count verified claims (must contain both PÅSTÅENDE: and VERIFIERING: with HÖG or MEDEL confidence)
        verified_count = sum(1 for line in claim_verification.split('\n') 
                           if 'PÅSTÅENDE:' in line and 'VERIFIERING:' in line 
                           and ('KONFIDENS: HÖG' in line or 'KONFIDENS: MEDEL' in line))
        
        # Count corrected claims (must contain both PÅSTÅENDE: and KORRIGERING: with non-empty correction)
        corrected_count = (
            sum(1 for line in claim_verification.split('\n') 
                if 'PÅSTÅENDE:' in line and 'KORRIGERING:' in line 
                and not line.split('KORRIGERING:')[1].strip() == '') +
            sum(1 for line in unsupported_assertions.split('\n')
                if 'PÅSTÅENDE:' in line and 'KORRIGERING:' in line 
                and not line.split('KORRIGERING:')[1].strip() == '')
        )
        
        article.verified_claims = verified_count
        article.corrected_claims = corrected_count
        
        article.analysis_sources = json.dumps(analysis.get("sources", []), ensure_ascii=False)
        article.analyzed_at = datetime.utcnow()
        article.last_updated_at = datetime.utcnow()
        
        # Keep old fields for backward compatibility
        article.balanced_title = analysis.get("main_facts", "")[:300]  # Truncate to match column size
        article.balanced_summary = analysis.get("context", "")
        article.bias_score = 0  # No longer used but keeping for compatibility
        article.bias_label = "nyanserad"
        article.bias_explanation = analysis.get("perspectives", "")
        article.openai_tokens = analysis.get("tokens", 0)
        
        # Store the full analysis
        article.nuanced_perspective = json.dumps(analysis, ensure_ascii=False)
        
        sess.commit()
        sess.close()
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'verified_claims': verified_count,
            'corrected_claims': corrected_count
        })
        
    except Exception as e:
        if 'sess' in locals():
            sess.close()
        return jsonify({'error': str(e)}), 500

# ----------------------------------------------------------------------
# Analytics – verification metrics per outlet
# ----------------------------------------------------------------------
@app.route("/analytics")
def analytics():
    query = request.args.get('q', '').strip()
    sess = Session()
    
    if query:
        # Search in title and summary
        rows = (
            sess.query(
                Article.site,
                Article.verified_claims,
                Article.corrected_claims,
                Article.nuanced_perspective,
                Article.analyzed_at
            )
            .filter(Article.nuanced_perspective.is_not(None))
            .filter(or_(
                Article.title.ilike(f'%{query}%'),
                Article.summary.ilike(f'%{query}%')
            ))
            .all()
        )
    else:
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
    
    # Debug: Print raw data
    print("Raw rows:", rows)
    
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
        
        try:
            analysis = json.loads(analysis_json)
            quality = analysis.get("reporting_quality", {})
            if quality:
                metrics[site]["avg_objectivity"] += quality.get("objectivity_score", 0) or 0
                metrics[site]["avg_depth"] += quality.get("depth_score", 0) or 0
                metrics[site]["avg_evidence"] += quality.get("evidence_score", 0) or 0
                metrics[site]["avg_clarity"] += quality.get("clarity_score", 0) or 0
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing analysis for {site}:", e)
            continue

    # Calculate averages
    for site in metrics:
        total = metrics[site]["total_articles"]
        if total > 0:
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
    
    # Debug: Print final payload
    print("Final payload:", json.dumps(payload, indent=2))
    
    sess.close()

    return render_template(
        "analytics.html",
        verification_data=payload,
        sites=SITES,
        now=datetime.utcnow(),
        search_query=query
    )


# ---------- dev reset -------------------------------------------------
@app.route('/reset-analytics', methods=['POST'])
def reset_analytics():
    data = request.get_json()
    if not data or 'password' not in data or data['password'] != ADMIN_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 401
        
    try:
        # Reset all analysis data
        sess = Session()
        sess.query(Article).update({
            'nuanced_perspective': None,
            'analyzed_at': None,
            'last_updated_at': None,
            'verified_claims': 0,
            'corrected_claims': 0
        })
        sess.commit()
        sess.close()
        return jsonify({'status': 'ok'})
    except Exception as e:
        sess.rollback()
        return jsonify({'error': str(e)}), 500

@app.post("/reset-all")
@rate_limit("3 per hour")
def reset_all():
    # Get password from request
    data = request.get_json()
    if not data or 'password' not in data:
        return jsonify({'error': 'Password required'}), 401
    
    # Check if admin password is configured
    if not ADMIN_PASSWORD:
        return jsonify({'error': 'Admin password not configured'}), 500
    
    # Check password
    if data['password'] != ADMIN_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 401
    
    # If password is correct, proceed with reset
    sess = Session()
    sess.query(Article).delete()
    sess.commit()
    sess.close()
    return ("", 204)

# ---------- fetch news -------------------------------------------------
@app.post("/api/fetch-news")
@rate_limit("10 per hour")
def api_fetch_news():
    try:
        # Check rate limits
        can_fetch, message = check_fetch_limits()
        if not can_fetch:
            return jsonify({"status": "error", "message": message}), 429
        
        # Fetch news from all sources
        news = collect_news(NEWS_PER_SITE, NEWS_SUMMARY_LEN)
        sess = Session()
        
        # Store new articles
        for site, items in news.items():
            for art in items:
                # Check if article already exists
                existing = sess.query(Article).filter_by(site=site, url=art["url"]).first()
                if not existing:
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
                    sess.add(row)
        
        sess.commit()
        sess.close()
        return jsonify({"status": "ok", "message": "News fetched successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/about')
def about():
    return render_template('about.html', 
                         sites=SITES,
                         now=datetime.utcnow())

if __name__ == "__main__":
    app.run()
