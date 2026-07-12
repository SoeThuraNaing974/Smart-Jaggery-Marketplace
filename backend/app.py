import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from db import db


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

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(warehouse_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(messages_bp)

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
