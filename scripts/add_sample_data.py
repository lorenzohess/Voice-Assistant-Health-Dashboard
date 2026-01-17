#!/usr/bin/env python3
"""Add sample data for testing the Health Dashboard."""

import sys
import os
import random
from datetime import date, time, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import WeightEntry, SleepEntry, WakeTimeEntry, WorkoutEntry


def add_sample_data():
    """Generate sample health data for the past 60 days."""
    app = create_app()
    
    with app.app_context():
        # Clear existing data
        WeightEntry.query.delete()
        SleepEntry.query.delete()
        WakeTimeEntry.query.delete()
        WorkoutEntry.query.delete()
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
        
        db.session.commit()
        print("Sample data added successfully!")
        print(f"  - {WeightEntry.query.count()} weight entries")
        print(f"  - {SleepEntry.query.count()} sleep entries")
        print(f"  - {WakeTimeEntry.query.count()} wake time entries")
        print(f"  - {WorkoutEntry.query.count()} workout entries")


if __name__ == "__main__":
    add_sample_data()
