"""
Course import script from JSON.

Imports courses from JSON file (e.g., exported from Zanfia).
Supports dry-run mode for validation without database changes.

Usage:
    uv run python app/scripts/import_courses.py --file import_courses.json
    uv run python app/scripts/import_courses.py --file import_courses.json --dry-run
    uv run python app/scripts/import_courses.py --file import_courses.json --skip-attachments
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session

from app.courses.models import Course, Lesson, Module
from app.db.session import get_db


class CourseImporter:
    """Handles course import from JSON."""

    def __init__(self, db: Session, dry_run: bool = False, skip_attachments: bool = False):
        self.db = db
        self.dry_run = dry_run
        self.skip_attachments = skip_attachments
        self.stats = {
            "courses_created": 0,
            "courses_skipped": 0,
            "modules_created": 0,
            "lessons_created": 0,
            "attachments_created": 0,
            "errors": [],
        }

    def import_courses(self, data: dict[str, Any]) -> None:
        """Import all courses from JSON data."""
        courses = data.get("courses", [])

        if not courses:
            print("⚠️  No courses found in JSON file")
            return

        print(f"📚 Found {len(courses)} course(s) to import")
        print()

        for course_data in courses:
            try:
                self._import_course(course_data)
            except Exception as e:
                error_msg = f"Failed to import course '{course_data.get('slug', 'unknown')}': {e}"
                self.stats["errors"].append(error_msg)
                print(f"❌ {error_msg}")

        if not self.dry_run:
            self.db.commit()

    def _import_course(self, course_data: dict[str, Any]) -> None:
        """Import a single course with its modules and lessons."""
        slug = course_data.get("slug")

        if not slug:
            raise ValueError("Course slug is required")

        existing = self.db.query(Course).filter(Course.slug == slug).first()

        if existing:
            print(f"⏭️  Skipping existing course: {slug}")
            self.stats["courses_skipped"] += 1
            return

        print(f"📖 Importing course: {slug}")

        if self.dry_run:
            print(f"   [DRY RUN] Would create course: {course_data.get('title')}")
            self.stats["courses_created"] += 1

            modules_data = course_data.get("modules", [])
            for module_data in modules_data:
                self._import_module(None, module_data)
        else:
            course = Course(
                slug=slug,
                title=course_data.get("title"),
                description=course_data.get("description"),
                difficulty=course_data.get("difficulty", "beginner"),
                estimated_hours=course_data.get("estimated_hours", 0),
                is_published=course_data.get("is_published", False),
                is_featured=course_data.get("is_featured", False),
                category=course_data.get("category"),
                thumbnail_url=course_data.get("thumbnail_url"),
                sort_order=course_data.get("sort_order", 0),
            )
            self.db.add(course)
            self.db.flush()
            self.stats["courses_created"] += 1
            print(f"   ✅ Created course: {course.title}")

            modules_data = course_data.get("modules", [])
            for module_data in modules_data:
                self._import_module(course.id, module_data)

    def _import_module(self, course_id: str, module_data: dict[str, Any]) -> None:
        """Import a module with its lessons."""
        if self.dry_run:
            print(f"   [DRY RUN] Would create module: {module_data.get('title')}")
            self.stats["modules_created"] += 1

            lessons_data = module_data.get("lessons", [])
            for lesson_data in lessons_data:
                print(f"      [DRY RUN] Would create lesson: {lesson_data.get('title')}")
                self.stats["lessons_created"] += 1

                if not self.skip_attachments:
                    attachments_data = lesson_data.get("attachments", [])
                    for attachment_data in attachments_data:
                        print(
                            f"         [DRY RUN] Would create attachment: {attachment_data.get('title')}"
                        )
                        self.stats["attachments_created"] += 1
        else:
            module = Module(
                course_id=course_id,
                title=module_data.get("title"),
                description=module_data.get("description"),
                sort_order=module_data.get("sort_order", 0),
            )
            self.db.add(module)
            self.db.flush()
            self.stats["modules_created"] += 1
            print(f"      ✅ Created module: {module.title}")

            lessons_data = module_data.get("lessons", [])
            for lesson_data in lessons_data:
                self._import_lesson(module.id, lesson_data)

    def _import_lesson(self, module_id: str, lesson_data: dict[str, Any]) -> None:
        """Import a lesson with its attachments."""
        lesson = Lesson(
            module_id=module_id,
            title=lesson_data.get("title"),
            description=lesson_data.get("description"),
            mux_playback_id=lesson_data.get("mux_playback_id"),
            mux_asset_id=lesson_data.get("mux_asset_id"),
            duration_seconds=lesson_data.get("duration_seconds", 0),
            is_preview=lesson_data.get("is_preview", False),
            sort_order=lesson_data.get("sort_order", 0),
        )
        self.db.add(lesson)
        self.db.flush()
        self.stats["lessons_created"] += 1

        preview_badge = " (preview)" if lesson.is_preview else ""
        print(f"         ✅ Created lesson: {lesson.title}{preview_badge}")

        if not self.skip_attachments:
            attachments_data = lesson_data.get("attachments", [])
            for attachment_data in attachments_data:
                self._import_attachment(lesson.id, attachment_data)

    def _import_attachment(self, lesson_id: str, attachment_data: dict[str, Any]) -> None:
        """Import an attachment (placeholder - actual file upload not implemented)."""
        file_path = attachment_data.get("file_path")
        title = attachment_data.get("title")

        print(f"            ⚠️  Attachment '{title}' - file upload not implemented")
        print(f"               Expected file: {file_path}")


    def print_summary(self) -> None:
        """Print import summary."""
        print()
        print("=" * 60)

        if self.dry_run:
            print("🔍 DRY RUN SUMMARY")
        else:
            print("🎉 IMPORT SUMMARY")

        print("=" * 60)
        print(f"   Courses created:  {self.stats['courses_created']}")
        print(f"   Courses skipped:  {self.stats['courses_skipped']}")
        print(f"   Modules created:  {self.stats['modules_created']}")
        print(f"   Lessons created:  {self.stats['lessons_created']}")
        print(f"   Attachments:      {self.stats['attachments_created']}")

        if self.stats["errors"]:
            print()
            print(f"   ❌ Errors: {len(self.stats['errors'])}")
            for error in self.stats["errors"]:
                print(f"      - {error}")

        print("=" * 60)

        if self.dry_run:
            print("ℹ️  This was a dry run. No changes were made to the database.")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Import courses from JSON file")
    parser.add_argument(
        "--file",
        type=str,
        default="app/scripts/import_courses.json",
        help="Path to JSON file (default: app/scripts/import_courses.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate JSON without making database changes",
    )
    parser.add_argument(
        "--skip-attachments",
        action="store_true",
        help="Skip attachment processing",
    )

    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)

    print("=" * 60)
    print("📥 Course Import Script")
    print("=" * 60)
    print(f"   File: {file_path}")
    print(f"   Dry run: {args.dry_run}")
    print(f"   Skip attachments: {args.skip_attachments}")
    print("=" * 60)
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

    db = next(get_db())
    try:
        importer = CourseImporter(
            db=db,
            dry_run=args.dry_run,
            skip_attachments=args.skip_attachments,
        )
        importer.import_courses(data)
        importer.print_summary()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
