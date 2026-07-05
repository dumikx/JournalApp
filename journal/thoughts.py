from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func

from .extensions import db
from .models import Thought

bp = Blueprint("thoughts", __name__)


def _topics_with_counts():
    """[(temă, număr gânduri)], cele mai folosite primele."""
    rows = (
        db.session.query(Thought.topic, func.count().label("c"))
        .filter(Thought.topic.isnot(None))
        .group_by(Thought.topic)
        .order_by(db.desc("c"), Thought.topic)
        .all()
    )
    return [(t, int(c)) for t, c in rows]


@bp.route("/ganduri")
@login_required
def index():
    active_topic = request.args.get("tema", "").strip()
    query = Thought.query.order_by(Thought.created_at.desc())
    if active_topic:
        query = query.filter(Thought.topic == active_topic)
    return render_template(
        "thoughts.html",
        thoughts=query.all(),
        topics=_topics_with_counts(),
        active_topic=active_topic,
    )


@bp.route("/ganduri/new", methods=["POST"])
@login_required
def create():
    body = request.form.get("body", "").strip()
    topic = request.form.get("topic", "").strip() or None
    if not body:
        flash("Gândul nu poate fi gol.", "error")
        return redirect(url_for("thoughts.index"))
    db.session.add(Thought(body=body, topic=topic))
    db.session.commit()
    return redirect(url_for("thoughts.index"))


@bp.route("/ganduri/<int:thought_id>/edit", methods=["GET", "POST"])
@login_required
def edit(thought_id):
    thought = db.get_or_404(Thought, thought_id)
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        topic = request.form.get("topic", "").strip() or None
        if not body:
            flash("Gândul nu poate fi gol.", "error")
        else:
            thought.body = body
            thought.topic = topic
            db.session.commit()
            flash("Gândul a fost salvat.", "success")
            return redirect(url_for("thoughts.index"))
    return render_template("thought_form.html", thought=thought)


@bp.route("/ganduri/<int:thought_id>/delete", methods=["POST"])
@login_required
def delete(thought_id):
    thought = db.get_or_404(Thought, thought_id)
    db.session.delete(thought)
    db.session.commit()
    flash("Gândul a fost șters.", "info")
    return redirect(url_for("thoughts.index"))
