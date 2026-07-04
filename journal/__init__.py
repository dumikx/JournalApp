from pathlib import Path

import click
from flask import Flask
from markupsafe import Markup, escape

from config import Config
from .dates_ro import format_date_long, format_date_short, format_month_year
from .extensions import csrf, db, limiter, login_manager, migrate


BASE_DIR = Path(__file__).resolve().parent.parent


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Autentifică-te pentru a continua."

    from . import models  # noqa: F401  (înregistrează modelele pentru migrații)
    from .auth import bp as auth_bp
    from .entries import bp as entries_bp
    from .photos_api import bp as photos_bp
    from .search import bp as search_bp
    from .export import bp as export_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(entries_bp)
    app.register_blueprint(photos_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(export_bp)

    app.jinja_env.filters["data_lunga"] = format_date_long
    app.jinja_env.filters["data_scurta"] = format_date_short
    app.jinja_env.globals["luna_an"] = format_month_year

    @app.template_filter("nl2br")
    def nl2br(text):
        # body e text simplu; păstrăm doar newline-urile (white-space: pre-wrap
        # în CSS face restul), filtrul există pentru contextele fără CSS.
        return Markup("<br>".join(escape(text).splitlines()))

    @app.cli.command("create-password-hash")
    @click.argument("password")
    def create_password_hash(password):
        """Afișează hash-ul bcrypt pentru env var-ul JOURNAL_PASSWORD_HASH."""
        import bcrypt

        click.echo(bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode())

    return app
