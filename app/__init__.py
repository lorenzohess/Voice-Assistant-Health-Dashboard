"""Health Dashboard Flask Application Factory."""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    # Default configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    
    # Database path - use data/ directory
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    db_path = os.path.join(data_dir, "health.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Override with custom config if provided
    if config:
        app.config.update(config)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
