"""
Update package catalog with the 2 packages from the screenshot.
This will DELETE all existing packages and create new ones.

Usage:
    python -m app.scripts.update_packages_catalog
"""

import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import SessionLocal

# Import all models to ensure relationships are resolved
import app.db.base  # noqa: F401
from app.packages.models.package import Package, PackageProcess


# Package data matching the screenshot
PACKAGE_DATA = [
    {
        "id": "office-autopilot",
        "title": "Obsługa biurowa na autopilocie",
        "slug": "obsluga-biurowa-autopilot",
        "description": "Automatyczne zarządzanie kalendarzem i skrzynką pocztową",
        "category": "Operacje",
        "price": 99,  # Will be converted to 9900 grosz
        "originalPrice": None,
        "processes": [
            {
                "name": "Automatyzacja emaili",
                "description": "Automatyczne zarządzanie skrzynką pocztową Gmail",
            },
            {
                "name": "Zarządzanie kalendarzem",
                "description": "Automatyczne zarządzanie Google Calendar",
            },
            {
                "name": "Integracja Slack",
                "description": "Powiadomienia i zarządzanie przez Slack",
            },
        ],
        "tools": ["Gmail", "Google Calendar", "Slack", "n8n"],
        "difficulty": "intermediate",
        "totalTimeSaved": "10h/tydzień",
        "videoUrl": "https://www.youtube.com/embed/dQw4w9WgXcQ",  # Example YouTube embed URL
        "isPublished": True,
        "isFeatured": True,
    },
    {
        "id": "chatbot-rag",
        "title": "Chatbot AI (RAG) - obsługa klienta",
        "slug": "chatbot-rag-obsluga-klienta",
        "description": "Odpowiada na pytania klienta i udziela supportu 24/7",
        "category": "Obsługa klienta",
        "price": 159,  # Will be converted to 15900 grosz
        "originalPrice": None,
        "processes": [
            {
                "name": "Integracja WhatsApp",
                "description": "Chatbot dostępny przez WhatsApp",
            },
            {
                "name": "Integracja Messenger",
                "description": "Chatbot dostępny przez Facebook Messenger",
            },
            {
                "name": "Widget na stronę",
                "description": "Widget chatbota do osadzenia na stronie WWW",
            },
            {
                "name": "Silnik RAG",
                "description": "Retrieval Augmented Generation z własną bazą wiedzy",
            },
        ],
        "tools": ["WhatsApp", "Messenger", "Website Widget", "Qdrant", "OpenAI"],
        "difficulty": "advanced",
        "totalTimeSaved": "24/7 dostępność",
        "videoUrl": "https://www.youtube.com/embed/dQw4w9WgXcQ",  # Example YouTube embed URL
        "isPublished": True,
        "isFeatured": True,
    },
]


def clear_existing_packages(db: Session) -> None:
    """Delete all existing packages and their related data."""
    print("Deleting all existing packages...")
    deleted_count = db.query(Package).delete()
    db.commit()
    print(f"Deleted {deleted_count} packages (cascade will remove related data)")


def create_packages(db: Session) -> None:
    """Create new packages from PACKAGE_DATA."""
    print("Creating new packages...")

    for pkg_data in PACKAGE_DATA:
        # Convert price from PLN to grosz (99 PLN → 9900 groszy)
        price_grosz = pkg_data["price"] * 100
        original_price_grosz = (
            pkg_data["originalPrice"] * 100 if pkg_data["originalPrice"] else None
        )

        # Create package
        package = Package(
            id=uuid.uuid4(),
            slug=pkg_data["slug"],
            title=pkg_data["title"],
            description=pkg_data["description"],
            category=pkg_data["category"],
            price=price_grosz,
            original_price=original_price_grosz,
            currency="PLN",
            difficulty=pkg_data["difficulty"],
            total_time_saved=pkg_data["totalTimeSaved"],
            tools=json.dumps(pkg_data["tools"]),  # Store as JSON string
            video_url=pkg_data.get("videoUrl"),
            is_published=pkg_data["isPublished"],
            is_featured=pkg_data["isFeatured"],
            is_bundle=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(package)
        db.flush()  # Flush to get package.id

        # Create package processes
        for idx, process_data in enumerate(pkg_data["processes"]):
            process = PackageProcess(
                id=uuid.uuid4(),
                package_id=package.id,
                name=process_data["name"],
                description=process_data["description"],
                sort_order=idx,
            )
            db.add(process)

        print(
            f"✓ Created package: {pkg_data['title']} ({pkg_data['price']} PLN) with {len(pkg_data['processes'])} processes"
        )

    db.commit()
    print("\n✅ Package catalog updated successfully!")
    print(f"Total packages: {len(PACKAGE_DATA)}")


def main() -> None:
    """Main function to run the catalog update."""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("UPDATING PACKAGE CATALOG")
        print("=" * 60)
        print()

        # Step 1: Clear existing packages
        clear_existing_packages(db)
        print()

        # Step 2: Create new packages
        create_packages(db)
        print()

        print("=" * 60)
        print("CATALOG UPDATE COMPLETE")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during catalog update: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
