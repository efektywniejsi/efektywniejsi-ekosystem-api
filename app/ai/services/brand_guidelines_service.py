from sqlalchemy.orm import Session

from app.ai.models.brand_guidelines import BrandGuidelines
from app.ai.schemas.brand_guidelines import BrandGuidelinesUpdate


def get_brand_guidelines(db: Session) -> BrandGuidelines | None:
    result: BrandGuidelines | None = (
        db.query(BrandGuidelines).filter(BrandGuidelines.name == "default").first()
    )
    return result


def upsert_brand_guidelines(db: Session, data: BrandGuidelinesUpdate) -> BrandGuidelines:
    existing = get_brand_guidelines(db)

    if existing:
        for field, value in data.model_dump().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    guidelines = BrandGuidelines(name="default", **data.model_dump())
    db.add(guidelines)
    db.commit()
    db.refresh(guidelines)
    return guidelines
