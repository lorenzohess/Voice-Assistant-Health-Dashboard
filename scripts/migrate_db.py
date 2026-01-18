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
        print(f"\nHealth DB migration complete! {changes} columns added.")
    else:
        print("\nHealth DB: No migrations needed.")


def migrate_food_db():
    """Apply migrations to foods.db."""
    FOOD_DB = DATA_DIR / "foods.db"
    
    if not FOOD_DB.exists():
        print(f"Food database not found: {FOOD_DB}")
        print("Run import_usda.py to create it.")
        return
    
    print(f"Migrating: {FOOD_DB}")
    
    conn = sqlite3.connect(FOOD_DB)
    cursor = conn.cursor()
    
    changes = 0
    
    # Check if foods table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='foods'")
    if cursor.fetchone():
        # Add new schema columns
        if add_column_if_missing(cursor, "foods", "calories_per_unit", "REAL"):
            # Migrate data: if old 'calories' column exists, copy as calories_per_unit / 100
            try:
                cursor.execute("UPDATE foods SET calories_per_unit = calories / 100.0 WHERE calories_per_unit IS NULL AND calories IS NOT NULL")
                print("  Migrated calories -> calories_per_unit")
            except:
                pass
            changes += 1
        
        if add_column_if_missing(cursor, "foods", "unit_type", "TEXT", "'mass'"):
            changes += 1
        
        if add_column_if_missing(cursor, "foods", "canonical_unit", "TEXT", "'g'"):
            changes += 1
    
    # Create food_aliases table if missing
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='food_aliases'")
    if not cursor.fetchone():
        print("  Creating food_aliases table...")
        cursor.execute("""
            CREATE TABLE food_aliases (
                id INTEGER PRIMARY KEY,
                food_id INTEGER NOT NULL,
                alias TEXT NOT NULL,
                FOREIGN KEY (food_id) REFERENCES foods(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alias ON food_aliases(alias)")
        changes += 1
    
    # Create unit_conversions table if missing
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='unit_conversions'")
    if not cursor.fetchone():
        print("  Creating unit_conversions table...")
        cursor.execute("""
            CREATE TABLE unit_conversions (
                from_unit TEXT NOT NULL,
                to_unit TEXT NOT NULL,
                factor REAL NOT NULL,
                PRIMARY KEY (from_unit, to_unit)
            )
        """)
        # Insert standard conversions
        conversions = [
            ('oz', 'g', 28.35),
            ('lb', 'g', 453.6),
            ('kg', 'g', 1000),
            ('cup', 'ml', 236.6),
            ('tbsp', 'ml', 14.79),
            ('tsp', 'ml', 4.93),
            ('fl oz', 'ml', 29.57),
        ]
        cursor.executemany("INSERT OR IGNORE INTO unit_conversions VALUES (?, ?, ?)", conversions)
        changes += 1
    
    conn.commit()
    conn.close()
    
    if changes > 0:
        print(f"\nFood DB migration complete! {changes} changes made.")
    else:
        print("\nFood DB: No migrations needed.")


if __name__ == "__main__":
    migrate_health_db()
    migrate_food_db()
