"""Flask routes for the Health Dashboard."""

import csv
import io
import json
from datetime import datetime, date, timedelta
from statistics import mean, median

from flask import Blueprint, render_template, request, jsonify, Response
import plotly.graph_objects as go
import plotly.utils

from app import db
from app.models import (
    WeightEntry, SleepEntry, WakeTimeEntry, WorkoutEntry, CalorieEntry, 
    MealPreset, CustomMetric, CustomMetricEntry
)
from app.pool_schedule import get_pool_status, get_weekly_schedule
from app.food_db import (
    search_foods, get_food_by_id, add_food, get_food_count, init_food_db,
    parse_quantity, compute_calories
)
from app.validation import (
    validate_weight, validate_calories_single, validate_calories_daily,
    validate_sleep
)

main_bp = Blueprint("main", __name__)


def get_date_range(window: str) -> tuple[date, date]:
    """Get start and end dates based on time window selection."""
    end_date = date.today()
    
    if window == "1w":
        start_date = end_date - timedelta(days=7)
    elif window == "3m":
        start_date = end_date - timedelta(days=90)
    elif window == "6m":
        start_date = end_date - timedelta(days=180)
    elif window == "1y":
        start_date = end_date - timedelta(days=365)
    else:  # Default: 1 month
        start_date = end_date - timedelta(days=30)
    
    return start_date, end_date


def calculate_metrics(values: list[float]) -> dict:
    """Calculate statistics for a list of values."""
    if not values:
        return {
            "latest": None,
            "average": None,
            "median": None,
            "min": None,
            "max": None,
            "count": 0,
        }
    
    return {
        "latest": values[-1] if values else None,
        "average": round(mean(values), 2),
        "median": round(median(values), 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "count": len(values),
    }


def create_line_chart(dates: list, values: list, title: str, y_label: str, color: str = "#3b82f6") -> str:
    """Create a Plotly line chart and return as JSON."""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines+markers",
        name=title,
        line=dict(color=color, width=2),
        marker=dict(size=6),
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Date",
        yaxis_title=y_label,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=50, r=30, t=50, b=50),
        height=300,
    )
    
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.1)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.1)")
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def create_bar_chart(dates: list, values: list, title: str, y_label: str, color: str = "#10b981") -> str:
    """Create a Plotly bar chart and return as JSON."""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=dates,
        y=values,
        name=title,
        marker_color=color,
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Date",
        yaxis_title=y_label,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=50, r=30, t=50, b=50),
        height=300,
    )
    
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.1)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.1)")
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


