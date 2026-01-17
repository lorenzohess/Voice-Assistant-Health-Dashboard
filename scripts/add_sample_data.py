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
from app.food_db import init_food_db, add_custom_food, get_food_db_connection


# Common foods with nutritional data
SAMPLE_FOODS = [
    # Breakfast
    {"name": "Scrambled eggs (2)", "calories": 180, "protein": 12, "carbs": 2, "fat": 14, "category": "breakfast"},
    {"name": "Fried egg", "calories": 90, "protein": 6, "carbs": 0.5, "fat": 7, "category": "breakfast"},
    {"name": "Boiled egg", "calories": 78, "protein": 6, "carbs": 0.5, "fat": 5, "category": "breakfast"},
    {"name": "Oatmeal with milk", "calories": 250, "protein": 8, "carbs": 45, "fat": 5, "category": "breakfast"},
    {"name": "Greek yogurt", "calories": 100, "protein": 17, "carbs": 6, "fat": 0.5, "category": "breakfast"},
    {"name": "Banana", "calories": 105, "protein": 1.3, "carbs": 27, "fat": 0.4, "category": "fruit"},
    {"name": "Toast with butter", "calories": 150, "protein": 3, "carbs": 20, "fat": 7, "category": "breakfast"},
    {"name": "Croissant", "calories": 230, "protein": 5, "carbs": 26, "fat": 12, "category": "breakfast"},
    
    # Lunch/Dinner proteins
    {"name": "Chicken breast (grilled)", "calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "category": "protein", "serving_unit": "100g"},
    {"name": "Salmon fillet", "calories": 208, "protein": 20, "carbs": 0, "fat": 13, "category": "protein", "serving_unit": "100g"},
    {"name": "Ground beef (lean)", "calories": 250, "protein": 26, "carbs": 0, "fat": 15, "category": "protein", "serving_unit": "100g"},
    {"name": "Tofu", "calories": 76, "protein": 8, "carbs": 2, "fat": 4.5, "category": "protein", "serving_unit": "100g"},
    {"name": "Tuna (canned)", "calories": 116, "protein": 26, "carbs": 0, "fat": 0.8, "category": "protein", "serving_unit": "100g"},
    
    # Carbs
    {"name": "White rice (cooked)", "calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3, "category": "carbs", "serving_unit": "100g"},
    {"name": "Brown rice (cooked)", "calories": 112, "protein": 2.6, "carbs": 24, "fat": 0.9, "category": "carbs", "serving_unit": "100g"},
    {"name": "Pasta (cooked)", "calories": 131, "protein": 5, "carbs": 25, "fat": 1.1, "category": "carbs", "serving_unit": "100g"},
    {"name": "Whole wheat bread", "calories": 80, "protein": 4, "carbs": 15, "fat": 1, "category": "carbs", "serving_unit": "slice"},
    {"name": "Baked potato", "calories": 161, "protein": 4.3, "carbs": 37, "fat": 0.2, "category": "carbs", "serving_unit": "medium"},
    {"name": "Sweet potato", "calories": 103, "protein": 2.3, "carbs": 24, "fat": 0.1, "category": "carbs", "serving_unit": "medium"},
    
    # Vegetables
    {"name": "Broccoli (steamed)", "calories": 55, "protein": 3.7, "carbs": 11, "fat": 0.6, "category": "vegetable", "serving_unit": "cup"},
    {"name": "Spinach (raw)", "calories": 7, "protein": 0.9, "carbs": 1.1, "fat": 0.1, "category": "vegetable", "serving_unit": "cup"},
    {"name": "Carrots", "calories": 52, "protein": 1.2, "carbs": 12, "fat": 0.3, "category": "vegetable", "serving_unit": "100g"},
    {"name": "Green beans", "calories": 31, "protein": 1.8, "carbs": 7, "fat": 0.1, "category": "vegetable", "serving_unit": "cup"},
    {"name": "Mixed salad", "calories": 20, "protein": 1.5, "carbs": 4, "fat": 0.2, "category": "vegetable", "serving_unit": "cup"},
    
    # Fruits
    {"name": "Apple", "calories": 95, "protein": 0.5, "carbs": 25, "fat": 0.3, "category": "fruit"},
    {"name": "Orange", "calories": 62, "protein": 1.2, "carbs": 15, "fat": 0.2, "category": "fruit"},
    {"name": "Blueberries", "calories": 85, "protein": 1.1, "carbs": 21, "fat": 0.5, "category": "fruit", "serving_unit": "cup"},
    {"name": "Strawberries", "calories": 50, "protein": 1, "carbs": 12, "fat": 0.5, "category": "fruit", "serving_unit": "cup"},
    
    # Snacks
    {"name": "Almonds", "calories": 164, "protein": 6, "carbs": 6, "fat": 14, "category": "snack", "serving_unit": "oz"},
    {"name": "Peanut butter", "calories": 190, "protein": 7, "carbs": 7, "fat": 16, "category": "snack", "serving_unit": "2 tbsp"},
    {"name": "Dark chocolate", "calories": 170, "protein": 2, "carbs": 13, "fat": 12, "category": "snack", "serving_unit": "oz"},
    {"name": "Cheese (cheddar)", "calories": 113, "protein": 7, "carbs": 0.4, "fat": 9, "category": "dairy", "serving_unit": "oz"},
    
    # Drinks
    {"name": "Whole milk", "calories": 149, "protein": 8, "carbs": 12, "fat": 8, "category": "dairy", "serving_unit": "cup"},
    {"name": "Skim milk", "calories": 83, "protein": 8, "carbs": 12, "fat": 0.2, "category": "dairy", "serving_unit": "cup"},
    {"name": "Orange juice", "calories": 112, "protein": 1.7, "carbs": 26, "fat": 0.5, "category": "drink", "serving_unit": "cup"},
    {"name": "Coffee (black)", "calories": 2, "protein": 0.3, "carbs": 0, "fat": 0, "category": "drink", "serving_unit": "cup"},
    {"name": "Coffee with milk", "calories": 30, "protein": 1, "carbs": 2, "fat": 1.5, "category": "drink", "serving_unit": "cup"},
    
    # Common meals
    {"name": "Chicken salad", "calories": 350, "protein": 25, "carbs": 15, "fat": 20, "category": "meal"},
    {"name": "Burrito bowl", "calories": 650, "protein": 35, "carbs": 70, "fat": 25, "category": "meal"},
    {"name": "Grilled cheese sandwich", "calories": 390, "protein": 13, "carbs": 30, "fat": 25, "category": "meal"},
    {"name": "Veggie stir fry", "calories": 250, "protein": 8, "carbs": 30, "fat": 12, "category": "meal"},
    {"name": "Spaghetti bolognese", "calories": 450, "protein": 22, "carbs": 55, "fat": 15, "category": "meal"},
    {"name": "Caesar salad", "calories": 280, "protein": 8, "carbs": 12, "fat": 22, "category": "meal"},
    {"name": "Protein shake", "calories": 200, "protein": 30, "carbs": 10, "fat": 3, "category": "drink"},
]


def add_sample_foods():
    """Add sample foods to the food database."""
    init_food_db()
    
    # Clear existing foods
    conn = get_food_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM foods")
    conn.commit()
    conn.close()
    
    # Add sample foods
    for food in SAMPLE_FOODS:
        add_custom_food(
            name=food["name"],
            calories=food["calories"],
            protein=food.get("protein"),
            carbs=food.get("carbs"),
            fat=food.get("fat"),
            serving_size=food.get("serving_size", 1),
            serving_unit=food.get("serving_unit", "serving"),
            category=food.get("category", "other")
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
        base_weight = 75.0
        
        workout_types = ["Running", "Weights", "Yoga", "Swimming", "Cycling", "HIIT"]
        
        for i in range(60, 0, -1):
            entry_date = today - timedelta(days=i)
            
            # Weight: gradual decrease with some noise
            weight = base_weight - (60 - i) * 0.03 + random.uniform(-0.5, 0.5)
            weight_entry = WeightEntry(date=entry_date, weight_kg=round(weight, 1))
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
            color="#10b981"  # Green
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
