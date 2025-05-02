# sources.py  – add or edit feeds here only
SITES = {
    "svt": {
        "name": "SVT",
        "rss":  "https://www.svt.se/nyheter/rss.xml",
        "html": "https://www.svt.se/nyheter/",
    },
    "aftonbladet": {
        "name": "Aftonbladet",
        "rss":  "https://rss.aftonbladet.se/rss2/small/pages/sections/senastenytt/",
        "html": "https://www.aftonbladet.se/nyheter/",
    },
    "expressen": {
        "name": "Expressen",
        "rss":  "https://feeds.expressen.se/nyheter/",
        "html": "https://www.expressen.se/",
    },
    #
    "nyheter24": {
        "name": "Nyheter24",
        "rss":  "https://rsshub.app/nyheter24",   # ← new, DNS‑stable
        "html": "https://nyheter24.se/",
    },
    "omni": {
        "name": "Omni",
        "rss":  "https://feeds.omni.se/rss/omni", # ← valid XML
        "html": "https://www.omni.se/",
    },
    "dagens": {
        "name": "Dagens",
        "rss":  "https://dagens.se/rss.xml",   # valid but sometimes 1–2 bad chars
        "html": "https://dagens.se/",
    },

}
