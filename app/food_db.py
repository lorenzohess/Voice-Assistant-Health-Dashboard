"""Food database operations with fuzzy search and calorie computation."""

import sqlite3
import os
import re
from typing import Optional
from rapidfuzz import fuzz

# Path to the food database (separate from health data)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
FOOD_DB_PATH = os.path.join(DATA_DIR, "foods.db")

# Unit conversion factors
# Mass units to grams
MASS_CONVERSIONS = {
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "oz": 28.35,
    "ounce": 28.35,
    "ounces": 28.35,
    "lb": 453.6,
    "lbs": 453.6,
    "pound": 453.6,
    "pounds": 453.6,
    "kg": 1000.0,
    "kilogram": 1000.0,
    "kilograms": 1000.0,
}

# Volume units to ml
VOLUME_CONVERSIONS = {
    "ml": 1.0,
    "milliliter": 1.0,
    "milliliters": 1.0,
    "l": 1000.0,
    "liter": 1000.0,
    "liters": 1000.0,
    "cup": 236.6,
    "cups": 236.6,
    "tbsp": 14.79,
    "tablespoon": 14.79,
    "tablespoons": 14.79,
    "tsp": 4.93,
    "teaspoon": 4.93,
    "teaspoons": 4.93,
    "fl oz": 29.57,
    "fl_oz": 29.57,
    "fluid ounce": 29.57,
    "fluid ounces": 29.57,
}

# Piece units (no conversion needed)
PIECE_UNITS = {"piece", "pieces", "item", "items", "serving", "servings", "slice", "slices"}


def get_food_db_connection():
    """Get a connection to the food database."""
    return sqlite3.connect(FOOD_DB_PATH)


def init_food_db():
    """Initialize the food database schema."""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    # Main foods table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY,
            fdc_id INTEGER,
            name TEXT NOT NULL,
            calories_per_unit REAL NOT NULL,
            unit_type TEXT NOT NULL DEFAULT 'mass',
            canonical_unit TEXT NOT NULL DEFAULT 'g',
            category TEXT
        )
    """)
    
    # Aliases table for natural language matching
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_aliases (
            id INTEGER PRIMARY KEY,
            food_id INTEGER NOT NULL,
            alias TEXT NOT NULL,
            FOREIGN KEY (food_id) REFERENCES foods(id) ON DELETE CASCADE,
            UNIQUE(food_id, alias)
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_name ON foods(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_category ON foods(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alias_text ON food_aliases(alias)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alias_food ON food_aliases(food_id)")
    
    conn.commit()
    conn.close()


def get_unit_type(unit: str) -> Optional[str]:
    """Determine if unit is mass, volume, or piece."""
    unit_lower = unit.lower().strip()
    if unit_lower in MASS_CONVERSIONS:
        return "mass"
    elif unit_lower in VOLUME_CONVERSIONS:
        return "volume"
    elif unit_lower in PIECE_UNITS:
        return "piece"
    return None


def convert_to_canonical(quantity: float, unit: str) -> tuple[float, str, str]:
    """
    Convert quantity to canonical unit.
    Returns (converted_quantity, canonical_unit, unit_type)
    """
    unit_lower = unit.lower().strip()
    
    if unit_lower in MASS_CONVERSIONS:
        factor = MASS_CONVERSIONS[unit_lower]
        return (quantity * factor, "g", "mass")
    elif unit_lower in VOLUME_CONVERSIONS:
        factor = VOLUME_CONVERSIONS[unit_lower]
        return (quantity * factor, "ml", "volume")
    elif unit_lower in PIECE_UNITS:
        return (quantity, "piece", "piece")
    else:
        # Unknown unit, assume it's a valid canonical unit
        return (quantity, unit_lower, "unknown")


def parse_quantity(text: str) -> dict:
    """
    Parse quantity text like '2.5 cups' or '150g' into quantity and unit.
    Returns {'quantity': float, 'unit': str, 'valid': bool}
    """
    if not text:
        return {"quantity": None, "unit": None, "valid": False}
    
    text = text.strip().lower()
    
    # Pattern: number (with optional decimal) followed by optional space and unit
    # Examples: "150g", "2.5 cups", "1 piece", "100 g"
    pattern = r'^(\d+\.?\d*)\s*(.+)$'
    match = re.match(pattern, text)
    
    if not match:
        return {"quantity": None, "unit": None, "valid": False}
    
    try:
        quantity = float(match.group(1))
        unit = match.group(2).strip()
        
        # Validate unit
        unit_type = get_unit_type(unit)
        if unit_type is None:
            return {"quantity": quantity, "unit": unit, "valid": False, "error": f"Unknown unit: {unit}"}
        
        return {"quantity": quantity, "unit": unit, "unit_type": unit_type, "valid": True}
    except ValueError:
        return {"quantity": None, "unit": None, "valid": False}


def compute_calories(food_id: int, quantity: float, unit: str) -> dict:
    """
    Compute calories for a given food and quantity.
    Returns {'calories': float, 'food_name': str, 'computed': bool, 'error': str|None}
    """
    food = get_food_by_id(food_id)
    if not food:
        return {"calories": None, "computed": False, "error": "Food not found"}
    
    # Convert input quantity to canonical unit
    converted_qty, canonical_unit, input_unit_type = convert_to_canonical(quantity, unit)
    
    # Check if unit types match
    if input_unit_type != food["unit_type"]:
        return {
            "calories": None,
            "computed": False,
            "error": f"Unit mismatch: food uses {food['unit_type']} ({food['canonical_unit']}), but you specified {input_unit_type} ({unit})"
        }
    
    # Compute calories
    # calories = quantity_in_canonical_units * calories_per_unit
    calories = converted_qty * food["calories_per_unit"]
    
    return {
        "calories": round(calories, 1),
        "food_name": food["name"],
        "food_id": food_id,
        "quantity": quantity,
        "unit": unit,
        "computed": True,
        "error": None
    }


def search_foods(query: str, limit: int = 20) -> list[dict]:
    """
    Search foods by name and aliases using fuzzy matching.
    Returns top matches sorted by relevance.
    """
    if not query or len(query) < 2:
        return []
    
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    query_lower = query.lower()
    
    # Search in both foods and aliases
    cursor.execute("""
        SELECT DISTINCT f.id, f.name, f.calories_per_unit, f.unit_type, f.canonical_unit, f.category
        FROM foods f
        LEFT JOIN food_aliases a ON f.id = a.food_id
        WHERE LOWER(f.name) LIKE ? OR LOWER(a.alias) LIKE ?
        LIMIT 200
    """, (f"%{query_lower}%", f"%{query_lower}%"))
    
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
            "calories_per_unit": row[2],
            "unit_type": row[3],
            "canonical_unit": row[4],
            "category": row[5],
            # For UI compatibility - show calories for 1 canonical unit
            "calories": row[2],
            "serving_size": 1,
            "serving_unit": row[4],
        }
        # Calculate fuzzy score against food name
        food["score"] = fuzz.WRatio(query_lower, row[1].lower())
        foods.append(food)
    
    # Sort by score and return top results
    foods.sort(key=lambda x: x["score"], reverse=True)
    return foods[:limit]


def get_food_by_id(food_id: int) -> Optional[dict]:
    """Get a food item by ID."""
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, calories_per_unit, unit_type, canonical_unit, category, fdc_id
        FROM foods WHERE id = ?
    """, (food_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        "id": row[0],
        "name": row[1],
        "calories_per_unit": row[2],
        "unit_type": row[3],
        "canonical_unit": row[4],
        "category": row[5],
        "fdc_id": row[6],
    }


