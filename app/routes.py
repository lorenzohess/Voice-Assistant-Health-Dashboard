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
from app.models import WeightEntry, SleepEntry, WakeTimeEntry, WorkoutEntry, CalorieEntry
from app.pool_schedule import get_pool_status, get_weekly_schedule

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
    
    # Pool schedule
    pool_status = get_pool_status()
    pool_weekly = get_weekly_schedule()
    
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
        pool_status=pool_status,
        pool_weekly=pool_weekly,
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
