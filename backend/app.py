import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from db import db

from flask_sqlalchemy import SQLAlchemy


def _ensure_new_columns():
    """Tiny in-place migration: db.create_all() creates missing TABLES but never
    adds new columns to an existing table, so columns introduced after a database
    was first created are added here."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    cols = {c["name"] for c in insp.get_columns("jaggery_batches")}
    if "deleted_by" not in cols:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE jaggery_batches ADD COLUMN deleted_by VARCHAR(10)"))
            # everything soft-deleted before this column existed was warehouse-deleted
            conn.execute(text("UPDATE jaggery_batches SET deleted_by = 'warehouse' "
                              "WHERE deleted_at IS NOT NULL AND deleted_by IS NULL"))
    # category names are no longer globally unique — drop the old constraint
    # (Postgres only; fresh databases are created without it from the model)
    if db.engine.dialect.name == "postgresql":
        for uc in insp.get_unique_constraints("jaggery_batches"):
            if uc.get("column_names") == ["batch_id"] and uc.get("name"):
                with db.engine.begin() as conn:
                    conn.execute(text(f'ALTER TABLE jaggery_batches DROP CONSTRAINT "{uc["name"]}"'))


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    # allow the EJS frontend (and direct browser calls) to talk to the API
    CORS(app, supports_credentials=True,
         origins=["http://localhost:3000", "http://127.0.0.1:3000"])

    # import models so create_all sees them
    from models import User, Warehouse, JaggeryBatch, Order, OrderItem, Promotion  # noqa: F401

    # blueprints
    from routes.auth_routes import bp as auth_bp
    from routes.customer import bp as customer_bp
    from routes.warehouse import bp as warehouse_bp
    from routes.admin import bp as admin_bp
    from routes.messages import bp as messages_bp
    # Consolidated pickup & delivery (multi-warehouse splitting, escrow, wallets).
    # Additive: new endpoints only — the single-warehouse /api/orders flow is untouched.
    from consolidated import bp as consolidated_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(warehouse_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(consolidated_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    # serve uploaded certificates for download
    @app.get("/uploads/<path:filename>")
    def uploads(filename):
        return send_from_directory(Config.UPLOAD_FOLDER, filename)

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"error": "file too large (max 10MB)"}), 413

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "not found"}), 404

    with app.app_context():
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        db.create_all()
        _ensure_new_columns()
        # A fresh hosted database (e.g. Render) has no accounts at all, and a
        # free hosting plan has no shell to run seed.py from — so with
        # SEED_DEMO=true the app seeds itself. No-op once an admin exists.
        if os.getenv("SEED_DEMO", "").lower() in ("1", "true", "yes"):
            from seed import seed_demo
            seed_demo()

    return app


if __name__ == "__main__":
    # Module-level instantiation is intentionally omitted so importing this
    # module (e.g. from tests) does not open a DB connection. Run with
    # `python app.py`; for gunicorn use `wsgi:app`.
    # threaded=True → handle several requests at once (each page makes multiple
    # API calls, so this makes the whole site much faster). debug is left OFF for
    # speed and so the interactive debugger is never exposed when hosted online.
    import os
    _debug = os.environ.get("FLASK_DEBUG") == "1"
    create_app().run(host="127.0.0.1", port=5000, threaded=True, debug=_debug)

