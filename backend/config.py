import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_url():
    """Read DATABASE_URL; normalise the scheme so SQLAlchemy/psycopg2 accept it.
    Cloud hosts (Render, Railway, Heroku) hand out 'postgres://' which SQLAlchemy
    no longer recognises — it must be 'postgresql://'."""
    url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/jaggery_db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    # postgresql://user:password@host:port/dbname
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-prod")
    JWT_ALGO = "HS256"
    JWT_EXP_HOURS = int(os.getenv("JWT_EXP_HOURS", "12"))

    # Local file storage for batch quality certificates (PDF)
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))
    ALLOWED_EXTENSIONS = {"pdf"}
    IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "avif"}
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

    # Perishability: > EXPIRY_MONTHS old = EXPIRED (cannot order);
    # between NEAR_EXPIRY_MONTHS and EXPIRY_MONTHS = "near expiry" warning.
    EXPIRY_MONTHS = 9
    NEAR_EXPIRY_MONTHS = 8
    LOW_STOCK_KG = 50
    # Flat home-delivery fee when no per-region charge is configured (pickup is free).
    DEFAULT_DELIVERY_FEE = float(os.getenv("DEFAULT_DELIVERY_FEE", "2"))

    # Foreign (international) delivery, in Kyats: every foreign fee stays inside
    # this band, and each shipping country has its own default fee by distance —
    # used whenever the admin hasn't priced that exact country on the
    # delivery-charges page. Keys are lowercase country names as they appear in
    # the checkout dropdown (frontend/lib/locations.js COUNTRIES).
    FOREIGN_FEE_MIN = 20000
    FOREIGN_FEE_MAX = 50000
    FOREIGN_COUNTRY_FEES = {
        # neighbours / mainland South-East Asia
        "thailand": 20000, "laos": 20000, "bangladesh": 22000, "cambodia": 22000,
        "india": 24000, "vietnam": 24000, "china": 25000,
        # wider South / South-East Asia
        "malaysia": 26000, "sri lanka": 26000, "nepal": 26000, "singapore": 28000,
        "indonesia": 30000, "philippines": 30000,
        # East Asia
        "south korea": 36000, "japan": 38000,
        # Middle East
        "united arab emirates": 34000, "qatar": 34000, "saudi arabia": 36000,
        # Oceania / Europe / Americas
        "australia": 42000,
        "united kingdom": 46000, "germany": 46000, "france": 46000,
        "united states": 50000, "canada": 50000,
    }
    PG_BIN = os.getenv("PG_BIN", r"C:\Program Files\PostgreSQL\16\bin")
    PG_PORT = os.getenv("PG_PORT", "5433")

    # SMTP for real email sending. If SMTP_HOST is blank, email runs in dry-run
    # mode (no send, just reports recipient count) so the app still works locally.
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@jaggery.local")
    SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() == "true"

    # Subscription payment methods (mobile wallets + bank). No live gateway here:
    # a payment is recorded with its transaction reference and confirmed.
    PAYMENT_METHODS = {"kpay", "wavepay", "ayapay", "cbpay", "yomapay", "bank"}
    # Merchant accounts shown to the payer on the checkout page.
    MERCHANT_ACCOUNTS = {
        "kpay": os.getenv("PAY_KPAY", "09-7xx-xxx-xxx (Smart Jaggery Mart)"),
        "wavepay": os.getenv("PAY_WAVE", "09-7xx-xxx-xxx (Smart Jaggery Mart)"),
        "ayapay": os.getenv("PAY_AYA", "09-7xx-xxx-xxx (Smart Jaggery Mart)"),
        "cbpay": os.getenv("PAY_CB", "09-7xx-xxx-xxx (Smart Jaggery Mart)"),
        "yomapay": os.getenv("PAY_YOMA", "09-7xx-xxx-xxx (Smart Jaggery Mart)"),
        "bank": os.getenv("PAY_BANK", "AYA Bank — 1234 5678 9012 (Smart Jaggery Mart Co.)"),
    }
