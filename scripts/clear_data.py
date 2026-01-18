#!/usr/bin/env python3
"""Clear all health data from the database (keeps custom metric definitions)."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models import (
    WeightEntry, SleepEntry, WakeTimeEntry, WorkoutEntry,
    CalorieEntry, CustomMetricEntry, MealPreset
)


def clear_data(include_presets: bool = False):
    """Clear all health data entries.
    
    Args:
        include_presets: If True, also delete meal presets
    """
    app = create_app()
    
    with app.app_context():
        print("Clearing health data...")
        
        # Delete all entries
        count = CalorieEntry.query.delete()
        print(f"  Deleted {count} calorie entries")
        
        count = WeightEntry.query.delete()
        print(f"  Deleted {count} weight entries")
        
        count = SleepEntry.query.delete()
        print(f"  Deleted {count} sleep entries")
        
        count = WakeTimeEntry.query.delete()
        print(f"  Deleted {count} wake time entries")
        
        count = WorkoutEntry.query.delete()
        print(f"  Deleted {count} workout entries")
        
        count = CustomMetricEntry.query.delete()
        print(f"  Deleted {count} custom metric entries")
        
        if include_presets:
            count = MealPreset.query.delete()
            print(f"  Deleted {count} meal presets")
        
        db.session.commit()
        print("\nDone! All data cleared.")
        print("Note: Custom metric definitions are preserved.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clear health data from database")
    parser.add_argument(
        "--include-presets",
        action="store_true",
        help="Also delete meal presets"
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    if not args.yes:
        response = input("This will delete ALL health data. Continue? [y/N] ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
    clear_data(include_presets=args.include_presets)