def add_food(
    name: str,
    calories_per_unit: float,
    unit_type: str = "mass",
    canonical_unit: str = "g",
    category: str = None,
    fdc_id: int = None,
    aliases: list[str] = None
) -> int:
    """Add a food to the database. Returns the new food ID."""
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO foods (name, calories_per_unit, unit_type, canonical_unit, category, fdc_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, calories_per_unit, unit_type, canonical_unit, category, fdc_id))
    
    food_id = cursor.lastrowid
    
    # Add aliases if provided
    if aliases:
        for alias in aliases:
            try:
                cursor.execute("""
                    INSERT INTO food_aliases (food_id, alias) VALUES (?, ?)
                """, (food_id, alias.lower()))
            except sqlite3.IntegrityError:
                pass  # Ignore duplicate aliases
    
    conn.commit()
    conn.close()
    
    return food_id


def add_alias(food_id: int, alias: str) -> bool:
    """Add an alias to a food. Returns True if successful."""
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO food_aliases (food_id, alias) VALUES (?, ?)
        """, (food_id, alias.lower()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def get_food_aliases(food_id: int) -> list[str]:
    """Get all aliases for a food."""
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT alias FROM food_aliases WHERE food_id = ?", (food_id,))
    aliases = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return aliases


def get_food_count() -> int:
    """Get the total number of foods in the database."""
    if not os.path.exists(FOOD_DB_PATH):
        return 0
    
    try:
        conn = get_food_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM foods")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except sqlite3.OperationalError:
        return 0


def get_food_categories() -> list[str]:
    """Get all unique food categories."""
    conn = get_food_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM foods WHERE category IS NOT NULL ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories


# Keep old function name for compatibility with routes.py
def add_custom_food(
    name: str,
    calories: float,
    serving_size: float = 100,
    serving_unit: str = "g",
    brand: str = None,
    category: str = "custom",
    **kwargs  # Ignore old macro arguments
) -> int:
    """Legacy function for adding custom food. Converts to new schema."""
    # Determine unit type from serving_unit
    unit_type = get_unit_type(serving_unit) or "mass"
    
    # Convert calories to calories_per_canonical_unit
    if unit_type == "mass":
        canonical_unit = "g"
        # Convert from serving_size/serving_unit to per gram
        converted, _, _ = convert_to_canonical(serving_size, serving_unit)
        calories_per_unit = calories / converted if converted > 0 else calories
    elif unit_type == "volume":
        canonical_unit = "ml"
        converted, _, _ = convert_to_canonical(serving_size, serving_unit)
        calories_per_unit = calories / converted if converted > 0 else calories
    else:
        canonical_unit = "piece"
        calories_per_unit = calories / serving_size if serving_size > 0 else calories
    
    return add_food(
        name=name,
        calories_per_unit=calories_per_unit,
        unit_type=unit_type,
        canonical_unit=canonical_unit,
        category=category,
    )
