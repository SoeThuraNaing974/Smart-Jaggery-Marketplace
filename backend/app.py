import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from db import db


def create_app(config_overrides=None):
    """Create and configure the Flask application.
    
    Reads DATABASE_URL from environment and properly initializes SQLAlchemy.
    """
    app = Flask(__name__)
    
    # Load base config
    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH
    
    if config_overrides:
        app.config.update(config_overrides)

    # =========================
    # Database Configuration
    # =========================
    # CRITICAL: Read DATABASE_URL from environment BEFORE initializing db
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    # Convert old PostgreSQL URL format if necessary
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize Flask-SQLAlchemy AFTER setting the database URI
    db.init_app(app)
    
    # =========================
    # CORS Configuration
    # =========================
    CORS(app, supports_credentials=True,
         origins=["http://localhost:3000", "http://127.0.0.1:3000"])

    # =========================
    # Import Models
    # =========================
    from models import User, Warehouse, JaggeryBatch, Order, OrderItem, Promotion  # noqa: F401

    # =========================
    # Register Blueprints
    # =========================
    from routes.auth_routes import bp as auth_bp
    from routes.customer import bp as customer_bp
    from routes.warehouse import bp as warehouse_bp
    from routes.admin import bp as admin_bp
    from routes.messages import bp as messages_bp
    from consolidated import bp as consolidated_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(warehouse_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(consolidated_bp)

    # =========================
    # Error Handlers & Routes
    # =========================
    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/uploads/<path:filename>")
    def uploads(filename):
        return send_from_directory(Config.UPLOAD_FOLDER, filename)

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"error": "file too large (max 10MB)"}), 413

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "not found"}), 404

    # =========================
    # Database Initialization
    # =========================
    def _ensure_new_columns():
        """Migrate existing tables to add any new columns."""
        from sqlalchemy import inspect, text
        insp = inspect(db.engine)
        cols = {c["name"] for c in insp.get_columns("jaggery_batches")}
        if "deleted_by" not in cols:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE jaggery_batches ADD COLUMN deleted_by VARCHAR(10)"))
                conn.execute(text("UPDATE jaggery_batches SET deleted_by = 'warehouse' "
                                  "WHERE deleted_at IS NOT NULL AND deleted_by IS NULL"))
        if db.engine.dialect.name == "postgresql":
            for uc in insp.get_unique_constraints("jaggery_batches"):
                if uc.get("column_names") == ["batch_id"] and uc.get("name"):
                    with db.engine.begin() as conn:
                        conn.execute(text(f'ALTER TABLE jaggery_batches DROP CONSTRAINT "{uc["name"]}"'))

    with app.app_context():
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        db.create_all()
        _ensure_new_columns()
        if os.getenv("SEED_DEMO", "").lower() in ("1", "true", "yes"):
            from seed import seed_demo
            seed_demo()

    return app


if __name__ == "__main__":
    _debug = os.environ.get("FLASK_DEBUG") == "1"
    create_app().run(host="127.0.0.1", port=5000, threaded=True, debug=_debug)

