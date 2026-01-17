"""Food database operations with fuzzy search."""

import sqlite3
import os
from typing import Optional
from rapidfuzz import fuzz, process

# Path to the food database (separate from health data)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
FOOD_DB_PATH = os.path.join(DATA_DIR, "foods.db")


def get_food_db_connection():
    """Get a connection to the food database."""
    return sqlite3.connect(FOOD_DB_PATH)


def init_food_db():
    """Initialize the food database schema."""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY,
            fdc_id INTEGER,
            name TEXT NOT NULL,
            brand TEXT,
            serving_size REAL,
            serving_unit TEXT,
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL,
            fiber REAL,
            category TEXT
        )
    """)
    
    # Create index for faster name searches
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_name ON foods(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_category ON foods(category)")
    
    conn.commit()
    conn.close()


def search_foods(query: str, limit: int = 20) -> list[dict]:
    """
    Search foods by name using fuzzy matching.
    Returns top matches sorted by relevance.
    """
    if not query or len(query) < 2:
        return []
    
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    # First try exact substring match (faster)
    cursor.execute("""
        SELECT id, name, brand, calories, protein, carbs, fat, serving_size, serving_unit
        FROM foods 
        WHERE LOWER(name) LIKE ? 
        LIMIT 100
    """, (f"%{query.lower()}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return []
    
    # Use fuzzy matching to rank results
    foods = []
    for row in rows:
        food = {
            "id": row[0],
            "name": row[1],
            "brand": row[2],
            "calories": row[3],
            "protein": row[4],
            "carbs": row[5],
            "fat": row[6],
            "serving_size": row[7],
            "serving_unit": row[8],
        }
        # Calculate fuzzy score
        food["score"] = fuzz.WRatio(query.lower(), row[1].lower())
        foods.append(food)
    
    # Sort by score and return top results
    foods.sort(key=lambda x: x["score"], reverse=True)
    return foods[:limit]


def get_food_by_id(food_id: int) -> Optional[dict]:
    """Get a food item by ID."""
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, brand, calories, protein, carbs, fat, 
               serving_size, serving_unit, fiber, category
        FROM foods WHERE id = ?
    """, (food_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        "id": row[0],
        "name": row[1],
        "brand": row[2],
        "calories": row[3],
        "protein": row[4],
        "carbs": row[5],
        "fat": row[6],
        "serving_size": row[7],
        "serving_unit": row[8],
        "fiber": row[9],
        "category": row[10],
    }


def add_custom_food(
    name: str,
    calories: float,
    protein: float = None,
    carbs: float = None,
    fat: float = None,
    serving_size: float = 100,
    serving_unit: str = "g",
    brand: str = None,
    category: str = "custom"
) -> int:
    """Add a custom food to the database. Returns the new food ID."""
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO foods (name, brand, serving_size, serving_unit, calories, protein, carbs, fat, category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, brand, serving_size, serving_unit, calories, protein, carbs, fat, category))
    
    food_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return food_id


def get_food_count() -> int:
    """Get the total number of foods in the database."""
    if not os.path.exists(FOOD_DB_PATH):
        return 0
    
    conn = get_food_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM foods")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_food_categories() -> list[str]:
    """Get all unique food categories."""
    conn = get_food_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM foods WHERE category IS NOT NULL ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories
