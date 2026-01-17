"""Seed test enrollments for development/testing."""

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.auth.models.user import User
from app.courses.models import Course, Enrollment, UserPoints, UserStreak
from app.db.session import get_db


def seed_test_enrollments(dry_run: bool = False) -> None:
    """Create test enrollments for user@test.pl."""
    db = next(get_db())

    try:
        user = db.query(User).filter(User.email == "user@test.pl").first()
        if not user:
            print("❌ User user@test.pl not found. Run seed_users.py first.")
            return

        demo_course = db.query(Course).filter(Course.slug == "demo-getting-started").first()
        masterclass = db.query(Course).filter(Course.slug == "masterclass-lowcode").first()

        if not demo_course or not masterclass:
            print("❌ Courses not found. Run seed_demo_course.py first.")
            return

        print(f"{'[DRY RUN] ' if dry_run else ''}Seeding test enrollments for {user.email}...")
        print()

        enrollments_created = 0
        enrollments_skipped = 0

        courses_to_enroll = [demo_course, masterclass]

        for course in courses_to_enroll:
            existing = (
                db.query(Enrollment)
                .filter(Enrollment.user_id == user.id, Enrollment.course_id == course.id)
                .first()
            )

            if existing:
                print(f"   ⏭️  Enrollment already exists: {course.title}")
                enrollments_skipped += 1
            else:
                if not dry_run:
                    enrollment = Enrollment(
                        user_id=user.id, course_id=course.id, enrolled_at=datetime.now()
                    )
                    db.add(enrollment)
                print(f"   ✅ Created enrollment: {course.title}")
                enrollments_created += 1

        user_points = db.query(UserPoints).filter(UserPoints.user_id == user.id).first()
        if not user_points:
            if not dry_run:
                user_points = UserPoints(user_id=user.id, total_points=0, level=1)
                db.add(user_points)
            print("   ✅ Created UserPoints (0 points, level 1)")
        else:
            print("   ⏭️  UserPoints already exists")

        user_streak = db.query(UserStreak).filter(UserStreak.user_id == user.id).first()
        if not user_streak:
            if not dry_run:
                user_streak = UserStreak(
                    user_id=user.id,
                    current_streak=0,
                    longest_streak=0,
                    last_activity_date=date.today(),
                )
                db.add(user_streak)
            print("   ✅ Created UserStreak (0 days)")
        else:
            print("   ⏭️  UserStreak already exists")

        if not dry_run:
            db.commit()
            print()
            print("=" * 60)
            print("✅ Test enrollments seeded successfully!")
        else:
            print()
            print("=" * 60)
            print("🔍 Dry run completed. Use --execute to apply changes.")

        print()
        print(f"Enrollments created: {enrollments_created}")
        print(f"Enrollments skipped: {enrollments_skipped}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed test enrollments")
    parser.add_argument("--execute", action="store_true", help="Execute changes (default: dry run)")
    args = parser.parse_args()

    dry_run = not args.execute
    seed_test_enrollments(dry_run=dry_run)


if __name__ == "__main__":
    main()
