#!/usr/bin/env python3
"""
Generate natural language aliases for foods using an LLM.

This script iterates through foods in the database and generates
natural language aliases that users might use to search for them.

Usage:
    # Interactive mode (default)
    python scripts/generate_aliases.py --provider openai
    
    # Automatic mode - no user interaction
    python scripts/generate_aliases.py --provider openai --auto
    
    # Process all foods automatically
    python scripts/generate_aliases.py --provider openai --auto --all
    
    # Dry run - preview without saving
    python scripts/generate_aliases.py --provider openai --auto --dry-run
"""

import sys
import os
import argparse
import json
import time
from typing import Callable, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.food_db import (
    init_food_db,
    get_food_db_connection,
    add_alias,
    get_food_aliases,
)


def get_foods_needing_aliases(min_aliases: int = 3, limit: int = None, all_foods: bool = False) -> list[dict]:
    """Get foods that have fewer than min_aliases aliases."""
    conn = get_food_db_connection()
    cursor = conn.cursor()

    if all_foods:
        # Get ALL foods, regardless of alias count
        query = """
            SELECT f.id, f.name, f.category, f.unit_type, f.canonical_unit,
                   COUNT(a.id) as alias_count
            FROM foods f
            LEFT JOIN food_aliases a ON f.id = a.food_id
            GROUP BY f.id
            ORDER BY f.name ASC
        """
    else:
        query = f"""
            SELECT f.id, f.name, f.category, f.unit_type, f.canonical_unit,
                   COUNT(a.id) as alias_count
            FROM foods f
            LEFT JOIN food_aliases a ON f.id = a.food_id
            GROUP BY f.id
            HAVING alias_count < {min_aliases}
            ORDER BY alias_count ASC, f.name ASC
        """
    
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "unit_type": row[3],
            "canonical_unit": row[4],
            "alias_count": row[5],
        }
        for row in rows
    ]


