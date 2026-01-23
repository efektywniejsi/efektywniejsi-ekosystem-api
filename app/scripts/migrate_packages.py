"""
Data migration script to import packages from mock data.

Usage:
    python -m app.scripts.migrate_packages
"""

import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import SessionLocal

# Import all models to ensure relationships are resolved
import app.db.base  # noqa: F401
from app.packages.models.package import Package, PackageProcess


# Package data from marketing app (apps/marketing/src/lib/packages-data.ts)
PACKAGE_DATA = [
    {
        "id": "priority-office",
        "title": "Pakiet wdrożeniowy: obsługa biurowa",
        "slug": "biuro-autopilot",
        "description": "Zbuduj cyfrowego asystenta przejmującego e-maile, kalendarz i faktury. Pełna integracja Google OAuth2.",
        "category": "Operacje",
        "price": 69,
        "originalPrice": 149,
        "processes": [
            {"name": "E-maile i kalendarz", "description": "Automatyzacja obsługi emaili i zarządzania kalendarzem"},
            {"name": "Faktury & OCR", "description": "Automatyczne przetwarzanie faktur z OCR"},
        ],
        "tools": ["n8n", "Google Workspace", "OAuth2", "OpenAI"],
        "difficulty": "intermediate",
        "totalTimeSaved": "10h/tydzień",
        "isPublished": True,
        "isFeatured": True,
    },
    {
        "id": "priority-chatbot",
        "title": "Pakiet wdrożeniowy: chatbot RAG",
        "slug": "chatbot-rag",
        "description": "Własny chatbot AI z bazą wiedzy Twojej firmy. Integracja Qdrant i bezpieczna instalacja na własnym serwerze.",
        "category": "Obsługa klienta",
        "price": 149,
        "originalPrice": 249,
        "processes": [
            {"name": "Silnik RAG", "description": "Silnik Retrieval Augmented Generation do chatbota"},
        ],
        "tools": ["Qdrant", "OpenAI", "Docker", "Python"],
        "difficulty": "advanced",
        "totalTimeSaved": "15h/tydzień",
        "isPublished": True,
        "isFeatured": True,
    },
    {
        "id": "sales-automation",
        "title": "Pakiet wdrożeniowy: automatyzacja sprzedaży",
        "slug": "sales-automation",
        "description": "Kompletny zestaw do automatyzacji procesu sprzedaży. Od kwalifikacji leadów po outreach w CRM.",
        "category": "Sprzedaż",
        "price": 497,
        "originalPrice": None,
        "processes": [
            {"name": "Scoring AI + CRM", "description": "Automatyczna kwalifikacja leadów z AI scoring"},
            {"name": "Cold outreach AI", "description": "Automatyczny cold outreach w CRM"},
        ],
        "tools": ["n8n", "HubSpot", "Instantly", "Clearbit", "Slack"],
        "difficulty": "intermediate",
        "totalTimeSaved": "15h/tydzień",
        "isPublished": True,
        "isFeatured": False,
    },
    {
        "id": "content-creator",
        "title": "Pakiet wdrożeniowy: twórca treści AI",
        "slug": "content-creator",
        "description": "Automatyzacja tworzenia i dystrybucji treści. Repurposing AI i harmonogramowanie w social media.",
        "category": "Marketing",
        "price": 497,
        "originalPrice": None,
        "processes": [
            {"name": "AI generuje treści", "description": "Automatyczne generowanie treści przez AI"},
            {"name": "Auto-publikacja", "description": "Automatyczna publikacja w social media"},
        ],
        "tools": ["n8n", "OpenAI", "Whisper", "Buffer"],
        "difficulty": "beginner",
        "totalTimeSaved": "10h/tydzień",
        "isPublished": True,
        "isFeatured": False,
    },
    {
        "id": "devops-autopilot",
        "title": "Pakiet wdrożeniowy: AI DevOps Autopilot",
        "slug": "devops-autopilot",
        "description": "Autonomiczny monitoring infrastruktury i obsługa incydentów w czasie rzeczywistym. Integracja Sentry, Kubernetes i Slack.",
        "category": "Inżynieria",
        "price": 597,
        "originalPrice": None,
        "processes": [
            {"name": "Incident Response AI", "description": "Automatyczna odpowiedź na incydenty z AI"},
            {"name": "Inteligentny monitoring", "description": "Monitoring infrastruktury z AI"},
        ],
        "tools": ["Kubernetes", "Sentry", "Snyder", "GitHub API", "Slack"],
        "difficulty": "advanced",
        "totalTimeSaved": "20h/tydzień",
        "isPublished": True,
        "isFeatured": False,
    },
    {
        "id": "social-media",
        "title": "Pakiet wdrożeniowy: social media",
        "slug": "social-media",
        "description": "Automatyzacja obecności w mediach społecznościowych. Inteligentny repurposing treści i planowanie publikacji z AI.",
        "category": "Marketing",
        "price": 397,
        "originalPrice": None,
        "processes": [
            {"name": "Repurposing treści AI", "description": "Automatyczne przetwarzanie treści na różne formaty"},
            {"name": "Auto-publikacja postów", "description": "Automatyczna publikacja w social media"},
        ],
        "tools": ["n8n", "OpenAI", "Buffer", "Canva API", "Whisper"],
        "difficulty": "intermediate",
        "totalTimeSaved": "12h/tydzień",
        "isPublished": True,
        "isFeatured": False,
    },
]


def migrate_packages(db: Session) -> None:
    """Migrate package data to database."""
    print("Starting package migration...")

    for pkg_data in PACKAGE_DATA:
        # Check if package already exists
        existing = db.query(Package).filter(Package.slug == pkg_data["slug"]).first()
        if existing:
            print(f"Package '{pkg_data['slug']}' already exists, skipping...")
            continue

        # Convert price from PLN to grosz (69 PLN → 6900 groszy)
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

        print(f"Created package: {pkg_data['slug']} with {len(pkg_data['processes'])} processes")

    db.commit()
    print("Package migration completed successfully!")


def main() -> None:
    """Main function to run the migration."""
    db = SessionLocal()
    try:
        migrate_packages(db)
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
