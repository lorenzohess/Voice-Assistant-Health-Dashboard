#!/usr/bin/env python3
"""
Import USDA FoodData Central data into the local food database.

This script downloads the USDA SR Legacy dataset (~7500 common foods)
and imports it into SQLite with the new schema (calories per gram).

Usage:
    python scripts/import_usda.py [--limit N] [--keep-existing]

Options:
    --limit N        Only import top N foods (by calorie data quality)
    --keep-existing  Don't delete existing foods, just add new ones
"""

import csv
import os
import sys
import sqlite3
import urllib.request
import zipfile
import tempfile
import argparse
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.food_db import init_food_db, get_food_db_connection

DATA_DIR = Path(__file__).parent.parent / "data"
FOOD_DB_PATH = DATA_DIR / "foods.db"

# USDA FoodData Central SR Legacy dataset
USDA_URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip"


def download_usda_data(temp_dir: str) -> str:
    """Download USDA dataset to temp directory."""
    zip_path = os.path.join(temp_dir, "usda_data.zip")
    
    print(f"Downloading USDA SR Legacy dataset...")
    print(f"URL: {USDA_URL}")
    
    def report_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = min(100, downloaded * 100 / total_size) if total_size > 0 else 0
        print(f"\rDownloading: {percent:.1f}% ({downloaded // 1024 // 1024}MB)", end="", flush=True)
    
    urllib.request.urlretrieve(USDA_URL, zip_path, report_progress)
    print("\nDownload complete!")
    
    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    return temp_dir


