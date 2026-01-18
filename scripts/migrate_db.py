#!/usr/bin/env python3
"""
Database migration script.
Adds missing columns to existing tables without losing data.

Usage:
    python scripts/migrate_db.py
"""

import sqlite3
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = Path(__file__).parent.parent / "data"
HEALTH_DB = DATA_DIR / "health.db"


def get_table_columns(cursor, table_name):
    """Get list of column names for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def add_column_if_missing(cursor, table_name, column_name, column_type, default=None):
    """Add column to table if it doesn't exist."""
    columns = get_table_columns(cursor, table_name)
    
    if column_name not in columns:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}{default_clause}"
        print(f"  Adding column: {table_name}.{column_name}")
        cursor.execute(sql)
        return True
    else:
        print(f"  Column exists: {table_name}.{column_name}")
        return False


def migrate_health_db():
    """Apply migrations to health.db."""
    if not HEALTH_DB.exists():
        print(f"Database not found: {HEALTH_DB}")
        print("Run the app first to create the database.")
        return
    
    print(f"Migrating: {HEALTH_DB}")
    
    conn = sqlite3.connect(HEALTH_DB)
    cursor = conn.cursor()
    
    changes = 0
    
    # Check if calorie_entries table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='calorie_entries'")
    if cursor.fetchone():
        # Add quantity column
        if add_column_if_missing(cursor, "calorie_entries", "quantity", "TEXT"):
            changes += 1
        
        # Add food_id column
        if add_column_if_missing(cursor, "calorie_entries", "food_id", "INTEGER"):
            changes += 1
        
        # Add meal_type column if missing
        if add_column_if_missing(cursor, "calorie_entries", "meal_type", "TEXT"):
            changes += 1
    
    # Check if meal_presets table exists and needs updates
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meal_presets'")
    if cursor.fetchone():
        # Add quantity column
        if add_column_if_missing(cursor, "meal_presets", "quantity", "TEXT"):
            changes += 1
        
        # Add food_id column
        if add_column_if_missing(cursor, "meal_presets", "food_id", "INTEGER"):
            changes += 1
    
    conn.commit()
    conn.close()
    
    if changes > 0:
        print(f"\nMigration complete! {changes} columns added.")
    else:
        print("\nNo migrations needed. Database is up to date.")


if __name__ == "__main__":
    migrate_health_db()