@main_bp.route("/")
def dashboard():
    """Main dashboard view."""
    window = request.args.get("window", "1m")
    start_date, end_date = get_date_range(window)
    
    # Fetch data within date range
    weight_entries = WeightEntry.query.filter(
        WeightEntry.date >= start_date,
        WeightEntry.date <= end_date
    ).order_by(WeightEntry.date).all()
    
    sleep_entries = SleepEntry.query.filter(
        SleepEntry.date >= start_date,
        SleepEntry.date <= end_date
    ).order_by(SleepEntry.date).all()
    
    wake_entries = WakeTimeEntry.query.filter(
        WakeTimeEntry.date >= start_date,
        WakeTimeEntry.date <= end_date
    ).order_by(WakeTimeEntry.date).all()
    
    workout_entries = WorkoutEntry.query.filter(
        WorkoutEntry.date >= start_date,
        WorkoutEntry.date <= end_date
    ).order_by(WorkoutEntry.date).all()
    
    # Prepare chart data
    weight_dates = [e.date.isoformat() for e in weight_entries]
    weight_values = [e.weight_kg for e in weight_entries]
    weight_chart = create_line_chart(weight_dates, weight_values, "Weight", "kg", "#3b82f6")
    weight_metrics = calculate_metrics(weight_values)
    
    sleep_dates = [e.date.isoformat() for e in sleep_entries]
    sleep_values = [e.hours for e in sleep_entries]
    sleep_chart = create_bar_chart(sleep_dates, sleep_values, "Sleep Duration", "hours", "#8b5cf6")
    sleep_metrics = calculate_metrics(sleep_values)
    
    # Wake time as decimal hours for graphing
    wake_dates = [e.date.isoformat() for e in wake_entries]
    wake_values = [e.wake_time.hour + e.wake_time.minute / 60 for e in wake_entries]
    wake_chart = create_line_chart(wake_dates, wake_values, "Wake Time", "hour", "#f59e0b")
    wake_metrics = calculate_metrics(wake_values)
    if wake_metrics["latest"]:
        # Format as time string for display
        h = int(wake_metrics["latest"])
        m = int((wake_metrics["latest"] - h) * 60)
        wake_metrics["latest_formatted"] = f"{h:02d}:{m:02d}"
    else:
        wake_metrics["latest_formatted"] = "N/A"
    
    # Workout count per day
    workout_by_date = {}
    for e in workout_entries:
        d = e.date.isoformat()
        workout_by_date[d] = workout_by_date.get(d, 0) + 1
    workout_dates = sorted(workout_by_date.keys())
    workout_values = [workout_by_date[d] for d in workout_dates]
    workout_chart = create_bar_chart(workout_dates, workout_values, "Workouts", "count", "#10b981")
    workout_metrics = {
        "total": len(workout_entries),
        "days_with_workout": len(workout_by_date),
    }
    
    # Calorie data
    calorie_entries = CalorieEntry.query.filter(
        CalorieEntry.date >= start_date,
        CalorieEntry.date <= end_date
    ).order_by(CalorieEntry.date).all()
    
    # Group calories by date
    calories_by_date = {}
    for e in calorie_entries:
        d = e.date.isoformat()
        if d not in calories_by_date:
            calories_by_date[d] = 0
        calories_by_date[d] += e.calories
    
    calorie_dates = sorted(calories_by_date.keys())
    calorie_values = [calories_by_date[d] for d in calorie_dates]
    calorie_chart = create_bar_chart(calorie_dates, calorie_values, "Daily Calories", "kcal", "#ef4444")
    calorie_metrics = calculate_metrics(calorie_values)
    
    # Today's calories breakdown
    today_entries = CalorieEntry.query.filter(
        CalorieEntry.date == date.today()
    ).order_by(CalorieEntry.created_at).all()
    today_calories = sum(e.calories for e in today_entries)
    
    # Get presets for quick-add
    presets = MealPreset.query.order_by(MealPreset.category, MealPreset.name).all()
    
    # Food database status
    food_count = get_food_count()
    
    # Pool schedule
    pool_status = get_pool_status()
    pool_weekly = get_weekly_schedule()
    
    # Custom metrics
    custom_metrics = CustomMetric.query.order_by(CustomMetric.name).all()
    custom_charts = []
    
    for metric in custom_metrics:
        entries = CustomMetricEntry.query.filter(
            CustomMetricEntry.metric_id == metric.id,
            CustomMetricEntry.date >= start_date,
            CustomMetricEntry.date <= end_date
        ).order_by(CustomMetricEntry.date).all()
        
        dates = [e.date.isoformat() for e in entries]
        values = [e.value for e in entries]
        
        if metric.chart_type == "line":
            chart_json = create_line_chart(dates, values, metric.name, metric.unit, metric.color)
        else:
            chart_json = create_bar_chart(dates, values, metric.name, metric.unit, metric.color)
        
        metrics_data = calculate_metrics(values)
        
        custom_charts.append({
            "id": metric.id,
            "name": metric.name,
            "unit": metric.unit,
            "chart_type": metric.chart_type,
            "color": metric.color,
            "chart_json": chart_json,
            "metrics": metrics_data,
        })
    
    return render_template(
        "dashboard.html",
        window=window,
        weight_chart=weight_chart,
        weight_metrics=weight_metrics,
        sleep_chart=sleep_chart,
        sleep_metrics=sleep_metrics,
        wake_chart=wake_chart,
        wake_metrics=wake_metrics,
        workout_chart=workout_chart,
        workout_metrics=workout_metrics,
        calorie_chart=calorie_chart,
        calorie_metrics=calorie_metrics,
        today_entries=today_entries,
        today_calories=today_calories,
        presets=presets,
        food_count=food_count,
        pool_status=pool_status,
        pool_weekly=pool_weekly,
        custom_charts=custom_charts,
        today=date.today().isoformat(),
    )


# --- API Endpoints for Data Entry ---

@main_bp.route("/api/weight", methods=["POST"])
def add_weight():
    """Add or update weight entry."""
    data = request.get_json()
    
    entry_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    weight_kg = float(data["weight_kg"])
    
    # Check for existing entry on this date
    existing = WeightEntry.query.filter_by(date=entry_date).first()
    if existing:
        existing.weight_kg = weight_kg
    else:
        entry = WeightEntry(date=entry_date, weight_kg=weight_kg)
        db.session.add(entry)
    
    db.session.commit()
    return jsonify({"status": "ok"})


