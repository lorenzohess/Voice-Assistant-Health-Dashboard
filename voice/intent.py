"""Intent parsing using regex patterns with Ollama fallback."""

import re
import json
from dataclasses import dataclass
from typing import Optional, Any

import requests

import requests as req

from .config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_ENABLED, API_BASE_URL, DEBUG


# Cache for custom metric patterns (loaded from API)
_custom_metric_patterns = []
_patterns_loaded = False


def load_custom_metric_patterns():
    """Load custom metrics with voice keywords from the API."""
    global _custom_metric_patterns, _patterns_loaded
    
    try:
        response = req.get(f"{API_BASE_URL}/api/custom-metrics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            metrics = data.get("metrics", [])
            
            _custom_metric_patterns = []
            for m in metrics:
                keyword = m.get("voice_keyword")
                if keyword:
                    # Create pattern: keyword followed by number
                    # e.g., "medication 2" or "medication, 2"
                    pattern = rf"{re.escape(keyword.lower())}\s*,?\s*(\d+(?:\.\d+)?)"
                    _custom_metric_patterns.append({
                        "id": m["id"],
                        "name": m["name"],
                        "keyword": keyword,
                        "pattern": pattern,
                    })
            
            _patterns_loaded = True
            if DEBUG:
                print(f"[Intent] Loaded {len(_custom_metric_patterns)} custom metric patterns")
    except Exception as e:
        if DEBUG:
            print(f"[Intent] Failed to load custom metric patterns: {e}")


def parse_custom_metrics(text: str) -> Optional[ParsedIntent]:
    """Check text against custom metric voice patterns."""
    global _patterns_loaded
    
    # Load patterns if not already loaded
    if not _patterns_loaded:
        load_custom_metric_patterns()
    
    text_lower = text.lower()
    
    for metric in _custom_metric_patterns:
        match = re.search(metric["pattern"], text_lower)
        if match:
            value = float(match.group(1))
            if DEBUG:
                print(f"[Intent] Custom metric match: {metric['name']} -> {value}")
            return ParsedIntent(
                intent="log_custom_metric",
                params={
                    "metric_id": metric["id"],
                    "metric_name": metric["name"],
                    "value": value,
                },
                raw_text=text,
                confidence=1.0,
            )
    
    return None


def reload_custom_patterns():
    """Force reload of custom metric patterns."""
    global _patterns_loaded
    _patterns_loaded = False
    load_custom_metric_patterns()


@dataclass
class ParsedIntent:
    """Parsed intent from user speech."""
    intent: str  # e.g., "add_calories", "log_weight"
    params: dict  # e.g., {"calories": 200, "food": "eggs"}
    raw_text: str
    confidence: float = 1.0  # 1.0 for regex, lower for Ollama


# Word-to-number mapping (Vosk often transcribes numbers as words)
WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
    # Fractions for sleep
    "half": 0.5, "quarter": 0.25,
}

# Time words for wake time (e.g., "seven thirty" = 7:30)
TIME_MINUTES = {
    "oh one": 1, "oh two": 2, "oh three": 3, "oh four": 4, "oh five": 5,
    "oh six": 6, "oh seven": 7, "oh eight": 8, "oh nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "twenty one": 21, "twenty two": 22, "twenty three": 23,
    "twenty four": 24, "twenty five": 25, "twenty six": 26, "twenty seven": 27,
    "twenty eight": 28, "twenty nine": 29, "thirty": 30, "thirty one": 31,
    "thirty two": 32, "thirty three": 33, "thirty four": 34, "thirty five": 35,
    "thirty six": 36, "thirty seven": 37, "thirty eight": 38, "thirty nine": 39,
    "forty": 40, "forty five": 45, "fifty": 50, "fifty five": 55,
}


