"""
Quick verification script for demo course.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.courses.models import Course, Lesson, Module
from app.db.session import get_db


def main():
    db = next(get_db())
    try:
        course = db.query(Course).filter(Course.slug == "demo-getting-started").first()
        if course:
            modules = db.query(Module).filter(Module.course_id == course.id).all()
            lessons = db.query(Lesson).join(Module).filter(Module.course_id == course.id).all()
            preview_lessons = [lesson for lesson in lessons if lesson.is_preview]

            print("✅ Demo Course Verification:")
            print(f"   Title: {course.title}")
            print(f"   Slug: {course.slug}")
            print(f"   Published: {course.is_published}")
            print(f"   Featured: {course.is_featured}")
            print(f"   Difficulty: {course.difficulty}")
            print(f"   Modules: {len(modules)}")
            print(f"   Lessons: {len(lessons)} ({len(preview_lessons)} preview)")
            print()
            for module in modules:
                module_lessons = [lesson for lesson in lessons if lesson.module_id == module.id]
                print(f"   📖 {module.title}: {len(module_lessons)} lessons")
                for lesson in module_lessons:
                    preview = " (PREVIEW)" if lesson.is_preview else ""
                    print(f"      - {lesson.title}{preview}")
        else:
            print("❌ Demo course not found")
    finally:
        db.close()


if __name__ == "__main__":
    main()
