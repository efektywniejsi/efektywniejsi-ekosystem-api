"""Routes for implementation package processes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models.user import User
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.implementation_packages.models.implementation_package import (
    ImplementationPackage,
    ImplementationPackageProcess,
)
from app.implementation_packages.schemas import (
    ProcessCreateRequest,
    ProcessUpdateRequest,
)

router = APIRouter()


@router.post("/{package_id}/processes", response_model=dict, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_process(
    request: Request,
    package_id: uuid.UUID,
    data: ProcessCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    pkg = db.query(ImplementationPackage).filter(ImplementationPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pakiet nie został znaleziony"
        )

    process = ImplementationPackageProcess(
        id=uuid.uuid4(),
        package_id=package_id,
        name=data.name,
        description=data.description,
        sort_order=data.sort_order,
    )
    db.add(process)
    db.commit()
    db.refresh(process)
    return {
        "id": str(process.id),
        "name": process.name,
        "description": process.description,
        "sort_order": process.sort_order,
    }


@router.patch("/processes/{process_id}", response_model=dict)
@limiter.limit("30/minute")
async def update_process(
    request: Request,
    process_id: uuid.UUID,
    data: ProcessUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    process = (
        db.query(ImplementationPackageProcess)
        .filter(ImplementationPackageProcess.id == process_id)
        .first()
    )
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proces nie został znaleziony"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(process, field, value)

    db.commit()
    db.refresh(process)
    return {
        "id": str(process.id),
        "name": process.name,
        "description": process.description,
        "sort_order": process.sort_order,
    }


@router.delete("/processes/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_process(
    request: Request,
    process_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    process = (
        db.query(ImplementationPackageProcess)
        .filter(ImplementationPackageProcess.id == process_id)
        .first()
    )
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proces nie został znaleziony"
        )
    db.delete(process)
    db.commit()
