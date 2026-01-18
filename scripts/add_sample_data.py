#!/usr/bin/env python3
"""Add sample data for testing the Health Dashboard."""

import sys
import os
import random
from datetime import date, time, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import (
    WeightEntry, SleepEntry, WakeTimeEntry, WorkoutEntry,
    CustomMetric, CustomMetricEntry
)
from app.food_db import init_food_db, add_food, get_food_db_connection


# Sample foods with new schema
# calories_per_unit: calories per canonical unit (g, ml, or piece)
SAMPLE_FOODS = [
    # Piece-based foods (calories per piece)
    {"name": "Egg (large)", "calories_per_unit": 70, "unit_type": "piece", "canonical_unit": "piece", "category": "breakfast",
     "aliases": ["egg", "eggs", "boiled egg", "fried egg", "scrambled egg"]},
    {"name": "Banana (medium)", "calories_per_unit": 105, "unit_type": "piece", "canonical_unit": "piece", "category": "fruit",
     "aliases": ["banana", "bananas"]},
    {"name": "Apple (medium)", "calories_per_unit": 95, "unit_type": "piece", "canonical_unit": "piece", "category": "fruit",
     "aliases": ["apple", "apples"]},
    {"name": "Orange (medium)", "calories_per_unit": 62, "unit_type": "piece", "canonical_unit": "piece", "category": "fruit",
     "aliases": ["orange", "oranges"]},
    {"name": "Slice of bread (white)", "calories_per_unit": 75, "unit_type": "piece", "canonical_unit": "piece", "category": "carbs",
     "aliases": ["bread", "white bread", "toast", "slice of bread"]},
    {"name": "Slice of bread (whole wheat)", "calories_per_unit": 70, "unit_type": "piece", "canonical_unit": "piece", "category": "carbs",
     "aliases": ["whole wheat bread", "wheat bread", "brown bread"]},
    {"name": "Croissant", "calories_per_unit": 230, "unit_type": "piece", "canonical_unit": "piece", "category": "breakfast",
     "aliases": ["croissant"]},
    {"name": "Avocado (half)", "calories_per_unit": 160, "unit_type": "piece", "canonical_unit": "piece", "category": "fruit",
     "aliases": ["avocado", "half avocado"]},
    
    # Mass-based foods (calories per gram)
    {"name": "Chicken breast (cooked)", "calories_per_unit": 1.65, "unit_type": "mass", "canonical_unit": "g", "category": "protein",
     "aliases": ["chicken", "grilled chicken", "chicken breast", "cooked chicken"]},
    {"name": "Chicken breast (raw)", "calories_per_unit": 1.20, "unit_type": "mass", "canonical_unit": "g", "category": "protein",
     "aliases": ["raw chicken", "raw chicken breast"]},
    {"name": "Salmon (cooked)", "calories_per_unit": 2.08, "unit_type": "mass", "canonical_unit": "g", "category": "protein",
     "aliases": ["salmon", "grilled salmon", "baked salmon", "salmon fillet"]},
    {"name": "Ground beef (lean, cooked)", "calories_per_unit": 2.50, "unit_type": "mass", "canonical_unit": "g", "category": "protein",
     "aliases": ["ground beef", "beef", "hamburger meat"]},
    {"name": "Tofu", "calories_per_unit": 0.76, "unit_type": "mass", "canonical_unit": "g", "category": "protein",
     "aliases": ["tofu"]},
    {"name": "Tuna (canned)", "calories_per_unit": 1.16, "unit_type": "mass", "canonical_unit": "g", "category": "protein",
     "aliases": ["tuna", "canned tuna"]},
    {"name": "White rice (cooked)", "calories_per_unit": 1.30, "unit_type": "mass", "canonical_unit": "g", "category": "carbs",
     "aliases": ["white rice", "rice", "cooked rice"]},
    {"name": "Brown rice (cooked)", "calories_per_unit": 1.12, "unit_type": "mass", "canonical_unit": "g", "category": "carbs",
     "aliases": ["brown rice"]},
    {"name": "Pasta (cooked)", "calories_per_unit": 1.31, "unit_type": "mass", "canonical_unit": "g", "category": "carbs",
     "aliases": ["pasta", "spaghetti", "noodles", "cooked pasta"]},
    {"name": "Pasta (dry)", "calories_per_unit": 3.71, "unit_type": "mass", "canonical_unit": "g", "category": "carbs",
     "aliases": ["dry pasta", "uncooked pasta"]},
    {"name": "Oatmeal (dry)", "calories_per_unit": 3.89, "unit_type": "mass", "canonical_unit": "g", "category": "breakfast",
     "aliases": ["oatmeal", "oats", "dry oatmeal"]},
    {"name": "Almonds", "calories_per_unit": 5.79, "unit_type": "mass", "canonical_unit": "g", "category": "snack",
     "aliases": ["almonds", "almond"]},
    {"name": "Peanut butter", "calories_per_unit": 5.88, "unit_type": "mass", "canonical_unit": "g", "category": "snack",
     "aliases": ["peanut butter", "pb"]},
    {"name": "Cheddar cheese", "calories_per_unit": 4.03, "unit_type": "mass", "canonical_unit": "g", "category": "dairy",
     "aliases": ["cheddar", "cheese", "cheddar cheese"]},
    {"name": "Broccoli (cooked)", "calories_per_unit": 0.35, "unit_type": "mass", "canonical_unit": "g", "category": "vegetable",
     "aliases": ["broccoli", "steamed broccoli"]},
    {"name": "Carrots (raw)", "calories_per_unit": 0.41, "unit_type": "mass", "canonical_unit": "g", "category": "vegetable",
     "aliases": ["carrots", "carrot", "raw carrots"]},
    {"name": "Spinach (raw)", "calories_per_unit": 0.23, "unit_type": "mass", "canonical_unit": "g", "category": "vegetable",
     "aliases": ["spinach", "raw spinach"]},
    {"name": "Potato (baked)", "calories_per_unit": 0.93, "unit_type": "mass", "canonical_unit": "g", "category": "carbs",
     "aliases": ["potato", "baked potato"]},
    {"name": "Sweet potato (baked)", "calories_per_unit": 0.90, "unit_type": "mass", "canonical_unit": "g", "category": "carbs",
     "aliases": ["sweet potato"]},
    
    # Volume-based foods (calories per ml)
    {"name": "Whole milk (3.25%)", "calories_per_unit": 0.63, "unit_type": "volume", "canonical_unit": "ml", "category": "dairy",
     "aliases": ["whole milk", "milk", "full fat milk"]},
    {"name": "Skim milk", "calories_per_unit": 0.35, "unit_type": "volume", "canonical_unit": "ml", "category": "dairy",
     "aliases": ["skim milk", "nonfat milk", "fat free milk"]},
    {"name": "2% milk", "calories_per_unit": 0.50, "unit_type": "volume", "canonical_unit": "ml", "category": "dairy",
     "aliases": ["2% milk", "reduced fat milk", "2 percent milk"]},
    {"name": "Orange juice", "calories_per_unit": 0.47, "unit_type": "volume", "canonical_unit": "ml", "category": "drink",
     "aliases": ["orange juice", "oj"]},
    {"name": "Apple juice", "calories_per_unit": 0.46, "unit_type": "volume", "canonical_unit": "ml", "category": "drink",
     "aliases": ["apple juice"]},
    {"name": "Coffee (black)", "calories_per_unit": 0.01, "unit_type": "volume", "canonical_unit": "ml", "category": "drink",
     "aliases": ["coffee", "black coffee"]},
    {"name": "Greek yogurt", "calories_per_unit": 0.59, "unit_type": "volume", "canonical_unit": "ml", "category": "dairy",
     "aliases": ["greek yogurt", "yogurt"]},
    {"name": "Olive oil", "calories_per_unit": 8.84, "unit_type": "volume", "canonical_unit": "ml", "category": "fats",
     "aliases": ["olive oil", "oil"]},
    {"name": "Honey", "calories_per_unit": 3.04, "unit_type": "volume", "canonical_unit": "ml", "category": "sweetener",
     "aliases": ["honey"]},
]


