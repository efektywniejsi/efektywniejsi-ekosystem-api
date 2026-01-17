"""
Update Mux IDs from placeholder to real IDs.

Reads mapping from JSON file and updates lessons in database.

Usage:
    uv run python app/scripts/update_mux_ids.py --mapping mux_id_mapping.json --dry-run
    uv run python app/scripts/update_mux_ids.py --mapping mux_id_mapping.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session

from app.courses.models import Lesson
from app.db.session import get_db


class MuxIdUpdater:
    """Handles Mux ID updates from mapping file."""

    def __init__(self, db: Session, dry_run: bool = False):
        self.db = db
        self.dry_run = dry_run
        self.stats = {
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

    def update_from_mapping(self, mappings: list[dict[str, Any]]) -> None:
        """Update lessons based on mapping data."""
        if not mappings:
            print("⚠️  No mappings found in file")
            return

        print(f"📥 Loaded {len(mappings)} mapping(s)")
        print()

        for mapping in mappings:
            try:
                self._update_lesson(mapping)
            except Exception as e:
                error_msg = f"Failed to update {mapping.get('placeholder', 'unknown')}: {e}"
                self.stats["errors"].append(error_msg)
                print(f"❌ {error_msg}")

        if not self.dry_run:
            self.db.commit()

    def _update_lesson(self, mapping: dict[str, Any]) -> None:
        """Update a single lesson's Mux IDs."""
        placeholder = mapping.get("placeholder")
        new_playback_id = mapping.get("mux_playback_id")
        new_asset_id = mapping.get("mux_asset_id")
        new_duration = mapping.get("duration_seconds")

        if not placeholder:
            raise ValueError("Missing 'placeholder' in mapping")

        if not new_playback_id:
            raise ValueError(f"Missing 'mux_playback_id' for {placeholder}")

        lesson = self.db.query(Lesson).filter(Lesson.mux_playback_id == placeholder).first()

        if not lesson:
            print(f"⏭️  No lesson found with placeholder: {placeholder}")
            self.stats["skipped"] += 1
            return

        if self.dry_run:
            print(f"[DRY RUN] Would update lesson: {lesson.title}")
            print(f"   Old Mux ID: {placeholder}")
            print(f"   New Mux ID: {new_playback_id}")
            if new_asset_id:
                print(f"   Asset ID:   {new_asset_id}")
            if new_duration and new_duration != lesson.duration_seconds:
                print(f"   Duration:   {lesson.duration_seconds}s → {new_duration}s")
            print()
            self.stats["updated"] += 1
        else:
            lesson.mux_playback_id = new_playback_id

            if new_asset_id:
                lesson.mux_asset_id = new_asset_id

            if new_duration and new_duration != lesson.duration_seconds:
                lesson.duration_seconds = new_duration

            self.db.flush()

            print(f"✅ Updated lesson: {lesson.title}")
            print(f"   Mux ID: {new_playback_id}")
            if new_asset_id:
                print(f"   Asset:  {new_asset_id}")
            print()

            self.stats["updated"] += 1

    def print_summary(self) -> None:
        """Print update summary."""
        print()
        print("=" * 60)

        if self.dry_run:
            print("🔍 DRY RUN SUMMARY")
        else:
            print("🎉 UPDATE SUMMARY")

        print("=" * 60)
        print(f"   Lessons updated: {self.stats['updated']}")
        print(f"   Lessons skipped: {self.stats['skipped']}")

        if self.stats["errors"]:
            print(f"   ❌ Errors: {len(self.stats['errors'])}")
            for error in self.stats["errors"]:
                print(f"      - {error}")

        print("=" * 60)

        if self.dry_run:
            print("ℹ️  This was a dry run. No changes were made to the database.")
        else:
            print("✅ All changes have been committed to the database.")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update Mux IDs from placeholder to real IDs")
    parser.add_argument(
        "--mapping",
        type=str,
        default="app/scripts/mux_id_mapping.json",
        help="Path to mapping JSON file (default: app/scripts/mux_id_mapping.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate mappings without making database changes",
    )

    args = parser.parse_args()

    file_path = Path(args.mapping)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    if not file_path.exists():
        print(f"❌ Error: Mapping file not found: {file_path}")
        sys.exit(1)

    print("=" * 60)
    print("🎬 Mux ID Update Script")
    print("=" * 60)
    print(f"   File: {file_path}")
    print(f"   Dry run: {args.dry_run}")
    print("=" * 60)
    print()

    if args.dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
        print()

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        sys.exit(1)

    mappings = data.get("mappings", [])

    db = next(get_db())
    try:
        updater = MuxIdUpdater(db=db, dry_run=args.dry_run)
        updater.update_from_mapping(mappings)
        updater.print_summary()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
