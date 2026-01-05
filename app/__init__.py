"""Flask application package."""

from __future__ import annotations

from flask import Flask

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]

def create_app() -> Flask:
    """Application factory.

    Returns:
        Configured Flask application.
    """
    if load_dotenv is not None:
        load_dotenv()

    from app.config import get_config
    from app.db import init_db
    from app.error_handlers import register_error_handlers
    from app.logging_config import configure_logging
    from app.routes.analysis import analysis_bp
    from app.routes.draw import draw_bp
    from app.routes.health import health_bp
    from app.routes.items import items_bp
    from app.routes.web import web_bp

    app = Flask(__name__)
    app.config.from_object(get_config())

    configure_logging(app)
    init_db(app)
    register_error_handlers(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(items_bp, url_prefix="/api")
    app.register_blueprint(draw_bp)

    return app
