from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.models.user import User
from app.courses.models.course import Lesson, Module
from app.integrations.models import (
    Integration,
    IntegrationProposal,
    IntegrationType,
    LessonIntegration,
    ProcessIntegration,
)
from app.integrations.schemas import (
    CategoryCountResponse,
    IntegrationCreate,
    IntegrationDetailResponse,
    IntegrationResponse,
    IntegrationUpdate,
    LessonBriefResponse,
    LessonIntegrationCreate,
    LessonIntegrationResponse,
    ProcessIntegrationCreate,
    ProcessIntegrationResponse,
    ProposalCreate,
    ProposalResponse,
    ProposalUpdate,
)
from app.packages.models.package import PackageProcess


class IntegrationService:
    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────────────────────────
    # Public Integration Methods
    # ─────────────────────────────────────────────────────────────

    def get_published_integrations(
        self,
        category: str | None = None,
        search: str | None = None,
    ) -> list[IntegrationResponse]:
        # Pre-load usage counts in single query to avoid N+1
        usage_counts = self._get_usage_counts()

        query = (
            self.db.query(Integration)
            .options(joinedload(Integration.integration_types))
            .filter(Integration.is_published == True)  # noqa: E712
        )

        if category:
            query = query.filter(Integration.category == category)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Integration.name.ilike(search_pattern))
                | (Integration.description.ilike(search_pattern))
            )

        query = query.order_by(Integration.sort_order, Integration.name)
        integrations = query.all()

        return [self._to_response(i, usage_counts.get(i.id, 0)) for i in integrations]

    def get_integration_by_slug(
        self, slug: str, include_unpublished: bool = False
    ) -> IntegrationDetailResponse:
        query = (
            self.db.query(Integration)
            .options(
                joinedload(Integration.integration_types),
                joinedload(Integration.lesson_integrations)
                .joinedload(LessonIntegration.lesson)
                .joinedload(Lesson.module)
                .joinedload(Module.course),
            )
            .filter(Integration.slug == slug)
        )

        if not include_unpublished:
            query = query.filter(Integration.is_published == True)  # noqa: E712

        integration = query.first()

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integracja nie znaleziona",
            )

        return self._to_detail_response(integration)

    def get_categories_with_counts(self) -> list[CategoryCountResponse]:
        results = (
            self.db.query(
                Integration.category,
                func.count(Integration.id).label("count"),
            )
            .filter(Integration.is_published == True)  # noqa: E712
            .group_by(Integration.category)
            .order_by(func.count(Integration.id).desc())
            .all()
        )

        return [CategoryCountResponse(category=r.category, count=r.count) for r in results]

    # ─────────────────────────────────────────────────────────────
    # Admin Integration Methods
    # ─────────────────────────────────────────────────────────────

    def get_all_integrations(self) -> list[IntegrationResponse]:
        # Pre-load usage counts in single query to avoid N+1
        usage_counts = self._get_usage_counts()

        integrations = (
            self.db.query(Integration)
            .options(joinedload(Integration.integration_types))
            .order_by(Integration.sort_order, Integration.name)
            .all()
        )
        return [self._to_response(i, usage_counts.get(i.id, 0)) for i in integrations]

    def get_integration_by_id(self, integration_id: UUID) -> IntegrationDetailResponse:
        integration = (
            self.db.query(Integration)
            .options(
                joinedload(Integration.integration_types),
                joinedload(Integration.lesson_integrations)
                .joinedload(LessonIntegration.lesson)
                .joinedload(Lesson.module)
                .joinedload(Module.course),
            )
            .filter(Integration.id == integration_id)
            .first()
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integracja nie znaleziona",
            )

        return self._to_detail_response(integration)

    def create_integration(self, data: IntegrationCreate, created_by: User) -> IntegrationResponse:
        # Check for slug uniqueness
        existing = self.db.query(Integration).filter(Integration.slug == data.slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integracja o tym slug już istnieje",
            )

        integration = Integration(
            slug=data.slug,
            name=data.name,
            icon=data.icon,
            category=data.category,
            description=data.description,
            auth_guide=data.auth_guide,
            official_docs_url=str(data.official_docs_url) if data.official_docs_url else None,
            video_tutorial_url=str(data.video_tutorial_url) if data.video_tutorial_url else None,
            is_published=data.is_published,
            sort_order=data.sort_order,
            created_by_id=created_by.id,
        )
        self.db.add(integration)
        self.db.flush()

        # Add integration types
        for type_name in data.integration_types:
            self.db.add(IntegrationType(integration_id=integration.id, type_name=type_name))

        self.db.commit()
        self.db.refresh(integration)

        return self._to_response(integration, 0)

    def update_integration(
        self, integration_id: UUID, data: IntegrationUpdate
    ) -> IntegrationResponse:
        integration = (
            self.db.query(Integration)
            .options(joinedload(Integration.integration_types))
            .filter(Integration.id == integration_id)
            .first()
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integracja nie znaleziona",
            )

        # Check slug uniqueness if changing
        if data.slug and data.slug != integration.slug:
            existing = self.db.query(Integration).filter(Integration.slug == data.slug).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Integracja o tym slug już istnieje",
                )

        # Update fields explicitly (not using setattr loop for clarity)
        if data.name is not None:
            integration.name = data.name
        if data.slug is not None:
            integration.slug = data.slug
        if data.icon is not None:
            integration.icon = data.icon
        if data.category is not None:
            integration.category = data.category
        if data.description is not None:
            integration.description = data.description
        if data.auth_guide is not None:
            integration.auth_guide = data.auth_guide
        if data.official_docs_url is not None:
            integration.official_docs_url = str(data.official_docs_url)
        if data.video_tutorial_url is not None:
            integration.video_tutorial_url = str(data.video_tutorial_url)
        if data.is_published is not None:
            integration.is_published = data.is_published
        if data.sort_order is not None:
            integration.sort_order = data.sort_order

        # Update integration types if provided
        if data.integration_types is not None:
            # Remove existing types
            self.db.query(IntegrationType).filter(
                IntegrationType.integration_id == integration_id
            ).delete()

            # Add new types
            for type_name in data.integration_types:
                self.db.add(IntegrationType(integration_id=integration.id, type_name=type_name))

        self.db.commit()
        self.db.refresh(integration)

        usage_count = self._get_usage_count_for_integration(integration_id)
        return self._to_response(integration, usage_count)

    def delete_integration(self, integration_id: UUID) -> None:
        integration = self.db.query(Integration).filter(Integration.id == integration_id).first()

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integracja nie znaleziona",
            )

        self.db.delete(integration)
        self.db.commit()

    # ─────────────────────────────────────────────────────────────
    # Lesson Integration Methods
    # ─────────────────────────────────────────────────────────────

    def get_lesson_integrations(self, lesson_id: UUID) -> list[LessonIntegrationResponse]:
        # Verify lesson exists
        lesson = self.db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lekcja nie znaleziona",
            )

        lesson_integrations = (
            self.db.query(LessonIntegration)
            .options(
                joinedload(LessonIntegration.integration).joinedload(Integration.integration_types)
            )
            .filter(LessonIntegration.lesson_id == lesson_id)
            .order_by(LessonIntegration.sort_order)
            .all()
        )

        # Get usage counts for these integrations
        integration_ids = [li.integration_id for li in lesson_integrations]
        usage_counts = self._get_usage_counts_for_ids(integration_ids)

        return [
            LessonIntegrationResponse(
                id=li.id,
                integration=self._to_response(
                    li.integration, usage_counts.get(li.integration_id, 0)
                ),
                context_note=li.context_note,
                sort_order=li.sort_order,
            )
            for li in lesson_integrations
        ]

    def attach_integration_to_lesson(
        self, lesson_id: UUID, data: LessonIntegrationCreate
    ) -> LessonIntegrationResponse:
        # Verify lesson exists
        lesson = self.db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lekcja nie znaleziona",
            )

        # Verify integration exists
        integration = (
            self.db.query(Integration)
            .options(joinedload(Integration.integration_types))
            .filter(Integration.id == data.integration_id)
            .first()
        )
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integracja nie znaleziona",
            )

        # Check if already attached
        existing = (
            self.db.query(LessonIntegration)
            .filter(
                LessonIntegration.lesson_id == lesson_id,
                LessonIntegration.integration_id == data.integration_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integracja jest już przypisana do tej lekcji",
            )

        lesson_integration = LessonIntegration(
            lesson_id=lesson_id,
            integration_id=data.integration_id,
            context_note=data.context_note,
            sort_order=data.sort_order,
        )
        self.db.add(lesson_integration)
        self.db.commit()
        self.db.refresh(lesson_integration)

        usage_count = self._get_usage_count_for_integration(data.integration_id)
        return LessonIntegrationResponse(
            id=lesson_integration.id,
            integration=self._to_response(integration, usage_count),
            context_note=lesson_integration.context_note,
            sort_order=lesson_integration.sort_order,
        )

    def detach_integration_from_lesson(self, lesson_id: UUID, integration_id: UUID) -> None:
        lesson_integration = (
            self.db.query(LessonIntegration)
            .filter(
                LessonIntegration.lesson_id == lesson_id,
                LessonIntegration.integration_id == integration_id,
            )
            .first()
        )

        if not lesson_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Powiązanie nie znalezione",
            )

        self.db.delete(lesson_integration)
        self.db.commit()

    # ─────────────────────────────────────────────────────────────
    # Process Integration Methods
    # ─────────────────────────────────────────────────────────────

    def get_process_integrations(self, process_id: UUID) -> list[ProcessIntegrationResponse]:
        # Verify process exists
        process = self.db.query(PackageProcess).filter(PackageProcess.id == process_id).first()
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proces nie znaleziony",
            )

        process_integrations = (
            self.db.query(ProcessIntegration)
            .options(
                joinedload(ProcessIntegration.integration).joinedload(Integration.integration_types)
            )
            .filter(ProcessIntegration.process_id == process_id)
            .order_by(ProcessIntegration.sort_order)
            .all()
        )

        # Get usage counts for these integrations
        integration_ids = [pi.integration_id for pi in process_integrations]
        usage_counts = self._get_usage_counts_for_ids(integration_ids)

        return [
            ProcessIntegrationResponse(
                id=pi.id,
                integration=self._to_response(
                    pi.integration, usage_counts.get(pi.integration_id, 0)
                ),
                context_note=pi.context_note,
                sort_order=pi.sort_order,
            )
            for pi in process_integrations
        ]

    def attach_integration_to_process(
        self, process_id: UUID, data: ProcessIntegrationCreate
    ) -> ProcessIntegrationResponse:
        # Verify process exists
        process = self.db.query(PackageProcess).filter(PackageProcess.id == process_id).first()
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proces nie znaleziony",
            )

        # Verify integration exists
        integration = (
            self.db.query(Integration)
            .options(joinedload(Integration.integration_types))
            .filter(Integration.id == data.integration_id)
            .first()
        )
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integracja nie znaleziona",
            )

        # Check if already attached
        existing = (
            self.db.query(ProcessIntegration)
            .filter(
                ProcessIntegration.process_id == process_id,
                ProcessIntegration.integration_id == data.integration_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integracja jest już przypisana do tego procesu",
            )

        process_integration = ProcessIntegration(
            process_id=process_id,
            integration_id=data.integration_id,
            context_note=data.context_note,
            sort_order=data.sort_order,
        )
        self.db.add(process_integration)
        self.db.commit()
        self.db.refresh(process_integration)

        usage_count = self._get_usage_count_for_integration(data.integration_id)
        return ProcessIntegrationResponse(
            id=process_integration.id,
            integration=self._to_response(integration, usage_count),
            context_note=process_integration.context_note,
            sort_order=process_integration.sort_order,
        )

    def detach_integration_from_process(self, process_id: UUID, integration_id: UUID) -> None:
        process_integration = (
            self.db.query(ProcessIntegration)
            .filter(
                ProcessIntegration.process_id == process_id,
                ProcessIntegration.integration_id == integration_id,
            )
            .first()
        )

        if not process_integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Powiązanie nie znalezione",
            )

        self.db.delete(process_integration)
        self.db.commit()

    # ─────────────────────────────────────────────────────────────
    # Proposal Methods
    # ─────────────────────────────────────────────────────────────

    def create_proposal(self, data: ProposalCreate, submitted_by: User) -> ProposalResponse:
        proposal = IntegrationProposal(
            name=data.name,
            category=data.category,
            description=data.description,
            official_docs_url=str(data.official_docs_url) if data.official_docs_url else None,
            submitted_by_id=submitted_by.id,
        )
        self.db.add(proposal)
        self.db.commit()
        self.db.refresh(proposal)

        return self._proposal_to_response(proposal, submitted_by.name)

    def get_user_proposals(self, user: User) -> list[ProposalResponse]:
        proposals = (
            self.db.query(IntegrationProposal)
            .filter(IntegrationProposal.submitted_by_id == user.id)
            .order_by(IntegrationProposal.created_at.desc())
            .all()
        )

        return [self._proposal_to_response(p, user.name) for p in proposals]

    def get_all_proposals(self) -> list[ProposalResponse]:
        proposals = (
            self.db.query(IntegrationProposal)
            .options(joinedload(IntegrationProposal.submitted_by))
            .order_by(IntegrationProposal.created_at.desc())
            .all()
        )

        return [
            self._proposal_to_response(p, p.submitted_by.name if p.submitted_by else "Unknown")
            for p in proposals
        ]

    def update_proposal(self, proposal_id: UUID, data: ProposalUpdate) -> ProposalResponse:
        proposal = (
            self.db.query(IntegrationProposal)
            .options(joinedload(IntegrationProposal.submitted_by))
            .filter(IntegrationProposal.id == proposal_id)
            .first()
        )

        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Propozycja nie znaleziona",
            )

        proposal.status = data.status
        if data.admin_notes is not None:
            proposal.admin_notes = data.admin_notes

        self.db.commit()
        self.db.refresh(proposal)

        return self._proposal_to_response(
            proposal, proposal.submitted_by.name if proposal.submitted_by else "Unknown"
        )

    # ─────────────────────────────────────────────────────────────
    # Private Helpers
    # ─────────────────────────────────────────────────────────────

    def _get_usage_counts(self) -> dict[UUID, int]:
        """Get usage counts for all integrations in a single query."""
        results = (
            self.db.query(
                LessonIntegration.integration_id,
                func.count(LessonIntegration.id).label("count"),
            )
            .group_by(LessonIntegration.integration_id)
            .all()
        )
        return {row[0]: row[1] for row in results}

    def _get_usage_counts_for_ids(self, integration_ids: list[UUID]) -> dict[UUID, int]:
        """Get usage counts for specific integration IDs."""
        if not integration_ids:
            return {}
        results = (
            self.db.query(
                LessonIntegration.integration_id,
                func.count(LessonIntegration.id).label("count"),
            )
            .filter(LessonIntegration.integration_id.in_(integration_ids))
            .group_by(LessonIntegration.integration_id)
            .all()
        )
        return {row[0]: row[1] for row in results}

    def _get_usage_count_for_integration(self, integration_id: UUID) -> int:
        """Get usage count for a single integration."""
        count: int = (
            self.db.query(LessonIntegration)
            .filter(LessonIntegration.integration_id == integration_id)
            .count()
        )
        return count

    def _to_response(self, integration: Integration, usage_count: int) -> IntegrationResponse:
        """Convert Integration to response. Usage count must be pre-loaded."""
        return IntegrationResponse(
            id=integration.id,
            slug=integration.slug,
            name=integration.name,
            icon=integration.icon,
            category=integration.category,
            description=integration.description,
            official_docs_url=integration.official_docs_url,
            video_tutorial_url=integration.video_tutorial_url,
            is_published=integration.is_published,
            sort_order=integration.sort_order,
            integration_types=[t.type_name for t in integration.integration_types],
            usage_count=usage_count,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
        )

    def _to_detail_response(self, integration: Integration) -> IntegrationDetailResponse:
        """Convert Integration to detail response with lesson info."""
        usage_count = len(integration.lesson_integrations)

        # Build lesson list from pre-loaded relationships
        used_in_lessons = []
        for li in integration.lesson_integrations:
            lesson = li.lesson
            if lesson and lesson.module and lesson.module.course:
                used_in_lessons.append(
                    LessonBriefResponse(
                        id=lesson.id,
                        title=lesson.title,
                        course_id=lesson.module.course.id,
                        course_title=lesson.module.course.title,
                    )
                )

        return IntegrationDetailResponse(
            id=integration.id,
            slug=integration.slug,
            name=integration.name,
            icon=integration.icon,
            category=integration.category,
            description=integration.description,
            auth_guide=integration.auth_guide,
            official_docs_url=integration.official_docs_url,
            video_tutorial_url=integration.video_tutorial_url,
            is_published=integration.is_published,
            sort_order=integration.sort_order,
            integration_types=[t.type_name for t in integration.integration_types],
            usage_count=usage_count,
            used_in_lessons=used_in_lessons,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
        )

    def _proposal_to_response(
        self, proposal: IntegrationProposal, submitted_by_name: str
    ) -> ProposalResponse:
        return ProposalResponse(
            id=proposal.id,
            name=proposal.name,
            category=proposal.category,
            description=proposal.description,
            official_docs_url=proposal.official_docs_url,
            status=proposal.status,
            admin_notes=proposal.admin_notes,
            submitted_by_id=proposal.submitted_by_id,
            submitted_by_name=submitted_by_name,
            created_at=proposal.created_at,
            updated_at=proposal.updated_at,
        )