@main_bp.route("/api/sleep", methods=["POST"])
def add_sleep():
    """Add or update sleep entry."""
    data = request.get_json()
    
    entry_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    hours = float(data["hours"])
    
    existing = SleepEntry.query.filter_by(date=entry_date).first()
    if existing:
        existing.hours = hours
    else:
        entry = SleepEntry(date=entry_date, hours=hours)
        db.session.add(entry)
    
    db.session.commit()
    return jsonify({"status": "ok"})


@main_bp.route("/api/wake", methods=["POST"])
def add_wake_time():
    """Add or update wake time entry."""
    data = request.get_json()
    
    entry_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    wake_time = datetime.strptime(data["wake_time"], "%H:%M:%S").time()
    
    existing = WakeTimeEntry.query.filter_by(date=entry_date).first()
    if existing:
        existing.wake_time = wake_time
    else:
        entry = WakeTimeEntry(date=entry_date, wake_time=wake_time)
        db.session.add(entry)
    
    db.session.commit()
    return jsonify({"status": "ok"})


@main_bp.route("/api/workout", methods=["POST"])
def add_workout():
    """Add workout entry."""
    data = request.get_json()
    
    entry_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    workout_type = data["workout_type"]
    duration = data.get("duration_minutes")
    notes = data.get("notes", "")
    
    entry = WorkoutEntry(
        date=entry_date,
        workout_type=workout_type,
        duration_minutes=int(duration) if duration else None,
        notes=notes,
    )
    db.session.add(entry)
    db.session.commit()
    
    return jsonify({"status": "ok", "id": entry.id})


@main_bp.route("/api/workout/<int:workout_id>", methods=["DELETE"])
def delete_workout(workout_id):
    """Delete a workout entry."""
    entry = WorkoutEntry.query.get_or_404(workout_id)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"status": "ok"})


# --- Food Search API ---

@main_bp.route("/api/foods/search")
def search_foods_api():
    """Search the food database."""
    query = request.args.get("q", "")
    limit = int(request.args.get("limit", 20))
    
    results = search_foods(query, limit=limit)
    return jsonify({"foods": results})


@main_bp.route("/api/foods/<int:food_id>")
def get_food(food_id):
    """Get a specific food by ID."""
    food = get_food_by_id(food_id)
    if not food:
        return jsonify({"error": "Food not found"}), 404
    return jsonify(food)


@main_bp.route("/api/foods", methods=["POST"])
def create_custom_food():
    """Add a custom food to the database."""
    data = request.get_json()
    
    food_id = add_food(
        name=data["name"],
        calories_per_unit=float(data["calories_per_unit"]),
        unit_type=data.get("unit_type", "mass"),
        canonical_unit=data.get("canonical_unit", "g"),
        category=data.get("category"),
        aliases=data.get("aliases", []),
    )
    
    return jsonify({"status": "ok", "id": food_id})


@main_bp.route("/api/foods/compute", methods=["POST"])
def compute_food_calories():
    """Compute calories for a food + quantity."""
    data = request.get_json()
    
    food_id = data.get("food_id")
    quantity_text = data.get("quantity")
    
    if not food_id or not quantity_text:
        return jsonify({"status": "error", "message": "food_id and quantity are required"}), 400
    
    # Parse quantity
    parsed = parse_quantity(quantity_text)
    if not parsed["valid"]:
        return jsonify({
            "status": "error",
            "message": parsed.get("error", f"Could not parse quantity: {quantity_text}")
        }), 400
    
    # Compute calories
    result = compute_calories(food_id, parsed["quantity"], parsed["unit"])
    
    if result.get("error"):
        return jsonify({"status": "error", "message": result["error"]}), 400
    
    return jsonify({
        "status": "ok",
        "calories": result["calories"],
        "food_name": result["food_name"],
        "quantity": result["quantity"],
        "unit": result["unit"],
    })


# --- Calorie Entry API ---

