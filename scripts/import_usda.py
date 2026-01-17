#!/usr/bin/env python3
"""
Import USDA FoodData Central data into the local food database.

This script downloads the USDA SR Legacy dataset (smaller, ~7500 common foods)
and imports it into SQLite for offline use.

Usage:
    python scripts/import_usda.py

The script will:
1. Download the USDA SR Legacy CSV files
2. Parse and import foods with nutritional data
3. Create an indexed SQLite database for fast searching
"""

import csv
import os
import sys
import sqlite3
import urllib.request
import zipfile
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = Path(__file__).parent.parent / "data"
FOOD_DB_PATH = DATA_DIR / "foods.db"

# USDA FoodData Central SR Legacy dataset
USDA_URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip"


def download_usda_data(temp_dir: str) -> str:
    """Download USDA dataset to temp directory."""
    zip_path = os.path.join(temp_dir, "usda_data.zip")
    
    print(f"Downloading USDA SR Legacy dataset...")
    print(f"URL: {USDA_URL}")
    
    # Download with progress
    def report_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = min(100, downloaded * 100 / total_size) if total_size > 0 else 0
        print(f"\rDownloading: {percent:.1f}% ({downloaded // 1024 // 1024}MB)", end="", flush=True)
    
    urllib.request.urlretrieve(USDA_URL, zip_path, report_progress)
    print("\nDownload complete!")
    
    # Extract
    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    return temp_dir


def parse_nutrients(nutrient_file: str) -> dict:
    """Parse nutrient data into a dict keyed by (fdc_id, nutrient_id)."""
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


