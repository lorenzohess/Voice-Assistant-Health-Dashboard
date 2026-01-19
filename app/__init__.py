"""Health Dashboard Flask Application Factory."""

import json
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def load_app_config(data_dir: str) -> dict:
    """Load application config from data/config.json."""
    config_path = os.path.join(data_dir, "config.json")
    default_config = {"database": "health.db"}
    
    if not os.path.exists(config_path):
        return default_config
    
    try:
        with open(config_path, "r") as f:
            return {**default_config, **json.load(f)}
    except (json.JSONDecodeError, IOError):
        return default_config


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
    # Database name can be set in data/config.json: {"database": "private-health.db"}
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    app_config = load_app_config(data_dir)
    db_path = os.path.join(data_dir, app_config["database"])
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
    
    # Initialize food database
    from app.food_db import init_food_db
    init_food_db()

    return app
