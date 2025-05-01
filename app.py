#!/usr/bin/env python3
"""
Minimal Flask front-end for Balanced News.
Lists latest 30 articles; users can click “Check balance” to trigger
an on-demand GPT call that is cached in the DB.
"""
from datetime import datetime
from flask import Flask, render_template, jsonify, abort
from dotenv import load_dotenv

from models import Session, Article, init_db
from analysis import analyse_article

load_dotenv()

app = Flask(__name__)
app.config.from_prefixed_env()      # reads SECRET_KEY, FLASK_ENV

init_db()


@app.route("/")
def index():
    session = Session()
    articles = (
        session.query(Article)
        .order_by(Article.fetched_at.desc())
        .limit(30)
        .all()
    )
    session.close()
    return render_template("index.html", articles=articles, now=datetime.utcnow())


# ---------- AJAX endpoint: analyse on demand ----------------------------
@app.post("/api/analyse/<int:aid>")
def api_analyse(aid: int):
    sess = Session()
    art  = sess.get(Article, aid) or abort(404)

    if art.balanced_title:                     # already cached, no cost
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
    sess.commit()
    sess.close()

    return jsonify({"status": "ok", **res})


if __name__ == "__main__":
    # FLASK_ENV=development gives auto-reload; otherwise set debug=True
    app.run()
