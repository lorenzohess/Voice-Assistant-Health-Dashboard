"""Data validation logic for health entries."""

from dataclasses import dataclass
from typing import Optional
from datetime import date

from app import db
from app.models import WeightEntry, CalorieEntry


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    has_warning: bool
    error_message: Optional[str] = None
    warning_message: Optional[str] = None


def validate_weight(weight_kg: float, entry_date: date) -> ValidationResult:
    """
    Validate weight entry.
    Hard limits: 20-200 kg
    Warning: Change > 5 kg from previous entry
    """
    # Hard limits
    if weight_kg < 20:
        return ValidationResult(
            is_valid=False,
            has_warning=False,
            error_message="Weight must be at least 20 kg"
        )
    if weight_kg > 200:
        return ValidationResult(
            is_valid=False,
            has_warning=False,
            error_message="Weight must be at most 200 kg"
        )
    
    # Check for large change from previous entry
    previous = WeightEntry.query.filter(
        WeightEntry.date < entry_date
    ).order_by(WeightEntry.date.desc()).first()
    
    if previous and abs(weight_kg - previous.weight_kg) > 5:
        return ValidationResult(
            is_valid=True,
            has_warning=True,
            warning_message=f"Large change detected: {abs(weight_kg - previous.weight_kg):.1f} kg from previous ({previous.weight_kg} kg)"
        )
    
    return ValidationResult(is_valid=True, has_warning=False)


def validate_calories_single(calories: float) -> ValidationResult:
    """
    Validate single food item calories.
    Hard limits: 0-2000
    Warning: > 2000 (requires confirmation)
    """
    if calories < 0:
        return ValidationResult(
            is_valid=False,
            has_warning=False,
            error_message="Calories cannot be negative"
        )
    if calories > 2000:
        return ValidationResult(
            is_valid=True,
            has_warning=True,
            warning_message=f"High calorie item: {calories} cal. Please confirm."
        )
    
    return ValidationResult(is_valid=True, has_warning=False)


def validate_calories_daily(entry_date: date, new_calories: float = 0) -> ValidationResult:
    """
    Validate daily calorie total.
    Warning: < 1000 or > 2500
    """
    # Sum existing entries for the date
    existing_total = db.session.query(
        db.func.sum(CalorieEntry.calories)
    ).filter(CalorieEntry.date == entry_date).scalar() or 0
    
    total = existing_total + new_calories
    
    if total < 1000 and total > 0:
        return ValidationResult(
            is_valid=True,
            has_warning=True,
            warning_message=f"Low daily intake: {total:.0f} cal"
        )
    if total > 2500:
        return ValidationResult(
            is_valid=True,
            has_warning=True,
            warning_message=f"High daily intake: {total:.0f} cal"
        )
    
    return ValidationResult(is_valid=True, has_warning=False)


def validate_sleep(hours: float) -> ValidationResult:
    """
    Validate sleep hours.
    Hard limits: 0-24
    Warning: < 3 or > 12
    """
    if hours < 0:
        return ValidationResult(
            is_valid=False,
            has_warning=False,
            error_message="Sleep hours cannot be negative"
        )
    if hours > 24:
        return ValidationResult(
            is_valid=False,
            has_warning=False,
            error_message="Sleep hours cannot exceed 24"
        )
    if hours < 3:
        return ValidationResult(
            is_valid=True,
            has_warning=True,
            warning_message=f"Very short sleep: {hours} hours"
        )
    if hours > 12:
        return ValidationResult(
            is_valid=True,
            has_warning=True,
            warning_message=f"Very long sleep: {hours} hours"
        )
    
    return ValidationResult(is_valid=True, has_warning=False)


def validate_wake_time(wake_time_str: str) -> ValidationResult:
    """
    Validate wake time format (ISO 8601: HH:MM:SS or HH:MM).
    """
    import re
    
    # Accept HH:MM or HH:MM:SS
    pattern = r'^([01]?[0-9]|2[0-3]):([0-5][0-9])(:[0-5][0-9])?$'
    if not re.match(pattern, wake_time_str):
        return ValidationResult(
            is_valid=False,
            has_warning=False,
            error_message="Invalid time format. Use HH:MM or HH:MM:SS"
        )
    
    return ValidationResult(is_valid=True, has_warning=False)


def validate_macros(calories: float, protein_g: float, carbs_g: float, fat_g: float) -> ValidationResult:
    """
    Validate that macros are consistent with calories.
    Formula: calories ≈ protein*4 + carbs*4 + fat*9 (within 15%)
    """
    if protein_g is None or carbs_g is None or fat_g is None:
        # Can't validate if macros not provided
        return ValidationResult(is_valid=True, has_warning=False)
    
    expected = (protein_g * 4) + (carbs_g * 4) + (fat_g * 9)
    
    if expected == 0:
        return ValidationResult(is_valid=True, has_warning=False)
    
    diff_percent = abs(calories - expected) / expected
    
    if diff_percent > 0.15:
        return ValidationResult(
            is_valid=True,
            has_warning=True,
            warning_message=f"Calorie/macro mismatch: {calories:.0f} cal entered, but macros suggest {expected:.0f} cal"
        )
    
    return ValidationResult(is_valid=True, has_warning=False)
