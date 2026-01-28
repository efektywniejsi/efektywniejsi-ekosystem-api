from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.schemas.brand_guidelines import BrandGuidelinesResponse, BrandGuidelinesUpdate
from app.ai.services.brand_guidelines_service import get_brand_guidelines, upsert_brand_guidelines
from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.db.session import get_db

router = APIRouter()


@router.get(
    "/brand-guidelines",
    response_model=BrandGuidelinesResponse,
)
async def get_guidelines(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> BrandGuidelinesResponse:
    """Get current brand guidelines (admin only)."""
    guidelines = get_brand_guidelines(db)
    if guidelines is None:
        return BrandGuidelinesResponse()
    return BrandGuidelinesResponse.model_validate(guidelines)


@router.put(
    "/brand-guidelines",
    response_model=BrandGuidelinesResponse,
)
async def update_guidelines(
    data: BrandGuidelinesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> BrandGuidelinesResponse:
    """Create or update brand guidelines (admin only)."""
    guidelines = upsert_brand_guidelines(db, data)
    return BrandGuidelinesResponse.model_validate(guidelines)
