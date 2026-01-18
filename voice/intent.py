"""Intent parsing using regex patterns with Ollama fallback."""

import re
import json
from dataclasses import dataclass
from typing import Optional, Any

import requests

from .config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, DEBUG


@dataclass
class ParsedIntent:
    """Parsed intent from user speech."""
    intent: str  # e.g., "add_calories", "log_weight"
    params: dict  # e.g., {"calories": 200, "food": "eggs"}
    raw_text: str
    confidence: float = 1.0  # 1.0 for regex, lower for Ollama


# Unit conversion helpers
def convert_weight_to_kg(value: float, unit: str) -> float:
    """Convert weight to kilograms."""
    unit = unit.lower() if unit else "kg"
    if unit in ("lb", "lbs", "pound", "pounds"):
        return value * 0.453592
    elif unit in ("kg", "kilo", "kilos", "kilogram", "kilograms"):
        return value
    return value  # Assume kg if unknown


def convert_to_grams(value: float, unit: str) -> float:
    """Convert mass to grams."""
    unit = unit.lower() if unit else "g"
    conversions = {
        "g": 1, "gram": 1, "grams": 1,
        "oz": 28.35, "ounce": 28.35, "ounces": 28.35,
        "lb": 453.6, "lbs": 453.6, "pound": 453.6, "pounds": 453.6,
        "kg": 1000, "kilo": 1000, "kilos": 1000,
    }
    return value * conversions.get(unit, 1)


# Regex patterns: (pattern, intent_name, param_extractor)
PATTERNS = [
    # Calories - direct amount
    (
        r"(?:add|log|ate|had)\s+(\d+)\s*(?:calories?|cals?|kcal)",
        "add_calories",
        lambda m: {"calories": int(m.group(1))}
    ),
    
    # Calories - food with calories
    (
        r"(?:add|log|ate|had)\s+(.+?)\s+(\d+)\s*(?:calories?|cals?|kcal)",
        "add_calories",
        lambda m: {"food": m.group(1).strip(), "calories": int(m.group(2))}
    ),
    
    # Calories - food lookup (will need API to compute)
    (
        r"(?:add|log|ate|had)\s+(\d+(?:\.\d+)?)\s*(g|oz|cup|cups|piece|pieces|serving|servings)?\s*(?:of\s+)?(.+?)(?:\s+to\s+calories)?$",
        "add_food",
        lambda m: {
            "quantity": float(m.group(1)),
            "unit": m.group(2) or "serving",
            "food": m.group(3).strip()
        }
    ),
    
    # Weight
    (
        r"(?:my\s+)?weight\s+(?:is\s+|today\s+)?(\d+(?:\.\d+)?)\s*(kg|lbs?|pounds?|kilos?)?",
        "log_weight",
        lambda m: {"weight_kg": convert_weight_to_kg(float(m.group(1)), m.group(2))}
    ),
    (
        r"(?:i\s+)?weigh\s+(\d+(?:\.\d+)?)\s*(kg|lbs?|pounds?|kilos?)?",
        "log_weight",
        lambda m: {"weight_kg": convert_weight_to_kg(float(m.group(1)), m.group(2))}
    ),
    
    # Sleep
    (
        r"(?:i\s+)?slept\s+(\d+(?:\.\d+)?)\s*(?:hours?)?",
        "log_sleep",
        lambda m: {"hours": float(m.group(1))}
    ),
    (
        r"(?:got\s+)?(\d+(?:\.\d+)?)\s*(?:hours?\s+)?(?:of\s+)?sleep",
        "log_sleep",
        lambda m: {"hours": float(m.group(1))}
    ),
    
    # Wake time
    (
        r"(?:i\s+)?woke\s+(?:up\s+)?(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
        "log_wake",
        lambda m: {
            "hour": int(m.group(1)) + (12 if m.group(3) and m.group(3).lower() == "pm" and int(m.group(1)) != 12 else 0),
            "minute": int(m.group(2)) if m.group(2) else 0
        }
    ),
    
    # Vegetables
    (
        r"(?:add|log|ate|had)\s+(\d+)\s*(?:servings?\s+)?(?:of\s+)?vegetables?",
        "log_vegetables",
        lambda m: {"servings": int(m.group(1))}
    ),
    
    # Workout
    (
        r"(?:i\s+)?(?:worked\s+out|exercised|did\s+(?:a\s+)?workout)\s*(?:for\s+)?(\d+)\s*(?:minutes?|mins?)?",
        "log_workout",
        lambda m: {"duration_minutes": int(m.group(1))}
    ),
    (
        r"(\d+)\s*(?:minute|min)\s*(?:workout|exercise)",
        "log_workout",
        lambda m: {"duration_minutes": int(m.group(1))}
    ),
]


