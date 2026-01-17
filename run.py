#!/usr/bin/env python3
"""Run the Health Dashboard Flask application."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Development server
    # For production on Pi, use: gunicorn -b 0.0.0.0:5000 run:app
    app.run(host="0.0.0.0", port=5000, debug=True)
