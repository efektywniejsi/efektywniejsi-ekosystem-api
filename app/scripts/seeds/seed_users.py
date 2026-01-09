"""
Seed script to create initial admin user.

Usage:
    uv run python -m app.scripts.seeds.seed_users
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.auth.models.user import User
from app.core.security import get_password_hash
from app.db.session import SessionLocal


def seed_admin_user() -> None:
    """Create initial admin user if it doesn't exist"""
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin_email = "admin@efektywniejsi.pl"
        existing_admin = db.query(User).filter(User.email == admin_email).first()

        if existing_admin:
            print(f"✓ Admin user already exists: {admin_email}")
            return

        # Create admin user
        admin_user = User(
            email=admin_email,
            name="Admin",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("✓ Admin user created successfully!")
        print(f"  Email: {admin_email}")
        print("  Password: admin123")
        print("  Role: admin")
        print("\n⚠️  IMPORTANT: Change the password after first login!")
    except Exception as e:
        print(f"✗ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


def seed_test_users() -> None:
    """Create test users for development"""
    db = SessionLocal()
    try:
        test_users = [
            {
                "email": "user@test.pl",
                "name": "Jan Kowalski",
                "password": "testuser123",
                "role": "paid",
            },
            {
                "email": "user2@test.pl",
                "name": "Anna Nowak",
                "password": "testuser123",
                "role": "paid",
            },
        ]

        for user_data in test_users:
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if existing_user:
                print(f"  User already exists: {user_data['email']}")
                continue

            user = User(
                email=user_data["email"],
                name=user_data["name"],
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"],
                is_active=True,
            )
            db.add(user)
            db.commit()
            print(f"✓ Test user created: {user_data['email']} (password: {user_data['password']})")
    except Exception as e:
        print(f"✗ Error creating test users: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("Seeding database with initial users...")
    print("=" * 80)

    seed_admin_user()
    print()
    seed_test_users()

    print("=" * 80)
    print("Seeding complete!")
    print("=" * 80)
