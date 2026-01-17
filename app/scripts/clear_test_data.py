"""Clear test data (enrollments, progress, gamification) for development/testing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.auth.models.user import User
from app.courses.models import (
    Enrollment,
    LessonProgress,
    PointsHistory,
    UserAchievement,
    UserPoints,
    UserStreak,
)
from app.db.session import get_db


def clear_test_data(user_email: str = "user@test.pl", dry_run: bool = False) -> None:
    """Clear all test data for specified user."""
    db = next(get_db())

    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            print(f"❌ User {user_email} not found.")
            return

        print(f"{'[DRY RUN] ' if dry_run else ''}Clearing test data for {user.email}...")
        print()

        enrollments = db.query(Enrollment).filter(Enrollment.user_id == user.id).all()
        print(f"   Enrollments: {len(enrollments)}")

        progress = db.query(LessonProgress).filter(LessonProgress.user_id == user.id).all()
        print(f"   Lesson progress: {len(progress)}")

        points_history = db.query(PointsHistory).filter(PointsHistory.user_id == user.id).all()
        print(f"   Points history: {len(points_history)}")

        achievements = db.query(UserAchievement).filter(UserAchievement.user_id == user.id).all()
        print(f"   Achievements: {len(achievements)}")

        user_points = db.query(UserPoints).filter(UserPoints.user_id == user.id).first()
        print(f"   User points: {'1' if user_points else '0'}")

        user_streak = db.query(UserStreak).filter(UserStreak.user_id == user.id).first()
        print(f"   User streak: {'1' if user_streak else '0'}")

        if not dry_run:
            for enrollment in enrollments:
                db.delete(enrollment)
            for prog in progress:
                db.delete(prog)
            for ph in points_history:
                db.delete(ph)
            for ach in achievements:
                db.delete(ach)
            if user_points:
                db.delete(user_points)
            if user_streak:
                db.delete(user_streak)

            db.commit()
            print()
            print("=" * 60)
            print("✅ Test data cleared successfully!")
        else:
            print()
            print("=" * 60)
            print("🔍 Dry run completed. Use --execute to apply changes.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Clear test data")
    parser.add_argument(
        "--user", default="user@test.pl", help="User email (default: user@test.pl)"
    )
    parser.add_argument(
        "--execute", action="store_true", help="Execute changes (default: dry run)"
    )
    args = parser.parse_args()

    dry_run = not args.execute
    clear_test_data(user_email=args.user, dry_run=dry_run)


if __name__ == "__main__":
    main()
