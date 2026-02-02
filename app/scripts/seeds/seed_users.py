import os
import secrets
import string
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.auth.models.user import User
from app.core.security import get_password_hash
from app.db.session import SessionLocal


def generate_secure_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def seed_admin_user() -> None:
    db = SessionLocal()
    try:
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@efektywniejsi.pl")
        admin_password = os.environ.get("ADMIN_PASSWORD") or generate_secure_password()
        admin_name = os.environ.get("ADMIN_NAME", "Admin")

        existing_admin = db.query(User).filter(User.email == admin_email).first()

        if existing_admin:
            print(f"✓ Admin user already exists: {admin_email}")
            return

        admin_user = User(
            email=admin_email,
            name=admin_name,
            hashed_password=get_password_hash(admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("✓ Admin user created successfully!")
        print(f"  Email:    {admin_email}")
        print(f"  Password: {admin_password}")
        print()
        print("  ╔══════════════════════════════════════════════════╗")
        print("  ║  SAVE THIS PASSWORD NOW — it won't be shown     ║")
        print("  ║  again. Change it after first login.             ║")
        print("  ╚══════════════════════════════════════════════════╝")
    except Exception as e:
        print(f"✗ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


def seed_test_users() -> None:
    db = SessionLocal()
    try:
        test_users = [
            {
                "email": os.environ.get("TEST_USER1_EMAIL", "user@test.pl"),
                "name": "Jan Kowalski",
                "password": os.environ.get("TEST_USER1_PASSWORD") or generate_secure_password(),
                "role": "paid",
            },
            {
                "email": os.environ.get("TEST_USER2_EMAIL", "user2@test.pl"),
                "name": "Anna Nowak",
                "password": os.environ.get("TEST_USER2_PASSWORD") or generate_secure_password(),
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
            print(f"✓ Test user created: {user_data['email']}")
            print(f"  Password: {user_data['password']}")
    except Exception as e:
        print(f"✗ Error creating test users: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("Seeding database with initial users...")
    print()
    print("  Tip: Set env vars to control credentials:")
    print("    ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_NAME")
    print("    TEST_USER1_EMAIL, TEST_USER1_PASSWORD")
    print("    TEST_USER2_EMAIL, TEST_USER2_PASSWORD")
    print("  If not set, secure random passwords will be generated.")
    print("=" * 80)

    seed_admin_user()
    print()
    seed_test_users()

    print("=" * 80)
    print("Seeding complete!")
    print("=" * 80)
