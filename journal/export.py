import io
from datetime import date, datetime

from flask import Blueprint, flash, render_template, request, send_file
from flask_login import login_required

from . import r2
from .models import Entry

bp = Blueprint("export", __name__)


def _parse(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@bp.route("/export", methods=["GET", "POST"])
@login_required
def export():
    if request.method == "POST":
        start = _parse(request.form.get("start_date", ""))
        end = _parse(request.form.get("end_date", ""))
        if not start or not end or start > end:
            flash("Interval de date invalid.", "error")
            return render_template("export.html")

        entries = (
            Entry.query.filter(Entry.entry_date >= start, Entry.entry_date <= end)
            .order_by(Entry.entry_date.asc())
            .all()
        )
        if not entries:
            flash("Nu există intrări în intervalul ales.", "info")
            return render_template("export.html")

        # WeasyPrint descarcă pozele direct din R2 prin presigned GET URLs.
        sections = [
            {
                "entry": e,
                "photo_urls": [r2.presign_get(p.r2_key_display) for p in e.photos],
            }
            for e in entries
        ]
        html = render_template(
            "pdf.html", sections=sections, start=start, end=end, generated=date.today()
        )

        # Import leneș: WeasyPrint are nevoie de biblioteci de sistem (pango etc.)
        # care pot lipsi în dezvoltare locală; restul aplicației merge fără ele.
        from weasyprint import HTML

        pdf_bytes = HTML(string=html).write_pdf()
        filename = f"jurnal_{start.isoformat()}_{end.isoformat()}.pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    return render_template("export.html")
