from flask_sqlalchemy import SQLAlchemy

# Single SQLAlchemy instance shared across the app. SQLAlchemy ORM uses bound
# parameters for all queries, so this protects us from SQL injection by default.
db = SQLAlchemy()