@main_bp.route("/api/calories", methods=["POST"])
def add_calorie_entry():
    """Add a calorie entry."""
    data = request.get_json()
    
    entry_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    calories = float(data["calories"])
    meal_name = data["meal_name"]
    
    # Validation
    validation = validate_calories_single(calories)
    if not validation.is_valid:
        return jsonify({"status": "error", "message": validation.error_message}), 400
    
    warnings = []
    if validation.has_warning:
        warnings.append(validation.warning_message)
    
    # Check daily total
    daily_validation = validate_calories_daily(entry_date, calories)
    if daily_validation.has_warning:
        warnings.append(daily_validation.warning_message)
    
    entry = CalorieEntry(
        date=entry_date,
        meal_name=meal_name,
        calories=calories,
        quantity=data.get("quantity"),
        food_id=int(data["food_id"]) if data.get("food_id") else None,
    )
    db.session.add(entry)
    db.session.commit()
    
    return jsonify({
        "status": "ok",
        "id": entry.id,
        "warnings": warnings if warnings else None
    })


@main_bp.route("/api/calories/<int:entry_id>", methods=["DELETE"])
def delete_calorie_entry(entry_id):
    """Delete a calorie entry."""
    entry = CalorieEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"status": "ok"})


@main_bp.route("/api/calories/today")
def get_today_calories():
    """Get today's calorie entries."""
    entries = CalorieEntry.query.filter(
        CalorieEntry.date == date.today()
    ).order_by(CalorieEntry.created_at).all()
    
    total = sum(e.calories for e in entries)
    
    return jsonify({
        "entries": [e.to_dict() for e in entries],
        "total": total
    })


# --- Meal Preset API ---

@main_bp.route("/api/presets", methods=["GET"])
def get_presets():
    """Get all meal presets."""
    presets = MealPreset.query.order_by(MealPreset.category, MealPreset.name).all()
    return jsonify({"presets": [p.to_dict() for p in presets]})


@main_bp.route("/api/presets", methods=["POST"])
def create_preset():
    """Create a new meal preset."""
    data = request.get_json()
    
    preset = MealPreset(
        name=data["name"],
        category=data.get("category"),
        calories=float(data["calories"]),
        quantity=data.get("quantity"),
        food_id=int(data["food_id"]) if data.get("food_id") else None,
    )
    db.session.add(preset)
    db.session.commit()
    
    return jsonify({"status": "ok", "id": preset.id})


@main_bp.route("/api/presets/<int:preset_id>", methods=["PUT"])
def update_preset(preset_id):
    """Update a meal preset."""
    preset = MealPreset.query.get_or_404(preset_id)
    data = request.get_json()
    
    preset.name = data.get("name", preset.name)
    preset.category = data.get("category", preset.category)
    preset.calories = float(data["calories"]) if data.get("calories") else preset.calories
    preset.quantity = data.get("quantity", preset.quantity)
    preset.food_id = int(data["food_id"]) if data.get("food_id") else preset.food_id
    
    db.session.commit()
    return jsonify({"status": "ok"})


@main_bp.route("/api/presets/<int:preset_id>", methods=["DELETE"])
def delete_preset(preset_id):
    """Delete a meal preset."""
    preset = MealPreset.query.get_or_404(preset_id)
    db.session.delete(preset)
    db.session.commit()
    return jsonify({"status": "ok"})


@main_bp.route("/api/presets/<int:preset_id>/log", methods=["POST"])
def log_preset(preset_id):
    """Log a preset as a calorie entry for today (or specified date)."""
    preset = MealPreset.query.get_or_404(preset_id)
    data = request.get_json() or {}
    
    entry_date = datetime.strptime(data["date"], "%Y-%m-%d").date() if data.get("date") else date.today()
    
    entry = CalorieEntry(
        date=entry_date,
        meal_name=preset.name,
        calories=preset.calories,
        quantity=preset.quantity,
        food_id=preset.food_id,
    )
    db.session.add(entry)
    db.session.commit()
    
    return jsonify({"status": "ok", "id": entry.id})


# --- System Control API ---

@main_bp.route("/api/volume/toggle", methods=["POST"])
def toggle_volume():
    """Toggle system volume mute state."""
    import subprocess
    try:
        # Toggle mute using amixer
        subprocess.run(["amixer", "set", "Master", "toggle"], check=True, capture_output=True)
        
        # Check new state
        result = subprocess.run(["amixer", "get", "Master"], capture_output=True, text=True)
        muted = "[off]" in result.stdout
        
        return jsonify({"status": "ok", "muted": muted})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "muted": False})


