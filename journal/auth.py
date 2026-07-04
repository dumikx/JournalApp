import hmac

import bcrypt
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import UserMixin, current_user, login_required, login_user, logout_user

from .extensions import limiter, login_manager

bp = Blueprint("auth", __name__)

# Hash valid al unei parole aleatoare; folosit doar ca verificarea să coste
# la fel de mult și când username-ul e greșit (evită timing side-channel).
_DUMMY_HASH = b"$2b$12$C6UzMDM.H6dfI/f/IKcEeO7ZFDCLxbF2mPuCkAJxRLJqLvIWDgQpe"


class User(UserMixin):
    """Singurul utilizator al aplicației; identitatea vine din env vars."""

    id = "1"


@login_manager.user_loader
def load_user(user_id):
    return User() if user_id == "1" else None


def _check_credentials(username: str, password: str) -> bool:
    expected_user = current_app.config["JOURNAL_USER"]
    password_hash = current_app.config["JOURNAL_PASSWORD_HASH"]
    if not expected_user or not password_hash:
        return False
    if not hmac.compare_digest(username.encode("utf-8"), expected_user.encode("utf-8")):
        bcrypt.checkpw(password.encode("utf-8"), _DUMMY_HASH)
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per 15 minutes", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("entries.index"))
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if _check_credentials(username, password):
            login_user(User(), remember=True)
            next_url = request.args.get("next", "")
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("entries.index"))
        flash("Utilizator sau parolă greșite.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Te-ai deconectat.", "info")
    return redirect(url_for("auth.login"))
