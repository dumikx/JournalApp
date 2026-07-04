from flask import Blueprint, render_template, request
from flask_login import login_required
from markupsafe import Markup, escape
from sqlalchemy import func

from .extensions import db
from .models import Entry

bp = Blueprint("search", __name__)

# Delimitatori improbabili în text; îi înlocuim cu <mark> DUPĂ escape HTML,
# ca textul jurnalului să nu poată injecta markup.
_START, _STOP = "\x02", "\x03"


def _highlight(raw_headline: str) -> Markup:
    escaped = str(escape(raw_headline))
    return Markup(
        escaped.replace(_START, "<mark>").replace(_STOP, "</mark>")
    )


@bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        # Dicționarul «simple» + unaccent pe ambele părți: textul scris cu sau
        # fără diacritice se găsește indiferent de forma din query.
        tsquery = func.plainto_tsquery("simple", func.f_unaccent(q))
        headline = func.ts_headline(
            "simple",
            func.f_unaccent(func.coalesce(Entry.title, "") + " " + Entry.body),
            tsquery,
            f"StartSel={_START}, StopSel={_STOP}, MaxFragments=2, "
            'MaxWords=25, MinWords=10, FragmentDelimiter=" … "',
        )
        rows = (
            db.session.query(Entry, headline)
            .filter(Entry.search_vector.op("@@")(tsquery))
            .order_by(Entry.entry_date.desc())
            .limit(100)
            .all()
        )
        results = [
            {"entry": entry, "snippet": _highlight(snippet)} for entry, snippet in rows
        ]
    return render_template("search.html", q=q, results=results)