@main_bp.route("/api/volume/state", methods=["GET"])
def get_volume_state():
    """Get current volume mute state."""
    import subprocess
    try:
        result = subprocess.run(["amixer", "get", "Master"], capture_output=True, text=True)
        muted = "[off]" in result.stdout
        return jsonify({"muted": muted})
    except:
        return jsonify({"muted": False})


@main_bp.route("/api/sample-data", methods=["POST"])
def load_sample_data():
    """Load sample data into the database."""
    from datetime import timedelta
    import random
    
    try:
        today = date.today()
        
        # Add sample weight entries (last 30 days)
        for i in range(30):
            entry_date = today - timedelta(days=i)
            weight = 75 + random.uniform(-2, 2)
            
            existing = WeightEntry.query.filter_by(date=entry_date).first()
            if not existing:
                entry = WeightEntry(date=entry_date, weight_kg=round(weight, 1))
                db.session.add(entry)
        
        # Add sample sleep entries
        for i in range(30):
            entry_date = today - timedelta(days=i)
            hours = 7 + random.uniform(-1.5, 1.5)
            
            existing = SleepEntry.query.filter_by(date=entry_date).first()
            if not existing:
                entry = SleepEntry(date=entry_date, hours=round(hours, 1))
                db.session.add(entry)
        
        # Add sample calorie entries
        for i in range(30):
            entry_date = today - timedelta(days=i)
            calories = 2000 + random.randint(-300, 300)
            
            existing = CalorieEntry.query.filter_by(date=entry_date).first()
            if not existing:
                entry = CalorieEntry(
                    date=entry_date,
                    meal_name="Sample meals",
                    calories=calories
                )
                db.session.add(entry)
        
        db.session.commit()
        return jsonify({"status": "ok", "message": "Sample data loaded"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)})


# --- Dashboard Refresh API ---

@main_bp.route("/api/last-updated", methods=["GET"])
def get_last_updated():
    """Get the timestamp of the most recent data update.
    
    Used by the dashboard to detect when to auto-refresh.
    """
    # Check the most recent entry across all tables
    latest = None
    
    # Check each table for the most recent created_at
    for model in [WeightEntry, SleepEntry, WakeTimeEntry, WorkoutEntry, CalorieEntry, CustomMetricEntry]:
        try:
            entry = model.query.order_by(model.created_at.desc()).first()
            if entry and entry.created_at:
                if latest is None or entry.created_at > latest:
                    latest = entry.created_at
        except:
            pass
    
    if latest:
        return jsonify({"last_updated": latest.isoformat()})
    else:
        return jsonify({"last_updated": None})


# --- Custom Metrics API ---

@main_bp.route("/api/custom-metrics", methods=["GET"])
def get_custom_metrics():
    """Get all custom metrics."""
    metrics = CustomMetric.query.order_by(CustomMetric.name).all()
    return jsonify({"metrics": [m.to_dict() for m in metrics]})


@main_bp.route("/api/custom-metrics", methods=["POST"])
def create_custom_metric():
    """Create a new custom metric (graph)."""
    data = request.get_json()
    
    # Check if metric with this name already exists
    existing = CustomMetric.query.filter_by(name=data["name"]).first()
    if existing:
        return jsonify({"status": "error", "message": "Metric with this name already exists"}), 400
    
    metric = CustomMetric(
        name=data["name"],
        unit=data.get("unit", "units"),
        chart_type=data.get("chart_type", "bar"),
        color=data.get("color", "#6366f1"),
    )
    db.session.add(metric)
    db.session.commit()
    
    return jsonify({"status": "ok", "id": metric.id, "metric": metric.to_dict()})


@main_bp.route("/api/custom-metrics/<int:metric_id>", methods=["PUT"])
def update_custom_metric(metric_id):
    """Update a custom metric."""
    metric = CustomMetric.query.get_or_404(metric_id)
    data = request.get_json()
    
    metric.name = data.get("name", metric.name)
    metric.unit = data.get("unit", metric.unit)
    metric.chart_type = data.get("chart_type", metric.chart_type)
    metric.color = data.get("color", metric.color)
    
    db.session.commit()
    return jsonify({"status": "ok"})


@main_bp.route("/api/custom-metrics/<int:metric_id>", methods=["DELETE"])
def delete_custom_metric(metric_id):
    """Delete a custom metric and all its entries."""
    metric = CustomMetric.query.get_or_404(metric_id)
    db.session.delete(metric)
    db.session.commit()
    return jsonify({"status": "ok"})


