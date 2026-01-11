"""
Verification script for imported courses.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.courses.models import Course, Lesson, Module
from app.db.session import get_db


def main():
    db = next(get_db())
    try:
        # Get all courses except demo
        courses = (
            db.query(Course)
            .filter(Course.slug != "demo-getting-started")
            .order_by(Course.slug)
            .all()
        )

        if not courses:
            print("❌ No imported courses found")
            return

        print("✅ Imported Courses Verification:")
        print("=" * 60)

        for course in courses:
            modules = (
                db.query(Module)
                .filter(Module.course_id == course.id)
                .order_by(Module.sort_order)
                .all()
            )
            total_lessons = (
                db.query(Lesson).join(Module).filter(Module.course_id == course.id).count()
            )
            preview_lessons = (
                db.query(Lesson)
                .join(Module)
                .filter(Module.course_id == course.id, Lesson.is_preview is True)
                .count()
            )

            print()
            print(f"📖 {course.title}")
            print(f"   Slug: {course.slug}")
            print(f"   Difficulty: {course.difficulty}")
            print(f"   Published: {course.is_published}")
            print(f"   Featured: {course.is_featured}")
            print(f"   Category: {course.category}")
            print(f"   Estimated hours: {course.estimated_hours}")
            print(f"   Modules: {len(modules)}")
            print(f"   Lessons: {total_lessons} ({preview_lessons} preview)")
            print()

            for module in modules:
                module_lessons = (
                    db.query(Lesson)
                    .filter(Lesson.module_id == module.id)
                    .order_by(Lesson.sort_order)
                    .all()
                )
                print(f"   📚 {module.title} ({len(module_lessons)} lessons)")
                for lesson in module_lessons:
                    preview = " [PREVIEW]" if lesson.is_preview else ""
                    duration_min = lesson.duration_seconds // 60
                    mux_id = (
                        lesson.mux_playback_id[:20] + "..."
                        if len(lesson.mux_playback_id) > 20
                        else lesson.mux_playback_id
                    )
                    print(f"      - {lesson.title}{preview}")
                    print(f"        Duration: {duration_min}m | Mux ID: {mux_id}")

        print()
        print("=" * 60)
        print(f"Total imported courses: {len(courses)}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
