from datetime import date, datetime

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from sqlalchemy import extract, func

from . import r2
from .extensions import db
from .models import Entry

bp = Blueprint("entries", __name__)


def _parse_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        abort(404)


def _parse_month(value: str) -> tuple[int, int] | None:
    try:
        d = datetime.strptime(value, "%Y-%m")
        return d.year, d.month
    except (ValueError, TypeError):
        return None


def months_with_entries() -> list[tuple[int, int, int]]:
    """[(an, lună, număr intrări)], descrescător."""
    rows = (
        db.session.query(
            extract("year", Entry.entry_date).label("y"),
            extract("month", Entry.entry_date).label("m"),
            func.count().label("c"),
        )
        .group_by("y", "m")
        .order_by(db.desc("y"), db.desc("m"))
        .all()
    )
    return [(int(r.y), int(r.m), int(r.c)) for r in rows]


def archive_tree(months: list[tuple[int, int, int]]):
    """{an: [(lună, număr)]} păstrând ordinea descrescătoare."""
    tree: dict[int, list[tuple[int, int]]] = {}
    for y, m, c in months:
        tree.setdefault(y, []).append((m, c))
    return tree


def entries_for_month(year: int, month: int) -> list[Entry]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return (
        Entry.query.filter(Entry.entry_date >= start, Entry.entry_date < end)
        .order_by(Entry.entry_date.desc())
        .all()
    )


def next_month_cursor(months, year: int, month: int) -> str | None:
    """Prima lună cu intrări strict mai veche decât (year, month), ca «YYYY-MM»."""
    for y, m, _ in months:
        if (y, m) < (year, month):
            return f"{y:04d}-{m:02d}"
    return None


def display_url(photo) -> str:
    return r2.presign_get(photo.r2_key_display)


@bp.app_context_processor
def inject_helpers():
    return {"display_url": display_url, "today": date.today}


@bp.route("/")
@login_required
def index():
    months = months_with_entries()
    start = None
    requested = _parse_month(request.args.get("month", ""))
    if requested and any((y, m) == requested for y, m, _ in months):
        start = requested
    elif months:
        start = (months[0][0], months[0][1])

    month_sections = []
    next_cursor = None
    if start:
        month_sections.append(
            {
                "year": start[0],
                "month": start[1],
                "entries": entries_for_month(*start),
            }
        )
        next_cursor = next_month_cursor(months, *start)

    return render_template(
        "timeline.html",
        month_sections=month_sections,
        next_cursor=next_cursor,
        archive=archive_tree(months),
        has_entries=bool(months),
    )


@bp.route("/timeline/partial")
@login_required
def timeline_partial():
    parsed = _parse_month(request.args.get("month", ""))
    if not parsed:
        return jsonify({"error": "lună invalidă"}), 400
    year, month = parsed
    months = months_with_entries()
    entries = entries_for_month(year, month)
    html = render_template(
        "_month.html", section={"year": year, "month": month, "entries": entries}
    )
    return jsonify({"html": html, "next": next_month_cursor(months, year, month)})


@bp.route("/entry/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        entry_date = _parse_iso_date(request.form.get("entry_date", ""))
        title = request.form.get("title", "").strip() or None
        body = request.form.get("body", "").rstrip()
        if not body:
            flash("Textul intrării nu poate fi gol.", "error")
            return render_template(
                "entry_form.html", entry=None, form_date=entry_date,
                form_title=title or "", form_body=body,
            )
        existing = Entry.query.filter_by(entry_date=entry_date).first()
        if existing:
            # Nu redirectăm: textul tastat s-ar pierde. Rămânem în formular
            # și oferim un link spre intrarea existentă.
            return render_template(
                "entry_form.html", entry=None, form_date=entry_date,
                form_title=title or "", form_body=body,
                existing_url=url_for(
                    "entries.edit", date_str=existing.entry_date.isoformat()
                ),
            )
        entry = Entry(entry_date=entry_date, title=title, body=body)
        db.session.add(entry)
        db.session.commit()
        flash("Intrarea a fost salvată. Poți adăuga poze mai jos.", "success")
        return redirect(url_for("entries.edit", date_str=entry.entry_date.isoformat()))

    default_date = _parse_iso_date(request.args.get("date", date.today().isoformat()))
    return render_template(
        "entry_form.html", entry=None, form_date=default_date, form_title="", form_body=""
    )


@bp.route("/entry/<date_str>")
@login_required
def detail(date_str):
    entry_date = _parse_iso_date(date_str)
    entry = Entry.query.filter_by(entry_date=entry_date).first_or_404()
    prev_entry = (
        Entry.query.filter(Entry.entry_date < entry.entry_date)
        .order_by(Entry.entry_date.desc())
        .first()
    )
    next_entry = (
        Entry.query.filter(Entry.entry_date > entry.entry_date)
        .order_by(Entry.entry_date.asc())
        .first()
    )
    photos = [
        {
            "id": p.id,
            "display": r2.presign_get(p.r2_key_display),
            "original": r2.presign_get(
                p.r2_key_original,
                download_filename=f"{entry.entry_date.isoformat()}_{p.position + 1}.jpg",
            ),
        }
        for p in entry.photos
    ]
    return render_template(
        "entry_detail.html",
        entry=entry,
        photos=photos,
        prev_entry=prev_entry,
        next_entry=next_entry,
    )


@bp.route("/entry/<date_str>/edit", methods=["GET", "POST"])
@login_required
def edit(date_str):
    entry_date = _parse_iso_date(date_str)
    entry = Entry.query.filter_by(entry_date=entry_date).first_or_404()

    form_date = entry.entry_date
    form_title = entry.title or ""
    form_body = entry.body

    if request.method == "POST":
        form_date = _parse_iso_date(request.form.get("entry_date", ""))
        form_title = request.form.get("title", "").strip()
        form_body = request.form.get("body", "").rstrip()
        if not form_body:
            flash("Textul intrării nu poate fi gol.", "error")
        elif (
            form_date != entry.entry_date
            and Entry.query.filter_by(entry_date=form_date).first()
        ):
            flash("Există deja o intrare pentru data aleasă.", "error")
        else:
            entry.entry_date = form_date
            entry.title = form_title or None
            entry.body = form_body
            db.session.commit()
            flash("Modificările au fost salvate.", "success")
            return redirect(
                url_for("entries.detail", date_str=entry.entry_date.isoformat())
            )

    photos = [
        {"id": p.id, "display": r2.presign_get(p.r2_key_display)}
        for p in entry.photos
    ]
    return render_template(
        "entry_form.html",
        entry=entry,
        photos=photos,
        form_date=form_date,
        form_title=form_title,
        form_body=form_body,
    )


@bp.route("/entry/<date_str>/delete", methods=["POST"])
@login_required
def delete(date_str):
    entry_date = _parse_iso_date(date_str)
    entry = Entry.query.filter_by(entry_date=entry_date).first_or_404()
    keys = [k for p in entry.photos for k in (p.r2_key_original, p.r2_key_display)]
    r2.delete_keys(keys)
    db.session.delete(entry)
    db.session.commit()
    flash("Intrarea a fost ștearsă.", "info")
    return redirect(url_for("entries.index"))
