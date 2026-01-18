"""Command handlers that call the Flask REST API."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import requests

from .config import API_BASE_URL, DEBUG
from .intent import ParsedIntent


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    message: str  # Human-readable message for TTS
    data: Optional[dict] = None


def _api_post(endpoint: str, data: dict) -> requests.Response:
    """Make POST request to Flask API."""
    url = f"{API_BASE_URL}{endpoint}"
    if DEBUG:
        print(f"[Commands] POST {url} -> {data}")
    return requests.post(url, json=data, timeout=10)


def _api_get(endpoint: str) -> requests.Response:
    """Make GET request to Flask API."""
    url = f"{API_BASE_URL}{endpoint}"
    if DEBUG:
        print(f"[Commands] GET {url}")
    return requests.get(url, timeout=10)


def cmd_add_calories(params: dict) -> CommandResult:
    """Add calorie entry."""
    calories = params.get("calories")
    food = params.get("food", "Voice entry")
    
    if not calories:
        return CommandResult(False, "I didn't catch the calorie amount.")
    
    try:
        response = _api_post("/api/calories", {
            "date": date.today().isoformat(),
            "meal_name": food,
            "calories": calories,
        })
        
        if response.status_code == 200:
            result = response.json()
            warnings = result.get("warnings", [])
            msg = f"Added {calories} calories"
            if food != "Voice entry":
                msg += f" for {food}"
            if warnings:
                msg += f". Warning: {warnings[0]}"
            return CommandResult(True, msg, result)
        else:
            error = response.json().get("message", "Unknown error")
            return CommandResult(False, f"Failed to add calories: {error}")
            
    except requests.exceptions.ConnectionError:
        return CommandResult(False, "Cannot connect to dashboard server.")
    except Exception as e:
        if DEBUG:
            print(f"[Commands] Error: {e}")
        return CommandResult(False, "An error occurred while adding calories.")


def cmd_add_food(params: dict) -> CommandResult:
    """Add food with quantity (requires calorie lookup)."""
    food = params.get("food")
    quantity = params.get("quantity")
    unit = params.get("unit", "serving")
    
    if not food or not quantity:
        return CommandResult(False, "I need both a food name and quantity.")
    
    try:
        # Search for food
        response = _api_get(f"/api/foods/search?q={food}&limit=1")
        
        if response.status_code != 200 or not response.json():
            return CommandResult(False, f"I couldn't find {food} in the database.")
        
        foods = response.json()
        if not foods:
            return CommandResult(False, f"I couldn't find {food} in the database.")
        
        found_food = foods[0]
        food_id = found_food["id"]
        
        # Compute calories
        quantity_str = f"{quantity}{unit}"
        compute_response = _api_post("/api/foods/compute", {
            "food_id": food_id,
            "quantity": quantity_str,
        })
        
        if compute_response.status_code != 200:
            error = compute_response.json().get("message", "Computation failed")
            return CommandResult(False, f"Couldn't compute calories: {error}")
        
        computed = compute_response.json()
        calories = computed.get("calories", 0)
        
        # Add the entry
        add_response = _api_post("/api/calories", {
            "date": date.today().isoformat(),
            "meal_name": found_food["name"],
            "calories": calories,
            "food_id": food_id,
            "quantity": quantity_str,
        })
        
        if add_response.status_code == 200:
            return CommandResult(
                True,
                f"Added {quantity} {unit} of {found_food['name']}, {int(calories)} calories.",
                add_response.json()
            )
        else:
            return CommandResult(False, "Failed to add the food entry.")
            
    except requests.exceptions.ConnectionError:
        return CommandResult(False, "Cannot connect to dashboard server.")
    except Exception as e:
        if DEBUG:
            print(f"[Commands] Error: {e}")
        return CommandResult(False, "An error occurred while adding food.")


def cmd_log_weight(params: dict) -> CommandResult:
    """Log weight entry."""
    weight_lbs = params.get("weight_lbs")
    
    if not weight_lbs:
        return CommandResult(False, "I didn't catch your weight.")
    
    try:
        response = _api_post("/api/weight", {
            "date": date.today().isoformat(),
            "weight_lbs": round(weight_lbs, 1),
        })
        
        if response.status_code == 200:
            result = response.json()
            warnings = result.get("warnings", [])
            msg = f"Logged weight as {round(weight_lbs, 1)} pounds"
            if warnings:
                msg += f". Warning: {warnings[0]}"
            return CommandResult(True, msg, result)
        else:
            error = response.json().get("message", "Unknown error")
            return CommandResult(False, f"Failed to log weight: {error}")
            
    except requests.exceptions.ConnectionError:
        return CommandResult(False, "Cannot connect to dashboard server.")
    except Exception as e:
        if DEBUG:
            print(f"[Commands] Error: {e}")
        return CommandResult(False, "An error occurred while logging weight.")


def cmd_log_sleep(params: dict) -> CommandResult:
    """Log sleep duration."""
    hours = params.get("hours")
    
    if not hours:
        return CommandResult(False, "I didn't catch how many hours you slept.")
    
    try:
        response = _api_post("/api/sleep", {
            "date": date.today().isoformat(),
            "hours": hours,
        })
        
        if response.status_code == 200:
            result = response.json()
            warnings = result.get("warnings", [])
            msg = f"Logged {hours} hours of sleep"
            if warnings:
                msg += f". Warning: {warnings[0]}"
            return CommandResult(True, msg, result)
        else:
            error = response.json().get("message", "Unknown error")
            return CommandResult(False, f"Failed to log sleep: {error}")
            
    except requests.exceptions.ConnectionError:
        return CommandResult(False, "Cannot connect to dashboard server.")
    except Exception as e:
        if DEBUG:
            print(f"[Commands] Error: {e}")
        return CommandResult(False, "An error occurred while logging sleep.")


def cmd_log_wake(params: dict) -> CommandResult:
    """Log wake time."""
    hour = params.get("hour", 7)
    minute = params.get("minute", 0)
    
    # Handle 12-hour to 24-hour conversion edge case
    if hour == 12 and params.get("am"):
        hour = 0  # 12 AM = midnight
    
    wake_time = f"{hour:02d}:{minute:02d}:00"
    
    try:
        response = _api_post("/api/wake", {
            "date": date.today().isoformat(),
            "wake_time": wake_time,  # API expects 'wake_time' not 'time'
        })
        
        if response.status_code == 200:
            result = response.json()
            time_str = f"{hour}:{minute:02d}"
            return CommandResult(True, f"Logged wake time as {time_str}", result)
        else:
            error = response.json().get("message", "Unknown error")
            return CommandResult(False, f"Failed to log wake time: {error}")
            
    except requests.exceptions.ConnectionError:
        return CommandResult(False, "Cannot connect to dashboard server.")
    except Exception as e:
        if DEBUG:
            print(f"[Commands] Error: {e}")
        return CommandResult(False, "An error occurred while logging wake time.")


def cmd_log_vegetables(params: dict) -> CommandResult:
    """Log vegetable servings."""
    servings = params.get("servings")
    
    if not servings:
        return CommandResult(False, "I didn't catch the number of servings.")
    
    try:
        # First, find the vegetables metric ID
        # This assumes a custom metric named "Vegetable Servings" exists
        response = _api_get("/api/custom-metrics")
        
        if response.status_code != 200:
            return CommandResult(False, "Failed to get custom metrics.")
        
        data = response.json()
        metrics = data.get("metrics", [])
        veg_metric = None
        for m in metrics:
            if "vegetable" in m["name"].lower():
                veg_metric = m
                break
        
        if not veg_metric:
            return CommandResult(False, "Vegetable tracking is not set up.")
        
        # Add entry
        add_response = _api_post(f"/api/custom-metrics/{veg_metric['id']}/entries", {
            "date": date.today().isoformat(),
            "value": servings,
        })
        
        if add_response.status_code == 200:
            return CommandResult(True, f"Logged {servings} servings of vegetables.", add_response.json())
        else:
            return CommandResult(False, "Failed to log vegetables.")
            
    except requests.exceptions.ConnectionError:
        return CommandResult(False, "Cannot connect to dashboard server.")
    except Exception as e:
        if DEBUG:
            print(f"[Commands] Error: {e}")
        return CommandResult(False, "An error occurred while logging vegetables.")


def cmd_log_workout(params: dict) -> CommandResult:
    """Log workout."""
    duration = params.get("duration_minutes")
    
    if not duration:
        return CommandResult(False, "I didn't catch the workout duration.")
    
    try:
        response = _api_post("/api/workout", {
            "date": date.today().isoformat(),
            "duration_minutes": duration,
            "workout_type": "General",
        })
        
        if response.status_code == 200:
            return CommandResult(True, f"Logged a {duration} minute workout.", response.json())
        else:
            error = response.json().get("message", "Unknown error")
            return CommandResult(False, f"Failed to log workout: {error}")
            
    except requests.exceptions.ConnectionError:
        return CommandResult(False, "Cannot connect to dashboard server.")
    except Exception as e:
        if DEBUG:
            print(f"[Commands] Error: {e}")
        return CommandResult(False, "An error occurred while logging workout.")


def cmd_log_custom_metric(params: dict) -> CommandResult:
    """Log a value to a custom metric."""
    metric_id = params.get("metric_id")
    metric_name = params.get("metric_name", "metric")
    value = params.get("value")
    
    if not metric_id or value is None:
        return CommandResult(False, "Missing metric or value.")
    
    try:
        response = _api_post(f"/api/custom-metrics/{metric_id}/entries", {
            "date": date.today().isoformat(),
            "value": value,
        })
        
        if response.status_code == 200:
            return CommandResult(True, f"Logged {value} for {metric_name}.", response.json())
        else:
            return CommandResult(False, f"Failed to log {metric_name}.")
            
    except requests.exceptions.ConnectionError:
        return CommandResult(False, "Cannot connect to dashboard server.")
    except Exception as e:
        if DEBUG:
            print(f"[Commands] Error: {e}")
        return CommandResult(False, f"An error occurred while logging {metric_name}.")


# Map intent names to handler functions
COMMAND_HANDLERS = {
    "add_calories": cmd_add_calories,
    "add_food": cmd_add_food,
    "log_weight": cmd_log_weight,
    "log_sleep": cmd_log_sleep,
    "log_wake": cmd_log_wake,
    "log_vegetables": cmd_log_vegetables,
    "log_workout": cmd_log_workout,
    "log_custom_metric": cmd_log_custom_metric,
}


def execute_command(intent: ParsedIntent) -> CommandResult:
    """Execute a parsed intent."""
    handler = COMMAND_HANDLERS.get(intent.intent)
    
    if not handler:
        return CommandResult(
            False,
            f"I don't know how to handle that command.",
        )
    
    return handler(intent.params)


if __name__ == "__main__":
    import sys
    from .intent import parse_intent
    
    if "--test" in sys.argv and len(sys.argv) > 2:
        text = " ".join(sys.argv[2:])
        print(f"Testing command: '{text}'")
        
        intent = parse_intent(text)
        if intent:
            print(f"Parsed intent: {intent.intent} -> {intent.params}")
            result = execute_command(intent)
            print(f"Result: {result.success}")
            print(f"Message: {result.message}")
        else:
            print("Could not parse intent.")
    else:
        print("Usage: python -m voice.commands --test <command>")
        print("Example: python -m voice.commands --test 'add 200 calories'")