def parse_nutrients(nutrient_file: str) -> dict:
    """Parse nutrient data into a dict keyed by fdc_id."""
    nutrients = {}
    
    with open(nutrient_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fdc_id = int(row['fdc_id'])
            nutrient_id = int(row['nutrient_id'])
            try:
                amount = float(row['amount']) if row['amount'] else 0
            except ValueError:
                amount = 0
            
            if fdc_id not in nutrients:
                nutrients[fdc_id] = {}
            nutrients[fdc_id][nutrient_id] = amount
    
    return nutrients


def generate_simple_aliases(name: str) -> list[str]:
    """Generate basic aliases from USDA food name."""
    aliases = []
    name_lower = name.lower()
    
    # Remove common prefixes/suffixes
    # USDA names are like "Chicken, broilers or fryers, breast, meat only, cooked, roasted"
    
    # Split by comma and take meaningful parts
    parts = [p.strip() for p in name_lower.split(',')]
    
    if parts:
        # First part is usually the main food
        main = parts[0]
        aliases.append(main)
        
        # Combine first two parts if there are more
        if len(parts) >= 2:
            aliases.append(f"{parts[0]} {parts[1]}")
        
        # Look for cooking method
        cooking_methods = ['raw', 'cooked', 'roasted', 'grilled', 'fried', 'baked', 'boiled', 'steamed']
        for part in parts:
            for method in cooking_methods:
                if method in part:
                    aliases.append(f"{method} {parts[0]}")
                    break
    
    # Remove duplicates and empty strings
    aliases = list(set(a.strip() for a in aliases if a.strip() and len(a) > 2))
    
    return aliases[:5]  # Max 5 aliases


def import_to_sqlite(temp_dir: str, limit: int = None, keep_existing: bool = False):
    """Import USDA data into SQLite database with new schema."""
    
    # Find the extracted directory
    extracted_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
    data_dir = os.path.join(temp_dir, extracted_dirs[0]) if extracted_dirs else temp_dir
    
    food_file = os.path.join(data_dir, "food.csv")
    nutrient_file = os.path.join(data_dir, "food_nutrient.csv")
    category_file = os.path.join(data_dir, "food_category.csv")
    
    if not os.path.exists(food_file):
        print(f"Error: food.csv not found in {data_dir}")
        print(f"Contents: {os.listdir(data_dir)}")
        return 0
    
    # Parse categories
    categories = {}
    if os.path.exists(category_file):
        with open(category_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                categories[int(row['id'])] = row['description']
    
    # Parse nutrients
    print("Parsing nutrient data...")
    nutrients = parse_nutrients(nutrient_file)
    
    # Nutrient IDs
    NUTRIENT_ENERGY = 1008  # kcal per 100g
    
    # Initialize database with new schema
    init_food_db()
    
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    if not keep_existing:
        print("Clearing existing data...")
        cursor.execute("DELETE FROM food_aliases")
        cursor.execute("DELETE FROM foods")
        conn.commit()
    
    # Collect foods with calorie data
    print("Reading food data...")
    foods_to_import = []
    
    with open(food_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fdc_id = int(row['fdc_id'])
            name = row['description'].strip()
            
            # Get category
            category_id = row.get('food_category_id', '')
            category = categories.get(int(category_id), None) if category_id else None
            
            # Get calories per 100g
            food_nutrients = nutrients.get(fdc_id, {})
            calories_per_100g = food_nutrients.get(NUTRIENT_ENERGY, 0)
            
            # Skip foods with no calorie data
            if calories_per_100g <= 0:
                continue
            
            # Convert to calories per gram
            calories_per_gram = calories_per_100g / 100.0
            
            foods_to_import.append({
                'fdc_id': fdc_id,
                'name': name,
                'calories_per_unit': calories_per_gram,
                'category': category,
            })
    
    # Sort by calorie value (foods with more data tend to be more common)
    # and limit if requested
    if limit:
        foods_to_import = foods_to_import[:limit]
    
    print(f"Importing {len(foods_to_import)} foods...")
    
    imported = 0
    aliases_added = 0
    
    for food in foods_to_import:
        # Insert food
        cursor.execute("""
            INSERT INTO foods (fdc_id, name, calories_per_unit, unit_type, canonical_unit, category)
            VALUES (?, ?, ?, 'mass', 'g', ?)
        """, (food['fdc_id'], food['name'], food['calories_per_unit'], food['category']))
        
        food_id = cursor.lastrowid
        
        # Generate and insert aliases
        aliases = generate_simple_aliases(food['name'])
        for alias in aliases:
            try:
                cursor.execute("""
                    INSERT INTO food_aliases (food_id, alias) VALUES (?, ?)
                """, (food_id, alias))
                aliases_added += 1
            except sqlite3.IntegrityError:
                pass  # Duplicate alias
        
        imported += 1
        if imported % 500 == 0:
            print(f"\rImported {imported} foods...", end="", flush=True)
            conn.commit()
    
    conn.commit()
    conn.close()
    
    print(f"\n\nImport complete!")
    print(f"  - Imported: {imported} foods")
    print(f"  - Generated: {aliases_added} aliases")
    print(f"  - Database: {FOOD_DB_PATH}")
    
    return imported


def add_common_foods():
    """Add common foods with better names and piece-based items."""
    conn = get_food_db_connection()
    cursor = conn.cursor()
    
    # Piece-based common foods (calories per piece)
    piece_foods = [
        ("Egg (large)", 70, "piece", "breakfast", ["egg", "eggs", "large egg"]),
        ("Egg (medium)", 60, "piece", "breakfast", ["medium egg"]),
        ("Banana (medium)", 105, "piece", "fruit", ["banana", "bananas"]),
        ("Apple (medium)", 95, "piece", "fruit", ["apple", "apples"]),
        ("Orange (medium)", 62, "piece", "fruit", ["orange", "oranges"]),
        ("Slice of bread", 75, "piece", "grain", ["bread", "toast", "slice of bread"]),
        ("Tortilla (flour, 8 inch)", 140, "piece", "grain", ["tortilla", "flour tortilla"]),
        ("Bagel", 280, "piece", "grain", ["bagel"]),
        ("English muffin", 130, "piece", "grain", ["english muffin"]),
    ]
    
    for name, cal, unit, cat, aliases in piece_foods:
        cursor.execute("""
            INSERT OR IGNORE INTO foods (name, calories_per_unit, unit_type, canonical_unit, category)
            VALUES (?, ?, 'piece', 'piece', ?)
        """, (name, cal, cat))
        
        food_id = cursor.lastrowid
        if food_id:
            for alias in aliases:
                try:
                    cursor.execute("INSERT INTO food_aliases (food_id, alias) VALUES (?, ?)", (food_id, alias))
                except sqlite3.IntegrityError:
                    pass
    
    # Volume-based common foods (calories per ml)
    volume_foods = [
        ("Whole milk", 0.63, "ml", "dairy", ["milk", "whole milk"]),
        ("Skim milk", 0.35, "ml", "dairy", ["skim milk", "nonfat milk"]),
        ("2% milk", 0.50, "ml", "dairy", ["2% milk", "reduced fat milk"]),
        ("Orange juice", 0.47, "ml", "beverage", ["orange juice", "oj"]),
        ("Coffee (black)", 0.01, "ml", "beverage", ["coffee", "black coffee"]),
        ("Olive oil", 8.84, "ml", "oil", ["olive oil", "oil"]),
    ]
    
    for name, cal, unit, cat, aliases in volume_foods:
        cursor.execute("""
            INSERT OR IGNORE INTO foods (name, calories_per_unit, unit_type, canonical_unit, category)
            VALUES (?, ?, 'volume', 'ml', ?)
        """, (name, cal, cat))
        
        food_id = cursor.lastrowid
        if food_id:
            for alias in aliases:
                try:
                    cursor.execute("INSERT INTO food_aliases (food_id, alias) VALUES (?, ?)", (food_id, alias))
                except sqlite3.IntegrityError:
                    pass
    
    conn.commit()
    conn.close()
    print(f"Added {len(piece_foods) + len(volume_foods)} common food entries with aliases")


def main():
    parser = argparse.ArgumentParser(description="Import USDA food database")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of foods to import")
    parser.add_argument("--keep-existing", action="store_true", help="Don't delete existing foods")
    args = parser.parse_args()
    
    print("=" * 60)
    print("USDA Food Database Importer")
    print("=" * 60)
    print()
    
    if args.limit:
        print(f"Limiting to {args.limit} foods")
    
    # Check if database already exists
    if FOOD_DB_PATH.exists() and not args.keep_existing:
        try:
            conn = get_food_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM foods")
            count = cursor.fetchone()[0]
            conn.close()
            
            if count > 0:
                print(f"Food database already exists with {count} foods.")
                response = input("Re-import? This will delete existing data. (y/N): ")
                if response.lower() != 'y':
                    print("Aborted.")
                    return
        except:
            pass
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            download_usda_data(temp_dir)
            imported = import_to_sqlite(temp_dir, limit=args.limit, keep_existing=args.keep_existing)
            if imported > 0:
                add_common_foods()
        except Exception as e:
            print(f"\nError during import: {e}")
            import traceback
            traceback.print_exc()
            print("\nYou can also manually add foods through the web interface.")


if __name__ == "__main__":
    main()