def add_sample_foods():
    """Add sample foods to the food database."""
    init_food_db()
    
    # Clear existing foods and aliases
    conn = get_food_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM food_aliases")
    cursor.execute("DELETE FROM foods")
    conn.commit()
    conn.close()
    
    # Add sample foods with aliases
    for food in SAMPLE_FOODS:
        add_food(
            name=food["name"],
            calories_per_unit=food["calories_per_unit"],
            unit_type=food["unit_type"],
            canonical_unit=food["canonical_unit"],
            category=food.get("category"),
            aliases=food.get("aliases", [])
        )
    
    print(f"  - {len(SAMPLE_FOODS)} foods in database")


def add_sample_data():
    """Generate sample health data for the past 60 days."""
    app = create_app()
    
    with app.app_context():
        # Clear existing data
        WeightEntry.query.delete()
        SleepEntry.query.delete()
        WakeTimeEntry.query.delete()
        WorkoutEntry.query.delete()
        CustomMetricEntry.query.delete()
        CustomMetric.query.delete()
        db.session.commit()
        
        today = date.today()
        base_weight = 165.0  # Base weight in lbs
        
        workout_types = ["Running", "Weights", "Yoga", "Swimming", "Cycling", "HIIT"]
        
        for i in range(60, 0, -1):
            entry_date = today - timedelta(days=i)
            
            # Weight: gradual decrease with some noise
            weight = base_weight - (60 - i) * 0.05 + random.uniform(-1.0, 1.0)  # Variation in lbs
            weight_entry = WeightEntry(date=entry_date, weight_kg=round(weight, 1))  # Stores lbs despite column name
            db.session.add(weight_entry)
            
            # Sleep: 6-9 hours with some variation
            sleep_hours = random.uniform(6, 9)
            sleep_entry = SleepEntry(date=entry_date, hours=round(sleep_hours, 1))
            db.session.add(sleep_entry)
            
            # Wake time: around 6:30-8:00 AM
            wake_hour = random.randint(6, 7)
            wake_minute = random.randint(0, 59)
            wake_entry = WakeTimeEntry(
                date=entry_date,
                wake_time=time(wake_hour, wake_minute, 0)
            )
            db.session.add(wake_entry)
            
            # Workouts: 3-4 per week on average
            if random.random() < 0.5:
                workout_entry = WorkoutEntry(
                    date=entry_date,
                    workout_type=random.choice(workout_types),
                    duration_minutes=random.randint(20, 60),
                    notes=""
                )
                db.session.add(workout_entry)
        
        # Create default custom metrics
        veggie_metric = CustomMetric(
            name="Vegetable Servings",
            unit="servings",
            chart_type="bar",
            color="#10b981",  # Green
            voice_keyword="vegetables"
        )
        db.session.add(veggie_metric)
        db.session.commit()
        
        # Add some sample veggie data for the past 30 days
        for i in range(30, 0, -1):
            entry_date = today - timedelta(days=i)
            # Random 0-6 servings, averaging around 3
            servings = max(0, random.gauss(3, 1.5))
            entry = CustomMetricEntry(
                metric_id=veggie_metric.id,
                date=entry_date,
                value=round(servings, 1)
            )
            db.session.add(entry)
        
        db.session.commit()
        
        print("Sample data added successfully!")
        print(f"  - {WeightEntry.query.count()} weight entries")
        print(f"  - {SleepEntry.query.count()} sleep entries")
        print(f"  - {WakeTimeEntry.query.count()} wake time entries")
        print(f"  - {WorkoutEntry.query.count()} workout entries")
        print(f"  - {CustomMetric.query.count()} custom metrics")
        print(f"  - {CustomMetricEntry.query.count()} custom metric entries")
    
    # Add sample foods (separate database)
    add_sample_foods()


if __name__ == "__main__":
    add_sample_data()
