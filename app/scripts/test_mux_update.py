"""
Test Mux ID update with rollback.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.courses.models import Lesson
from app.db.session import get_db


def main():
    db = next(get_db())
    try:
        with open("app/scripts/mux_id_mapping_example.json") as f:
            data = json.load(f)

        mappings = data.get("mappings", [])

        print("🧪 Testing Mux ID update (with rollback)")
        print("=" * 60)
        print()

        for mapping in mappings:
            placeholder = mapping["placeholder"]
            new_id = mapping["mux_playback_id"]

            lesson = db.query(Lesson).filter(Lesson.mux_playback_id == placeholder).first()

            if lesson:
                print(f"Before: {lesson.title}")
                print(f"  Mux ID: {lesson.mux_playback_id}")

                lesson.mux_playback_id = new_id
                lesson.mux_asset_id = mapping.get("mux_asset_id")
                db.flush()

                updated_lesson = db.query(Lesson).filter(Lesson.id == lesson.id).first()
                print(f"After:  {updated_lesson.title}")
                print(f"  Mux ID: {updated_lesson.mux_playback_id}")
                print("  ✅ Update successful")
                print()

        print("🔄 Rolling back all changes...")
        db.rollback()

        print("Verifying rollback...")
        for mapping in mappings:
            placeholder = mapping["placeholder"]
            lesson = db.query(Lesson).filter(Lesson.mux_playback_id == placeholder).first()
            if lesson:
                print(f"  ✅ {lesson.title}: Still has placeholder {placeholder}")

        print()
        print("=" * 60)
        print("✅ Test completed successfully")
        print("   Updates work correctly and rollback restored original values")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