def words_to_number(text: str) -> Optional[float]:
    """Convert word-based numbers to numeric value.
    
    Examples:
        "five hundred" -> 500
        "two thousand" -> 2000
        "eighty five" -> 85
        "8" -> 8
        "7.5" -> 7.5
    """
    text = text.strip().lower()
    
    # Already a number?
    try:
        return float(text)
    except ValueError:
        pass
    
    # Parse word numbers
    words = text.split()
    total = 0
    current = 0
    
    for word in words:
        if word in WORD_NUMBERS:
            val = WORD_NUMBERS[word]
            if val == 100:
                current = current * 100 if current else 100
            elif val == 1000:
                current = current * 1000 if current else 1000
                total += current
                current = 0
            else:
                current += val
        elif word == "and":
            continue
        else:
            # Unknown word, try as number
            try:
                current += float(word)
            except ValueError:
                pass
    
    total += current
    return total if total > 0 else None


def parse_time_words(text: str) -> tuple:
    """
    Parse time expressions like "seven thirty am" -> (7, 30, 'am').
    Returns (hour, minute, ampm) or (None, None, None) if not a time.
    """
    # Match patterns like "seven thirty am", "eight fifteen pm", "seven am"
    time_pattern = r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(oh\s+\w+|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|twenty\s+\w+|thirty|thirty\s+\w+|forty|forty\s+\w+|fifty|fifty\s+\w+)?\s*(am|pm|a\s*m|p\s*m)?\b'
    
    match = re.search(time_pattern, text.lower())
    if not match:
        return None, None, None
    
    hour_word = match.group(1)
    minute_word = match.group(2)
    ampm = match.group(3)
    
    # Convert hour
    hour = WORD_NUMBERS.get(hour_word, 0)
    
    # Convert minutes
    minute = 0
    if minute_word:
        minute_word = minute_word.strip()
        if minute_word in TIME_MINUTES:
            minute = TIME_MINUTES[minute_word]
        else:
            # Try word_to_number for compound like "twenty five"
            minute = int(words_to_number(minute_word) or 0)
    
    if ampm:
        ampm = ampm.replace(' ', '').lower()
    
    return hour, minute, ampm


