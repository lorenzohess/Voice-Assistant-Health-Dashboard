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
    quantity = db.Column(db.String(50), nullable=True)  # e.g., "150g", "2 cups"
    food_id = db.Column(db.Integer, nullable=True)  # Reference to foods table (if computed)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CalorieEntry {self.date}: {self.meal_name} ({self.calories} cal)>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "meal_name": self.meal_name,
            "calories": self.calories,
            "quantity": self.quantity,
            "food_id": self.food_id,
        }


class MealPreset(db.Model):
    """Quick-add meal preset for frequently eaten meals."""
    
    __tablename__ = "meal_presets"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    category = db.Column(db.String(50), nullable=True)  # breakfast, lunch, dinner, snack
    calories = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.String(50), nullable=True)  # e.g., "1 piece", "100g"
    food_id = db.Column(db.Integer, nullable=True)  # Reference to foods table
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MealPreset {self.name}: {self.calories} cal>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "calories": self.calories,
            "quantity": self.quantity,
            "food_id": self.food_id,
        }


class CustomMetric(db.Model):
    """User-defined custom metric definition."""
    
    __tablename__ = "custom_metrics"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    unit = db.Column(db.String(50), nullable=False)  # e.g., "servings", "glasses", "minutes"
    chart_type = db.Column(db.String(20), default="bar")  # "bar" or "line"
    color = db.Column(db.String(20), default="#6366f1")  # hex color
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to entries
    entries = db.relationship("CustomMetricEntry", backref="metric", lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CustomMetric {self.name} ({self.unit})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "unit": self.unit,
            "chart_type": self.chart_type,
            "color": self.color,
        }


class CustomMetricEntry(db.Model):
    """Entry for a user-defined custom metric."""
    
    __tablename__ = "custom_metric_entries"
    
    id = db.Column(db.Integer, primary_key=True)
    metric_id = db.Column(db.Integer, db.ForeignKey("custom_metrics.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    value = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint: one entry per metric per date
    __table_args__ = (db.UniqueConstraint('metric_id', 'date', name='uix_metric_date'),)
    
    def __repr__(self):
        return f"<CustomMetricEntry {self.metric_id} {self.date}: {self.value}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "metric_id": self.metric_id,
            "date": self.date.isoformat(),
            "value": self.value,
            "notes": self.notes,
        }