def import_to_sqlite(temp_dir: str):
    """Import USDA data into SQLite database."""
    
    # Find the extracted directory
    extracted_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
    if not extracted_dirs:
        # Files might be directly in temp_dir
        data_dir = temp_dir
    else:
        data_dir = os.path.join(temp_dir, extracted_dirs[0])
    
    food_file = os.path.join(data_dir, "food.csv")
    nutrient_file = os.path.join(data_dir, "food_nutrient.csv")
    category_file = os.path.join(data_dir, "food_category.csv")
    
    if not os.path.exists(food_file):
        print(f"Error: food.csv not found in {data_dir}")
        print(f"Contents: {os.listdir(data_dir)}")
        return
    
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
    
    # Nutrient IDs we care about:
    # 1008 = Energy (kcal)
    # 1003 = Protein
    # 1005 = Carbohydrates
    # 1004 = Total Fat
    # 1079 = Fiber
    NUTRIENT_ENERGY = 1008
    NUTRIENT_PROTEIN = 1003
    NUTRIENT_CARBS = 1005
    NUTRIENT_FAT = 1004
    NUTRIENT_FIBER = 1079
    
    # Initialize database
    DATA_DIR.mkdir(exist_ok=True)
    
    # Remove existing database
    if FOOD_DB_PATH.exists():
        os.remove(FOOD_DB_PATH)
    
    conn = sqlite3.connect(FOOD_DB_PATH)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE foods (
            id INTEGER PRIMARY KEY,
            fdc_id INTEGER,
            name TEXT NOT NULL,
            brand TEXT,
            serving_size REAL DEFAULT 100,
            serving_unit TEXT DEFAULT 'g',
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL,
            fiber REAL,
            category TEXT
        )
    """)
    
    # Import foods
    print("Importing foods...")
    imported = 0
    skipped = 0
    
    with open(food_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fdc_id = int(row['fdc_id'])
            name = row['description'].strip()
            
            # Get category
            category_id = row.get('food_category_id', '')
            category = categories.get(int(category_id), None) if category_id else None
            
            # Get nutrients
            food_nutrients = nutrients.get(fdc_id, {})
            calories = food_nutrients.get(NUTRIENT_ENERGY, 0)
            protein = food_nutrients.get(NUTRIENT_PROTEIN)
            carbs = food_nutrients.get(NUTRIENT_CARBS)
            fat = food_nutrients.get(NUTRIENT_FAT)
            fiber = food_nutrients.get(NUTRIENT_FIBER)
            
            # Skip foods with no calorie data
            if calories == 0:
                skipped += 1
                continue
            
            cursor.execute("""
                INSERT INTO foods (fdc_id, name, serving_size, serving_unit, calories, protein, carbs, fat, fiber, category)
                VALUES (?, ?, 100, 'g', ?, ?, ?, ?, ?, ?)
            """, (fdc_id, name, calories, protein, carbs, fat, fiber, category))
            
            imported += 1
            if imported % 1000 == 0:
                print(f"\rImported {imported} foods...", end="", flush=True)
    
    # Create indexes
    print(f"\nCreating indexes...")
    cursor.execute("CREATE INDEX idx_food_name ON foods(name)")
    cursor.execute("CREATE INDEX idx_food_category ON foods(category)")
    cursor.execute("CREATE INDEX idx_food_fdc_id ON foods(fdc_id)")
    
    conn.commit()
    conn.close()
    
    print(f"\nImport complete!")
    print(f"  - Imported: {imported} foods")
    print(f"  - Skipped (no calories): {skipped}")
    print(f"  - Database: {FOOD_DB_PATH}")


def add_common_foods():
    """Add some common foods that might be missing or have better names."""
    conn = sqlite3.connect(FOOD_DB_PATH)
    cursor = conn.cursor()
    
    common_foods = [
        # name, calories, protein, carbs, fat, category
        ("Coffee, black", 2, 0.3, 0, 0, "Beverages"),
        ("Coffee with milk", 20, 1, 2, 0.5, "Beverages"),
        ("Tea, black", 1, 0, 0, 0, "Beverages"),
        ("Water", 0, 0, 0, 0, "Beverages"),
        ("Toast, white bread", 75, 2.5, 14, 1, "Baked Products"),
        ("Toast, whole wheat", 70, 3.5, 12, 1, "Baked Products"),
        ("Scrambled eggs (2)", 180, 12, 2, 14, "Dairy and Egg Products"),
        ("Fried egg", 90, 6, 0.5, 7, "Dairy and Egg Products"),
        ("Boiled egg", 78, 6, 0.5, 5, "Dairy and Egg Products"),
        ("Oatmeal, cooked (1 cup)", 150, 5, 27, 3, "Cereal Grains and Pasta"),
        ("Greek yogurt (1 cup)", 130, 17, 8, 4, "Dairy and Egg Products"),
        ("Banana, medium", 105, 1.3, 27, 0.4, "Fruits"),
        ("Apple, medium", 95, 0.5, 25, 0.3, "Fruits"),
        ("Chicken breast, grilled (100g)", 165, 31, 0, 3.6, "Poultry Products"),
        ("Salmon, grilled (100g)", 208, 20, 0, 13, "Finfish and Shellfish Products"),
        ("Rice, white, cooked (1 cup)", 206, 4.3, 45, 0.4, "Cereal Grains and Pasta"),
        ("Rice, brown, cooked (1 cup)", 216, 5, 45, 1.8, "Cereal Grains and Pasta"),
        ("Pasta, cooked (1 cup)", 220, 8, 43, 1.3, "Cereal Grains and Pasta"),
        ("Broccoli, steamed (1 cup)", 55, 3.7, 11, 0.6, "Vegetables"),
        ("Spinach, raw (1 cup)", 7, 0.9, 1, 0.1, "Vegetables"),
        ("Avocado, half", 160, 2, 9, 15, "Fruits"),
        ("Almonds (1 oz)", 164, 6, 6, 14, "Nut and Seed Products"),
        ("Peanut butter (2 tbsp)", 188, 8, 6, 16, "Legumes"),
    ]
    
    for name, cals, prot, carbs, fat, cat in common_foods:
        cursor.execute("""
            INSERT OR IGNORE INTO foods (name, serving_size, serving_unit, calories, protein, carbs, fat, category)
            VALUES (?, 1, 'serving', ?, ?, ?, ?, ?)
        """, (name, cals, prot, carbs, fat, cat))
    
    conn.commit()
    conn.close()
    print(f"Added {len(common_foods)} common food entries")


def main():
    print("=" * 60)
    print("USDA Food Database Importer")
    print("=" * 60)
    print()
    
    # Check if database already exists
    if FOOD_DB_PATH.exists():
        conn = sqlite3.connect(FOOD_DB_PATH)
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
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            download_usda_data(temp_dir)
            import_to_sqlite(temp_dir)
            add_common_foods()
        except Exception as e:
            print(f"\nError during import: {e}")
            print("\nYou can also manually add foods through the web interface.")
            
            # Initialize empty database with schema
            DATA_DIR.mkdir(exist_ok=True)
            if not FOOD_DB_PATH.exists():
                conn = sqlite3.connect(FOOD_DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS foods (
                        id INTEGER PRIMARY KEY,
                        fdc_id INTEGER,
                        name TEXT NOT NULL,
                        brand TEXT,
                        serving_size REAL DEFAULT 100,
                        serving_unit TEXT DEFAULT 'g',
                        calories REAL,
                        protein REAL,
                        carbs REAL,
                        fat REAL,
                        fiber REAL,
                        category TEXT
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_food_name ON foods(name)")
                conn.commit()
                conn.close()
                print("Created empty food database. Add foods manually or retry import.")
            
            # Add common foods even if USDA import failed
            add_common_foods()


if __name__ == "__main__":
    main()