def parse_with_regex(text: str) -> Optional[ParsedIntent]:
    """Try to parse intent using regex patterns."""
    text_lower = text.lower().strip()
    
    for pattern, intent, extractor in PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            try:
                params = extractor(match)
                if DEBUG:
                    print(f"[Intent] Regex match: {intent} -> {params}")
                return ParsedIntent(
                    intent=intent,
                    params=params,
                    raw_text=text,
                    confidence=1.0
                )
            except Exception as e:
                if DEBUG:
                    print(f"[Intent] Regex extractor error: {e}")
                continue
    
    return None


def parse_with_ollama(text: str) -> Optional[ParsedIntent]:
    """Use Ollama LLM to parse intent as fallback."""
    if DEBUG:
        print(f"[Intent] Using Ollama fallback for: {text}")
    
    prompt = f"""Parse this health tracking command into a JSON object.
Possible intents: add_calories, add_food, log_weight, log_sleep, log_wake, log_vegetables, log_workout

Command: "{text}"

Return ONLY a JSON object with "intent" and "params" fields. Examples:
- "add 200 calories" -> {{"intent": "add_calories", "params": {{"calories": 200}}}}
- "I weigh 180 pounds" -> {{"intent": "log_weight", "params": {{"weight_kg": 81.6}}}}
- "slept 8 hours" -> {{"intent": "log_sleep", "params": {{"hours": 8}}}}
- "add 2 servings vegetables" -> {{"intent": "log_vegetables", "params": {{"servings": 2}}}}

If you cannot parse the command, return {{"intent": "unknown", "params": {{}}}}

JSON:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=OLLAMA_TIMEOUT,
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "")
            
            # Extract JSON from response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(response_text[start:end])
                intent = parsed.get("intent", "unknown")
                params = parsed.get("params", {})
                
                if intent != "unknown":
                    if DEBUG:
                        print(f"[Intent] Ollama parsed: {intent} -> {params}")
                    return ParsedIntent(
                        intent=intent,
                        params=params,
                        raw_text=text,
                        confidence=0.7
                    )
    except requests.exceptions.Timeout:
        if DEBUG:
            print("[Intent] Ollama timeout")
    except Exception as e:
        if DEBUG:
            print(f"[Intent] Ollama error: {e}")
    
    return None


def parse_intent(text: str) -> Optional[ParsedIntent]:
    """
    Parse user speech into structured intent.
    Tries regex first, falls back to Ollama.
    """
    if not text or not text.strip():
        return None
    
    # Try regex first (fast)
    result = parse_with_regex(text)
    if result:
        return result
    
    # Fallback to Ollama (slow but flexible)
    result = parse_with_ollama(text)
    if result:
        return result
    
    # Could not parse
    if DEBUG:
        print(f"[Intent] Could not parse: {text}")
    return None


if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv and len(sys.argv) > 2:
        text = " ".join(sys.argv[2:])
        print(f"Parsing: '{text}'")
        result = parse_intent(text)
        if result:
            print(f"Intent: {result.intent}")
            print(f"Params: {result.params}")
            print(f"Confidence: {result.confidence}")
        else:
            print("Could not parse intent.")
    else:
        # Interactive test mode
        print("Intent Parser Test Mode")
        print("Enter commands to parse (Ctrl+C to exit):")
        print()
        
        test_commands = [
            "add 200 calories",
            "add eggs 140 calories",
            "add 2 cups of rice to calories",
            "my weight is 180 pounds",
            "I weigh 82 kilos",
            "slept 7 hours",
            "I got 8 hours of sleep",
            "woke up at 7 am",
            "add 3 servings vegetables",
            "worked out for 45 minutes",
            "30 minute workout",
        ]
        
        for cmd in test_commands:
            print(f"'{cmd}'")
            result = parse_intent(cmd)
            if result:
                print(f"  -> {result.intent}: {result.params}")
            else:
                print(f"  -> FAILED TO PARSE")
            print()
