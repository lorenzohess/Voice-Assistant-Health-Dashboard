"""SQLAlchemy models for health data."""

from datetime import datetime, date, time
from app import db


class WeightEntry(db.Model):
    """Daily weight measurement."""
    
    __tablename__ = "weight_entries"
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    weight_kg = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<WeightEntry {self.date}: {self.weight_kg}kg>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "weight_kg": self.weight_kg,
        }


class SleepEntry(db.Model):
    """Daily sleep duration."""
    
    __tablename__ = "sleep_entries"
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    hours = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SleepEntry {self.date}: {self.hours}h>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "hours": self.hours,
        }


class WakeTimeEntry(db.Model):
    """Daily wake-up time."""
    
    __tablename__ = "wake_time_entries"
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    wake_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<WakeTimeEntry {self.date}: {self.wake_time}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "wake_time": self.wake_time.strftime("%H:%M:%S"),
        }


class WorkoutEntry(db.Model):
    """Workout log entry."""
    
    __tablename__ = "workout_entries"
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    workout_type = db.Column(db.String(100), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<WorkoutEntry {self.date}: {self.workout_type}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "workout_type": self.workout_type,
            "duration_minutes": self.duration_minutes,
            "notes": self.notes,
        }


class CalorieEntry(db.Model):
    """Calorie intake entry."""
    
    __tablename__ = "calorie_entries"
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    meal_name = db.Column(db.String(200), nullable=False)
    calories = db.Column(db.Float, nullable=False)
    protein_g = db.Column(db.Float, nullable=True)
    carbs_g = db.Column(db.Float, nullable=True)
    fat_g = db.Column(db.Float, nullable=True)
    meal_type = db.Column(db.String(50), nullable=True)  # breakfast, lunch, dinner, snack
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CalorieEntry {self.date}: {self.meal_name} ({self.calories} cal)>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "meal_name": self.meal_name,
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "meal_type": self.meal_type,
        }


class MealPreset(db.Model):
    """Quick-add meal preset for frequently eaten meals."""
    
    __tablename__ = "meal_presets"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    category = db.Column(db.String(50), nullable=True)  # breakfast, lunch, dinner, snack
    calories = db.Column(db.Float, nullable=False)
    protein_g = db.Column(db.Float, nullable=True)
    carbs_g = db.Column(db.Float, nullable=True)
    fat_g = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MealPreset {self.name}: {self.calories} cal>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
        }