def preprocess_text(text: str) -> str:
    """Preprocess text to normalize number words to digits.
    
    Handles special cases to avoid incorrect conversions.
    """
    result = text.lower()
    
    # DON'T preprocess if this looks like a wake time command
    # (we handle those with special parsing)
    if re.search(r'woke|wake', result):
        return result
    
    # Handle sleep fractions BEFORE general number conversion
    # "eight and a half" -> "8.5", "seven and three quarters" -> "7.75"
    result = re.sub(r'\b(\w+)\s+and\s+a\s+half\b', 
                    lambda m: str(float(words_to_number(m.group(1)) or 0) + 0.5) if words_to_number(m.group(1)) else m.group(0), 
                    result)
    result = re.sub(r'\b(\w+)\s+and\s+a\s+quarter\b', 
                    lambda m: str(float(words_to_number(m.group(1)) or 0) + 0.25) if words_to_number(m.group(1)) else m.group(0), 
                    result)
    result = re.sub(r'\b(\w+)\s+and\s+three\s+quarters?\b', 
                    lambda m: str(float(words_to_number(m.group(1)) or 0) + 0.75) if words_to_number(m.group(1)) else m.group(0), 
                    result)
    
    # General word-to-number conversion (but NOT for fraction words already handled)
    # Only convert standalone numbers, not parts of "and a half" etc.
    patterns = [
        # "five hundred calories" -> "500 calories"
        (r'\b((?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)(?:\s+(?:and\s+)?(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand))*)\b',
         lambda m: str(int(words_to_number(m.group(1)))) if words_to_number(m.group(1)) else m.group(1)),
    ]
    
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


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
# Note: Text is preprocessed so word numbers become digits
PATTERNS = [
    # Calories - direct amount (matches "add 500 calories", "had 500 calories", "added 500 calories")
    (
        r"(?:add(?:ed)?|log(?:ged)?|ate|had|eaten)\s+(\d+)\s*(?:calories?|cals?|kcal)",
        "add_calories",
        lambda m: {"calories": int(m.group(1))}
    ),
    
    # Calories - food with calories ("add eggs 140 calories")
    (
        r"(?:add(?:ed)?|log(?:ged)?|ate|had)\s+(.+?)\s+(\d+)\s*(?:calories?|cals?|kcal)",
        "add_calories",
        lambda m: {"food": m.group(1).strip(), "calories": int(m.group(2))}
    ),
    
    # Vegetables - "vegetables, 3 servings" or "vegetables 3 servings"
    (
        r"vegetables?\s*,?\s*(\d+)\s*(?:servings?)?",
        "log_vegetables",
        lambda m: {"servings": int(m.group(1))}
    ),
    
    # Calories - food lookup (will need API to compute)
    # This pattern is greedy, so specific patterns (like vegetables) must come first
    (
        r"(?:add(?:ed)?|log(?:ged)?|ate|had)\s+(\d+(?:\.\d+)?)\s*(g|grams?|oz|ounces?|cups?|pieces?|servings?|tbsp|tablespoons?|tsp|teaspoons?)?\s*(?:of\s+)?(.+?)(?:\s+to\s+calories)?$",
        "add_food",
        lambda m: {
            "quantity": float(m.group(1)),
            "unit": m.group(2) or "serving",
            "food": m.group(3).strip()
        }
    ),
    
    # Weight
    (
        r"(?:my\s+)?weight\s+(?:is\s+|was\s+|today\s+)?(\d+(?:\.\d+)?)\s*(kg|lbs?|pounds?|kilos?)?",
        "log_weight",
        lambda m: {"weight_kg": convert_weight_to_kg(float(m.group(1)), m.group(2))}
    ),
    (
        r"(?:i\s+)?weigh(?:ed)?\s+(\d+(?:\.\d+)?)\s*(kg|lbs?|pounds?|kilos?)?",
        "log_weight",
        lambda m: {"weight_kg": convert_weight_to_kg(float(m.group(1)), m.group(2))}
    ),
    
    # Sleep - with fractions: "8 hours", "7 and a half hours", "6.5 hours"
    (
        r"(?:i\s+)?slept\s+(\d+)\s+and\s+a\s+half\s*(?:hours?)?",
        "log_sleep",
        lambda m: {"hours": float(m.group(1)) + 0.5}
    ),
    (
        r"(?:i\s+)?slept\s+(\d+)\s+and\s+a\s+quarter\s*(?:hours?)?",
        "log_sleep",
        lambda m: {"hours": float(m.group(1)) + 0.25}
    ),
    (
        r"(?:i\s+)?slept\s+(\d+)\s+and\s+three\s+quarters?\s*(?:hours?)?",
        "log_sleep",
        lambda m: {"hours": float(m.group(1)) + 0.75}
    ),
    (
        r"(?:i\s+)?slept\s+(\d+(?:\.\d+)?)\s*(?:hours?)?",
        "log_sleep",
        lambda m: {"hours": float(m.group(1))}
    ),
    (
        r"(?:got\s+)?(\d+)\s+and\s+a\s+half\s*(?:hours?\s+)?(?:of\s+)?sleep",
        "log_sleep",
        lambda m: {"hours": float(m.group(1)) + 0.5}
    ),
    (
        r"(?:got\s+)?(\d+(?:\.\d+)?)\s*(?:hours?\s+)?(?:of\s+)?sleep",
        "log_sleep",
        lambda m: {"hours": float(m.group(1))}
    ),
    
    # Wake time - digit format: "7 am", "7:30 am", "7 30 am"
    (
        r"(?:i\s+)?woke\s+(?:up\s+)?(?:at\s+)?(\d{1,2})\s+(\d{2})\s*(am|pm)?",
        "log_wake",
        lambda m: {
            "hour": int(m.group(1)) + (12 if m.group(3) and m.group(3).lower() == "pm" and int(m.group(1)) != 12 else 0),
            "minute": int(m.group(2))
        }
    ),
    (
        r"(?:i\s+)?woke\s+(?:up\s+)?(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
        "log_wake",
        lambda m: {
            "hour": int(m.group(1)) + (12 if m.group(3) and m.group(3).lower() == "pm" and int(m.group(1)) != 12 else 0),
            "minute": int(m.group(2)) if m.group(2) else 0
        }
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


def parse_wake_time_words(text: str) -> Optional[ParsedIntent]:
    """Special parser for wake time with word-based times like 'seven thirty am'."""
    # Check if this is a wake time command
    wake_match = re.search(r'woke\s+(?:up\s+)?(?:at\s+)?(.+)', text.lower())
    if not wake_match:
        return None
    
    time_part = wake_match.group(1).strip()
    
    # Try to parse the time part
    hour, minute, ampm = parse_time_words(time_part)
    
    if hour is None:
        return None
    
    # Handle AM/PM
    if ampm == 'pm' and hour != 12:
        hour += 12
    elif ampm == 'am' and hour == 12:
        hour = 0
    
    if DEBUG:
        print(f"[Intent] Parsed wake time: {hour}:{minute:02d} from '{time_part}'")
    
    return ParsedIntent(
        intent="log_wake",
        params={"hour": hour, "minute": minute},
        raw_text=text,
        confidence=1.0
    )


def parse_with_regex(text: str) -> Optional[ParsedIntent]:
    """Try to parse intent using regex patterns."""
    # Special handling for wake time (word-based times like "seven thirty am")
    if re.search(r'woke', text.lower()):
        result = parse_wake_time_words(text)
        if result:
            return result
    
    # Preprocess to convert word numbers to digits
    processed = preprocess_text(text)
    
    if DEBUG and processed != text.lower():
        print(f"[Intent] Preprocessed: '{text}' -> '{processed}'")
    
    for pattern, intent, extractor in PATTERNS:
        match = re.search(pattern, processed, re.IGNORECASE)
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


# Valid intent names that Ollama can return
VALID_INTENTS = {"add_calories", "add_food", "log_weight", "log_sleep", "log_wake", "log_vegetables", "log_workout", "log_custom_metric"}


def parse_with_ollama(text: str) -> Optional[ParsedIntent]:
    """Use Ollama LLM to parse intent as fallback."""
    if DEBUG:
        print(f"[Intent] Using Ollama fallback for: {text}")
    
    prompt = f"""Parse this health tracking voice command into JSON.

VALID INTENTS (use exactly these names):
- add_calories: for logging calorie intake
- log_weight: for logging body weight
- log_sleep: for logging sleep hours
- log_vegetables: for logging vegetable servings
- log_workout: for logging exercise

Command: "{text}"

Respond with ONLY a JSON object, no other text:
{{"intent": "<intent_name>", "params": {{"<param>": <value>}}}}

Examples:
- "had 500 calories" -> {{"intent": "add_calories", "params": {{"calories": 500}}}}
- "I weigh 180 pounds" -> {{"intent": "log_weight", "params": {{"weight_kg": 81.6}}}}
- "slept 8 hours" -> {{"intent": "log_sleep", "params": {{"hours": 8}}}}

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
                
                # Validate intent is one we know
                if intent in VALID_INTENTS:
                    if DEBUG:
                        print(f"[Intent] Ollama parsed: {intent} -> {params}")
                    return ParsedIntent(
                        intent=intent,
                        params=params,
                        raw_text=text,
                        confidence=0.7
                    )
                else:
                    if DEBUG:
                        print(f"[Intent] Ollama returned invalid intent: {intent}")
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
    Checks custom metrics first, then regex, optionally Ollama.
    """
    if not text or not text.strip():
        return None
    
    # Check custom metric patterns first (user-defined)
    result = parse_custom_metrics(text)
    if result:
        return result
    
    # Try regex patterns (built-in)
    result = parse_with_regex(text)
    if result:
        return result
    
    # Fallback to Ollama (slow, unreliable with small models)
    if OLLAMA_ENABLED:
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