@main_bp.route("/api/custom-metrics/<int:metric_id>/entries", methods=["GET"])
def get_metric_entries(metric_id):
    """Get all entries for a custom metric."""
    metric = CustomMetric.query.get_or_404(metric_id)
    entries = CustomMetricEntry.query.filter_by(metric_id=metric_id).order_by(CustomMetricEntry.date).all()
    return jsonify({
        "metric": metric.to_dict(),
        "entries": [e.to_dict() for e in entries]
    })


@main_bp.route("/api/custom-metrics/<int:metric_id>/entries", methods=["POST"])
def add_metric_entry(metric_id):
    """Add or update an entry for a custom metric."""
    metric = CustomMetric.query.get_or_404(metric_id)
    data = request.get_json()
    
    entry_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    value = float(data["value"])
    
    # Check for existing entry on this date
    existing = CustomMetricEntry.query.filter_by(
        metric_id=metric_id,
        date=entry_date
    ).first()
    
    if existing:
        existing.value = value
        existing.notes = data.get("notes", existing.notes)
    else:
        entry = CustomMetricEntry(
            metric_id=metric_id,
            date=entry_date,
            value=value,
            notes=data.get("notes"),
        )
        db.session.add(entry)
    
    db.session.commit()
    return jsonify({"status": "ok"})


@main_bp.route("/api/custom-metrics/<int:metric_id>/entries/<int:entry_id>", methods=["DELETE"])
def delete_metric_entry(metric_id, entry_id):
    """Delete a custom metric entry."""
    entry = CustomMetricEntry.query.filter_by(id=entry_id, metric_id=metric_id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"status": "ok"})


# --- CSV Export ---

@main_bp.route("/export/weight")
def export_weight():
    """Export weight data as CSV."""
    entries = WeightEntry.query.order_by(WeightEntry.date).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "weight_kg"])
    for e in entries:
        writer.writerow([e.date.isoformat(), e.weight_kg])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=weight_export.csv"}
    )


@main_bp.route("/export/sleep")
def export_sleep():
    """Export sleep data as CSV."""
    entries = SleepEntry.query.order_by(SleepEntry.date).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "hours"])
    for e in entries:
        writer.writerow([e.date.isoformat(), e.hours])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sleep_export.csv"}
    )


@main_bp.route("/export/wake")
def export_wake():
    """Export wake time data as CSV."""
    entries = WakeTimeEntry.query.order_by(WakeTimeEntry.date).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "wake_time"])
    for e in entries:
        writer.writerow([e.date.isoformat(), e.wake_time.strftime("%H:%M:%S")])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=wake_time_export.csv"}
    )


@main_bp.route("/export/workout")
def export_workout():
    """Export workout data as CSV."""
    entries = WorkoutEntry.query.order_by(WorkoutEntry.date).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "workout_type", "duration_minutes", "notes"])
    for e in entries:
        writer.writerow([e.date.isoformat(), e.workout_type, e.duration_minutes or "", e.notes or ""])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=workout_export.csv"}
    )


@main_bp.route("/export/all")
def export_all():
    """Export all data as a single CSV with multiple sections."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Weight section
    writer.writerow(["# Weight Data"])
    writer.writerow(["date", "weight_kg"])
    for e in WeightEntry.query.order_by(WeightEntry.date).all():
        writer.writerow([e.date.isoformat(), e.weight_kg])
    writer.writerow([])
    
    # Sleep section
    writer.writerow(["# Sleep Data"])
    writer.writerow(["date", "hours"])
    for e in SleepEntry.query.order_by(SleepEntry.date).all():
        writer.writerow([e.date.isoformat(), e.hours])
    writer.writerow([])
    
    # Wake time section
    writer.writerow(["# Wake Time Data"])
    writer.writerow(["date", "wake_time"])
    for e in WakeTimeEntry.query.order_by(WakeTimeEntry.date).all():
        writer.writerow([e.date.isoformat(), e.wake_time.strftime("%H:%M:%S")])
    writer.writerow([])
    
    # Workout section
    writer.writerow(["# Workout Data"])
    writer.writerow(["date", "workout_type", "duration_minutes", "notes"])
    for e in WorkoutEntry.query.order_by(WorkoutEntry.date).all():
        writer.writerow([e.date.isoformat(), e.workout_type, e.duration_minutes or "", e.notes or ""])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=health_data_export.csv"}
    )
