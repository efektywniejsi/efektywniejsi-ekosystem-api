"""
Seed script for achievements.

Creates all achievement records in the database.
Can be run multiple times - skips existing achievements.

Usage:
    uv run python app/scripts/seed_achievements.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session

from app.courses.models import Achievement
from app.db.session import get_db


def seed_achievements(db: Session) -> None:
    """Seed achievements into the database."""

    # Streak Achievements (Priority 1)
    streak_achievements = [
        {
            "code": "streak_3_days",
            "title": "Pierwsze kroki",
            "description": "3 dni nauki z rzędu",
            "icon": "flame",
            "points_reward": 50,
            "category": "streak",
            "is_active": True,
        },
        {
            "code": "streak_7_days",
            "title": "Tydzień mocy",
            "description": "7 dni konsekwentnej nauki",
            "icon": "flame",
            "points_reward": 100,
            "category": "streak",
            "is_active": True,
        },
        {
            "code": "streak_14_days",
            "title": "Dwutygodniowy maraton",
            "description": "14 dni bez przerwy",
            "icon": "flame",
            "points_reward": 250,
            "category": "streak",
            "is_active": True,
        },
        {
            "code": "streak_30_days",
            "title": "Miesiąc nauki",
            "description": "30 dni konsekwentnej nauki",
            "icon": "trophy",
            "points_reward": 500,
            "category": "streak",
            "is_active": True,
        },
        {
            "code": "streak_60_days",
            "title": "Niezłomny uczeń",
            "description": "2 miesiące codziennej nauki",
            "icon": "trophy",
            "points_reward": 1000,
            "category": "streak",
            "is_active": True,
        },
        {
            "code": "streak_100_days",
            "title": "Legendarna konsystencja",
            "description": "100 dni z rzędu - jesteś legendą!",
            "icon": "star",
            "points_reward": 2000,
            "category": "streak",
            "is_active": True,
        },
    ]

    # General Achievements (Priority 2)
    general_achievements = [
        {
            "code": "first_lesson_completed",
            "title": "Pierwszy krok",
            "description": "Ukończona pierwsza lekcja",
            "icon": "zap",
            "points_reward": 10,
            "category": "general",
            "is_active": True,
        },
        {
            "code": "first_course_completed",
            "title": "Finisher",
            "description": "Ukończony pierwszy kurs",
            "icon": "award",
            "points_reward": 100,
            "category": "general",
            "is_active": True,
        },
        {
            "code": "watch_time_10_hours",
            "title": "Maratończyk",
            "description": "10 godzin materiałów wideo",
            "icon": "clock",
            "points_reward": 150,
            "category": "watch_time",
            "is_active": True,
        },
        {
            "code": "watch_time_50_hours",
            "title": "Mistrz nauki",
            "description": "50 godzin materiałów wideo",
            "icon": "clock",
            "points_reward": 500,
            "category": "watch_time",
            "is_active": True,
        },
    ]

    all_achievements = streak_achievements + general_achievements

    created_count = 0
    skipped_count = 0

    for achievement_data in all_achievements:
        # Check if achievement already exists
        existing = (
            db.query(Achievement).filter(Achievement.code == achievement_data["code"]).first()
        )

        if existing:
            print(f"⏭️  Skipping existing achievement: {achievement_data['code']}")
            skipped_count += 1
            continue

        # Create new achievement
        achievement = Achievement(**achievement_data)
        db.add(achievement)
        print(f"✅ Created achievement: {achievement_data['code']} ({achievement_data['title']})")
        created_count += 1

    db.commit()

    print("\n" + "=" * 60)
    print("🎉 Seeding complete!")
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total:   {created_count + skipped_count}")
    print("=" * 60)


def main() -> None:
    """Main entry point."""
    print("=" * 60)
    print("🌱 Achievement Seeding Script")
    print("=" * 60)
    print()

    db = next(get_db())
    try:
        seed_achievements(db)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
