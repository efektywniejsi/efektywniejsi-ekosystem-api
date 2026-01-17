"""
Seed script for demo course.

Creates a demo course "Getting Started" with sample modules and lessons.
Can be run multiple times - skips existing course.

Usage:
    uv run python app/scripts/seed_demo_course.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session

from app.courses.models import Course, Lesson, Module
from app.db.session import get_db


def seed_demo_course(db: Session) -> None:
    """Seed demo course into the database."""

    existing_course = db.query(Course).filter(Course.slug == "demo-getting-started").first()

    if existing_course:
        print("⏭️  Demo course already exists. Skipping.")
        return

    print("📚 Creating demo course...")

    demo_course = Course(
        slug="demo-getting-started",
        title="Demo Course - Getting Started",
        description="Poznaj podstawy platformy Efektywniejsi. Ten kurs wprowadzi Cię w korzystanie z systemu nauki, postępów i gamifikacji.",
        difficulty="beginner",
        estimated_hours=2,
        is_published=True,
        is_featured=True,
        category="tutorial",
        sort_order=0,
    )
    db.add(demo_course)
    db.flush()
    print(f"✅ Created course: {demo_course.title} (slug: {demo_course.slug})")

    module_1 = Module(
        course_id=demo_course.id,
        title="Moduł 1: Podstawy platformy",
        description="Wprowadzenie do podstawowych funkcji platformy",
        sort_order=1,
    )
    db.add(module_1)
    db.flush()
    print(f"✅ Created module: {module_1.title}")

    lesson_1_1 = Lesson(
        module_id=module_1.id,
        title="Witamy na platformie",
        description="Poznaj podstawy działania platformy Efektywniejsi",
        mux_playback_id="PLACEHOLDER_MUX_ID_001",
        mux_asset_id="PLACEHOLDER_ASSET_ID_001",
        duration_seconds=180,
        is_preview=True,
        sort_order=1,
    )
    db.add(lesson_1_1)
    print(f"✅ Created lesson: {lesson_1_1.title} (preview)")

    lesson_1_2 = Lesson(
        module_id=module_1.id,
        title="Nawigacja po interfejsie",
        description="Jak poruszać się po platformie i znajdować potrzebne funkcje",
        mux_playback_id="PLACEHOLDER_MUX_ID_002",
        mux_asset_id="PLACEHOLDER_ASSET_ID_002",
        duration_seconds=240,
        is_preview=False,
        sort_order=2,
    )
    db.add(lesson_1_2)
    print(f"✅ Created lesson: {lesson_1_2.title}")

    module_2 = Module(
        course_id=demo_course.id,
        title="Moduł 2: System postępów",
        description="Jak śledzić swoje postępy i wykorzystywać gamifikację",
        sort_order=2,
    )
    db.add(module_2)
    db.flush()
    print(f"✅ Created module: {module_2.title}")

    lesson_2_1 = Lesson(
        module_id=module_2.id,
        title="Śledzenie postępów w nauce",
        description="Dowiedz się jak monitorować swoje postępy w kursach",
        mux_playback_id="PLACEHOLDER_MUX_ID_003",
        mux_asset_id="PLACEHOLDER_ASSET_ID_003",
        duration_seconds=300,
        is_preview=False,
        sort_order=1,
    )
    db.add(lesson_2_1)
    print(f"✅ Created lesson: {lesson_2_1.title}")

    lesson_2_2 = Lesson(
        module_id=module_2.id,
        title="System punktów i osiągnięć",
        description="Zdobywaj punkty, odblokowuj osiągnięcia i buduj swoje streaki",
        mux_playback_id="PLACEHOLDER_MUX_ID_004",
        mux_asset_id="PLACEHOLDER_ASSET_ID_004",
        duration_seconds=360,
        is_preview=False,
        sort_order=2,
    )
    db.add(lesson_2_2)
    print(f"✅ Created lesson: {lesson_2_2.title}")

    lesson_2_3 = Lesson(
        module_id=module_2.id,
        title="Zdobywanie certyfikatów",
        description="Jak ukończyć kurs i wygenerować swój certyfikat",
        mux_playback_id="PLACEHOLDER_MUX_ID_005",
        mux_asset_id="PLACEHOLDER_ASSET_ID_005",
        duration_seconds=240,
        is_preview=False,
        sort_order=3,
    )
    db.add(lesson_2_3)
    print(f"✅ Created lesson: {lesson_2_3.title}")

    db.commit()

    print("\n" + "=" * 60)
    print("🎉 Demo course seeding complete!")
    print(f"   Course: {demo_course.title}")
    print("   Modules: 2")
    print("   Lessons: 5 (1 preview)")
    print("   Total duration: ~22 minutes")
    print("=" * 60)


def main() -> None:
    """Main entry point."""
    print("=" * 60)
    print("🌱 Demo Course Seeding Script")
    print("=" * 60)
    print()

    db = next(get_db())
    try:
        seed_demo_course(db)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
