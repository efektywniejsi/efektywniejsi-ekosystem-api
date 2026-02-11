from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models.user import User
from app.db.session import get_db
from app.integrations.schemas import ProposalCreate, ProposalResponse, ProposalUpdate
from app.integrations.services import IntegrationService

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# User Endpoints
# ─────────────────────────────────────────────────────────────


@router.post(
    "/integration-proposals",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_proposal(
    data: ProposalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProposalResponse:
    """Submit a new integration proposal."""
    service = IntegrationService(db)
    return service.create_proposal(data, current_user)


@router.get("/integration-proposals/mine", response_model=list[ProposalResponse])
def get_my_proposals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProposalResponse]:
    """Get current user's proposals."""
    service = IntegrationService(db)
    return service.get_user_proposals(current_user)


# ─────────────────────────────────────────────────────────────
# Admin Endpoints
# ─────────────────────────────────────────────────────────────


@router.get("/admin/integration-proposals", response_model=list[ProposalResponse])
def list_all_proposals(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ProposalResponse]:
    """List all proposals - Admin only."""
    service = IntegrationService(db)
    return service.get_all_proposals()


@router.patch("/admin/integration-proposals/{proposal_id}", response_model=ProposalResponse)
def update_proposal_status(
    proposal_id: UUID,
    data: ProposalUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProposalResponse:
    """Update proposal status - Admin only."""
    service = IntegrationService(db)
    return service.update_proposal(proposal_id, data)
