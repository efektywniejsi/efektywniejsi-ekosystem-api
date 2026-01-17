"""
List all lessons with placeholder Mux IDs.

Helps identify which lessons need real Mux IDs.

Usage:
    uv run python app/scripts/list_placeholder_lessons.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.courses.models import Course, Lesson, Module
from app.db.session import get_db


def main():
    db = next(get_db())
    try:
        lessons = (
            db.query(Lesson)
            .filter(
                Lesson.mux_playback_id.like("PLACEHOLDER%")
                | Lesson.mux_playback_id.like("TO_BE_REPLACED%")
            )
            .join(Module)
            .join(Course)
            .order_by(Course.slug, Module.sort_order, Lesson.sort_order)
            .all()
        )

        if not lessons:
            print("✅ No lessons with placeholder Mux IDs found")
            print("   All lessons have real Mux playback IDs.")
            return

        print("Lessons with placeholder Mux IDs:")
        print("=" * 60)
        print()

        for idx, lesson in enumerate(lessons, 1):
            module = db.query(Module).filter(Module.id == lesson.module_id).first()
            course = db.query(Course).filter(Course.id == module.course_id).first()

            duration_min = lesson.duration_seconds // 60
            duration_sec = lesson.duration_seconds % 60

            print(f"[{idx}] {lesson.mux_playback_id}")
            print(f"    Lekcja: {lesson.title}")
            print(f"    Moduł:  {module.title}")
            print(f"    Kurs:   {course.title} ({course.slug})")
            print(f"    Duration: {lesson.duration_seconds}s ({duration_min}m {duration_sec}s)")
            print(f"    Preview: {'Yes' if lesson.is_preview else 'No'}")
            print()

        print("=" * 60)
        print(f"Total: {len(lessons)} lessons need Mux IDs")
        print()
        print("💡 Next steps:")
        print("   1. Upload videos to Mux (see docs/mux-integration-guide.md)")
        print("   2. Create mux_id_mapping.json with real Mux IDs")
        print("   3. Run: uv run python app/scripts/update_mux_ids.py")

    finally:
        db.close()


if __name__ == "__main__":
    main()