def generate_aliases_ollama(food_name: str, category: str = None) -> list[str]:
    """Generate aliases using Ollama (local LLM)."""
    try:
        import requests
    except ImportError:
        print("Error: requests library not installed. Run: pip install requests")
        return []

    prompt = f"""Generate 3-5 natural ways a person might say or search for this food item.
Food: {food_name}
{f'Category: {category}' if category else ''}

Return ONLY a JSON array of strings, no explanation. Example:
["grilled chicken", "chicken breast", "chicken"]

Aliases:"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )

        if response.status_code == 200:
            result = response.json()
            text = result.get("response", "")
            try:
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    aliases = json.loads(text[start:end])
                    return [a.lower().strip() for a in aliases if isinstance(a, str)]
            except json.JSONDecodeError:
                pass
    except Exception as e:
        print(f"  Ollama error: {e}")

    return []


def generate_aliases_openai(food_name: str, category: str = None, retries: int = 3) -> list[str]:
    """Generate aliases using OpenAI API with retry logic."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  Error: OPENAI_API_KEY not set")
        return []

    try:
        import requests
    except ImportError:
        print("Error: requests library not installed")
        return []

    prompt = f"""Generate 3-5 natural ways a person might say or search for this food item when logging calories. 
Include common abbreviations, nicknames, and how people casually refer to this food.
Do not include questions or "near me" phrases.

Food: {food_name}
{f'Category: {category}' if category else ''}

Return ONLY a JSON array of lowercase strings, no explanation."""

    for attempt in range(retries):
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",  # Cost-effective model
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 150,
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                text = result["choices"][0]["message"]["content"]
                try:
                    # Find JSON array in response
                    start = text.find("[")
                    end = text.rfind("]") + 1
                    if start >= 0 and end > start:
                        aliases = json.loads(text[start:end])
                        return [a.lower().strip() for a in aliases if isinstance(a, str) and a.strip()]
                except json.JSONDecodeError:
                    pass
            elif response.status_code == 429:
                # Rate limited - wait and retry
                wait_time = 2 ** attempt
                print(f"  Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                print(f"  API error: {response.status_code} - {response.text[:100]}")
                
        except requests.exceptions.Timeout:
            print(f"  Timeout (attempt {attempt + 1}/{retries})")
            time.sleep(1)
        except Exception as e:
            print(f"  OpenAI error: {e}")
            break

    return []


def generate_aliases_manual(food_name: str, category: str = None) -> list[str]:
    """Manual alias entry (no LLM)."""
    return []


def process_food_interactive(food: dict, generate_fn: Callable, dry_run: bool = False) -> int:
    """Process a single food interactively."""
    print(f"\n{'='*60}")
    print(f"Food: {food['name']}")
    print(f"Category: {food['category'] or 'N/A'}")
    print(f"Unit: {food['canonical_unit']} ({food['unit_type']})")

    existing = get_food_aliases(food["id"])
    if existing:
        print(f"Existing aliases: {', '.join(existing)}")

    print("\nGenerating suggestions...")
    suggestions = generate_fn(food["name"], food["category"])

    if suggestions:
        print(f"Suggested aliases: {', '.join(suggestions)}")
    else:
        print("No suggestions generated.")

    print("\nOptions:")
    print("  [Enter] Accept suggestions" if suggestions else "  [Enter] Skip this food")
    print("  [e] Edit/add custom aliases")
    print("  [s] Skip this food")
    print("  [q] Quit")

    choice = input("> ").strip().lower()

    if choice == "q":
        return -1

    if choice == "s":
        print("Skipped.")
        return 0

    aliases_to_add = []

    if choice == "e":
        print("Enter aliases (comma-separated):")
        custom = input("> ").strip()
        if custom:
            aliases_to_add = [a.strip().lower() for a in custom.split(",") if a.strip()]
    elif suggestions:
        aliases_to_add = suggestions
    else:
        print("No new aliases to add.")
        return 0

    if dry_run:
        print(f"  [DRY RUN] Would add: {', '.join(aliases_to_add)}")
        return len(aliases_to_add)

    added = 0
    for alias in aliases_to_add:
        if alias and alias not in existing:
            if add_alias(food["id"], alias):
                added += 1
                print(f"  Added: {alias}")

    print(f"Added {added} new aliases.")
    return added


def process_food_auto(food: dict, generate_fn: Callable, dry_run: bool = False, verbose: bool = True) -> int:
    """Process a single food automatically (no user interaction)."""
    existing = get_food_aliases(food["id"])
    
    # Generate suggestions
    suggestions = generate_fn(food["name"], food["category"])
    
    if not suggestions:
        if verbose:
            print(f"  {food['name'][:50]:50s} - no suggestions")
        return 0
    
    # Filter out existing aliases
    new_aliases = [a for a in suggestions if a.lower() not in [e.lower() for e in existing]]
    
    if not new_aliases:
        if verbose:
            print(f"  {food['name'][:50]:50s} - all suggestions already exist")
        return 0
    
    if dry_run:
        if verbose:
            print(f"  {food['name'][:50]:50s} - would add: {', '.join(new_aliases)}")
        return len(new_aliases)
    
    # Save aliases
    added = 0
    for alias in new_aliases:
        if add_alias(food["id"], alias):
            added += 1
    
    if verbose:
        print(f"  {food['name'][:50]:50s} - added {added}: {', '.join(new_aliases[:3])}{'...' if len(new_aliases) > 3 else ''}")
    
    return added


def main():
    parser = argparse.ArgumentParser(description="Generate food aliases using LLM")
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai", "manual"],
        default="manual",
        help="LLM provider to use (default: manual)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of foods to process"
    )
    parser.add_argument(
        "--auto", action="store_true", help="Automatic mode - no user interaction"
    )
    parser.add_argument(
        "--all", action="store_true", dest="all_foods", 
        help="Process all foods (not just those needing aliases)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without saving to database"
    )
    parser.add_argument(
        "--delay", type=float, default=0.2, 
        help="Delay between API calls in seconds (default: 0.2)"
    )
    parser.add_argument(
        "--min-aliases", type=int, default=3,
        help="Only process foods with fewer than this many aliases (default: 3)"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Less verbose output in auto mode"
    )

    args = parser.parse_args()

    # Select generator function
    generators = {
        "ollama": generate_aliases_ollama,
        "openai": generate_aliases_openai,
        "manual": generate_aliases_manual,
    }
    generate_fn = generators[args.provider]

    print("=" * 60)
    print("Food Alias Generator")
    print("=" * 60)
    print(f"Provider: {args.provider}")
    print(f"Mode: {'automatic' if args.auto else 'interactive'}")
    if args.dry_run:
        print("DRY RUN - no changes will be saved")
    print()

    # Check API key for OpenAI
    if args.provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    # Initialize database
    init_food_db()

    # Get foods needing aliases
    foods = get_foods_needing_aliases(
        min_aliases=args.min_aliases,
        limit=args.limit,
        all_foods=args.all_foods
    )

    if not foods:
        print("No foods need aliases. Nothing to do.")
        return

    print(f"Found {len(foods)} foods to process.")
    
    if args.auto:
        print(f"Processing automatically with {args.delay}s delay between calls...")
        print()
        
        total_added = 0
        processed = 0
        errors = 0
        
        start_time = time.time()
        
        for i, food in enumerate(foods):
            try:
                result = process_food_auto(
                    food, generate_fn, 
                    dry_run=args.dry_run, 
                    verbose=not args.quiet
                )
                total_added += result
                processed += 1
                
                # Progress update every 50 foods
                if (i + 1) % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    eta = (len(foods) - i - 1) / rate if rate > 0 else 0
                    print(f"\n--- Progress: {i + 1}/{len(foods)} ({(i+1)*100/len(foods):.1f}%) | "
                          f"Aliases added: {total_added} | "
                          f"ETA: {eta/60:.1f}min ---\n")
                
                # Rate limiting
                if args.delay > 0 and i < len(foods) - 1:
                    time.sleep(args.delay)
                    
            except KeyboardInterrupt:
                print("\n\nInterrupted by user.")
                break
            except Exception as e:
                print(f"  Error processing {food['name']}: {e}")
                errors += 1
                if errors > 10:
                    print("Too many errors, stopping.")
                    break
        
        elapsed = time.time() - start_time
        print()
        print("=" * 60)
        print(f"Done! Processed {processed} foods in {elapsed:.1f}s")
        print(f"Aliases added: {total_added}")
        if errors:
            print(f"Errors: {errors}")
        print("=" * 60)
        
    else:
        # Interactive mode
        print("Press Enter to start, or 'q' to quit.")
        if input().strip().lower() == "q":
            return

        total_added = 0
        processed = 0
        batch_size = 10

        for i, food in enumerate(foods):
            result = process_food_interactive(food, generate_fn, dry_run=args.dry_run)

            if result == -1:
                break

            total_added += result
            processed += 1

            if (i + 1) % batch_size == 0 and i + 1 < len(foods):
                print(f"\n--- Batch complete ({i + 1}/{len(foods)}) ---")
                print(f"Total aliases added: {total_added}")
                print("Continue? [Enter] yes, [q] quit")
                if input().strip().lower() == "q":
                    break

        print()
        print("=" * 60)
        print(f"Done! Processed {processed} foods, added {total_added} aliases.")
        print("=" * 60)


if __name__ == "__main__":
    main()
