from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.courses.models.course import Lesson, Module
from app.processes.models import LessonProcess, Process
from app.processes.schemas import (
    LessonProcessCreate,
    LessonProcessResponse,
    ProcessCreate,
    ProcessDetailResponse,
    ProcessLessonBriefResponse,
    ProcessResponse,
    ProcessUpdate,
)


class ProcessService:
    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────────────────────────
    # Public Methods
    # ─────────────────────────────────────────────────────────────

    def get_published_processes(self) -> list[ProcessResponse]:
        usage_counts = self._get_usage_counts()

        processes = (
            self.db.query(Process)
            .filter(Process.is_published == True)  # noqa: E712
            .order_by(Process.sort_order, Process.name)
            .all()
        )

        return [self._to_response(p, usage_counts.get(p.id, 0)) for p in processes]

    def get_published_process_by_slug(self, slug: str) -> ProcessResponse:
        process = (
            self.db.query(Process)
            .filter(Process.slug == slug, Process.is_published == True)  # noqa: E712
            .first()
        )
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proces nie znaleziony",
            )
        usage_count = self._get_usage_count_for_process(process.id)
        return self._to_response(process, usage_count)

    def get_published_process_detail_by_slug(self, slug: str) -> ProcessDetailResponse:
        process = (
            self.db.query(Process)
            .options(
                joinedload(Process.lesson_processes)
                .joinedload(LessonProcess.lesson)
                .joinedload(Lesson.module)
                .joinedload(Module.course)
            )
            .filter(Process.slug == slug, Process.is_published == True)  # noqa: E712
            .first()
        )
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proces nie znaleziony",
            )

        used_in_lessons: list[ProcessLessonBriefResponse] = []
        for lp in process.lesson_processes:
            lesson = lp.lesson
            if lesson and lesson.module and lesson.module.course:
                used_in_lessons.append(
                    ProcessLessonBriefResponse(
                        id=lesson.id,
                        title=lesson.title,
                        course_slug=lesson.module.course.slug,
                        course_title=lesson.module.course.title,
                    )
                )

        usage_count = len(process.lesson_processes)
        base = self._to_response(process, usage_count)

        return ProcessDetailResponse(
            **base.model_dump(),
            used_in_lessons=used_in_lessons,
        )

    # ─────────────────────────────────────────────────────────────
    # Admin CRUD Methods
    # ─────────────────────────────────────────────────────────────

    def get_all_processes(self) -> list[ProcessResponse]:
        usage_counts = self._get_usage_counts()

        processes = self.db.query(Process).order_by(Process.sort_order, Process.name).all()

        return [self._to_response(p, usage_counts.get(p.id, 0)) for p in processes]

    def get_process_by_id(self, process_id: UUID) -> ProcessResponse:
        process = self.db.query(Process).filter(Process.id == process_id).first()
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proces nie znaleziony",
            )

        usage_count = self._get_usage_count_for_process(process_id)
        return self._to_response(process, usage_count)

    def create_process(self, data: ProcessCreate) -> ProcessResponse:
        existing = self.db.query(Process).filter(Process.slug == data.slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proces o tym slug już istnieje",
            )

        process = Process(
            slug=data.slug,
            name=data.name,
            description=data.description,
            icon=data.icon,
            mermaid_diagram=data.mermaid_diagram,
            code_snippets=(
                [s.model_dump() for s in data.code_snippets] if data.code_snippets else None
            ),
            is_published=data.is_published,
            sort_order=data.sort_order,
        )
        self.db.add(process)
        self.db.commit()
        self.db.refresh(process)

        return self._to_response(process, 0)

    def update_process(self, process_id: UUID, data: ProcessUpdate) -> ProcessResponse:
        process = self.db.query(Process).filter(Process.id == process_id).first()
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proces nie znaleziony",
            )

        if data.slug and data.slug != process.slug:
            existing = self.db.query(Process).filter(Process.slug == data.slug).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Proces o tym slug już istnieje",
                )

        update_fields = data.model_dump(exclude_unset=True)

        if "name" in update_fields:
            process.name = data.name
        if "slug" in update_fields:
            process.slug = data.slug
        if "description" in update_fields:
            process.description = data.description
        if "icon" in update_fields:
            process.icon = data.icon
        if "mermaid_diagram" in update_fields:
            process.mermaid_diagram = data.mermaid_diagram
        if "code_snippets" in update_fields:
            process.code_snippets = (
                [s.model_dump() for s in data.code_snippets] if data.code_snippets else None
            )
        if "is_published" in update_fields:
            process.is_published = data.is_published
        if "sort_order" in update_fields:
            process.sort_order = data.sort_order

        self.db.commit()
        self.db.refresh(process)

        usage_count = self._get_usage_count_for_process(process_id)
        return self._to_response(process, usage_count)

    def delete_process(self, process_id: UUID) -> None:
        process = self.db.query(Process).filter(Process.id == process_id).first()
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proces nie znaleziony",
            )

        self.db.delete(process)
        self.db.commit()

    # ─────────────────────────────────────────────────────────────
    # Lesson Process Methods
    # ─────────────────────────────────────────────────────────────

    def get_lesson_processes(self, lesson_id: UUID) -> list[LessonProcessResponse]:
        lesson = self.db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lekcja nie znaleziona",
            )

        lesson_processes = (
            self.db.query(LessonProcess)
            .filter(LessonProcess.lesson_id == lesson_id)
            .order_by(LessonProcess.sort_order)
            .all()
        )

        process_ids = [lp.process_id for lp in lesson_processes]
        usage_counts = self._get_usage_counts_for_ids(process_ids)

        return [
            LessonProcessResponse(
                id=lp.id,
                process=self._to_response(lp.process, usage_counts.get(lp.process_id, 0)),
                context_note=lp.context_note,
                sort_order=lp.sort_order,
            )
            for lp in lesson_processes
        ]

    def attach_process_to_lesson(
        self, lesson_id: UUID, data: LessonProcessCreate
    ) -> LessonProcessResponse:
        lesson = self.db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lekcja nie znaleziona",
            )

        process = self.db.query(Process).filter(Process.id == data.process_id).first()
        if not process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proces nie znaleziony",
            )

        existing = (
            self.db.query(LessonProcess)
            .filter(
                LessonProcess.lesson_id == lesson_id,
                LessonProcess.process_id == data.process_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proces jest już przypisany do tej lekcji",
            )

        lesson_process = LessonProcess(
            lesson_id=lesson_id,
            process_id=data.process_id,
            context_note=data.context_note,
            sort_order=data.sort_order,
        )
        self.db.add(lesson_process)
        self.db.commit()
        self.db.refresh(lesson_process)

        usage_count = self._get_usage_count_for_process(data.process_id)
        return LessonProcessResponse(
            id=lesson_process.id,
            process=self._to_response(process, usage_count),
            context_note=lesson_process.context_note,
            sort_order=lesson_process.sort_order,
        )

    def detach_process_from_lesson(self, lesson_id: UUID, process_id: UUID) -> None:
        lesson_process = (
            self.db.query(LessonProcess)
            .filter(
                LessonProcess.lesson_id == lesson_id,
                LessonProcess.process_id == process_id,
            )
            .first()
        )

        if not lesson_process:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Powiązanie nie znalezione",
            )

        self.db.delete(lesson_process)
        self.db.commit()

    # ─────────────────────────────────────────────────────────────
    # Private Helpers
    # ─────────────────────────────────────────────────────────────

    def _get_usage_counts(self) -> dict[UUID, int]:
        results = (
            self.db.query(
                LessonProcess.process_id,
                func.count(LessonProcess.id).label("count"),
            )
            .group_by(LessonProcess.process_id)
            .all()
        )
        return {row[0]: row[1] for row in results}

    def _get_usage_counts_for_ids(self, process_ids: list[UUID]) -> dict[UUID, int]:
        if not process_ids:
            return {}
        results = (
            self.db.query(
                LessonProcess.process_id,
                func.count(LessonProcess.id).label("count"),
            )
            .filter(LessonProcess.process_id.in_(process_ids))
            .group_by(LessonProcess.process_id)
            .all()
        )
        return {row[0]: row[1] for row in results}

    def _get_usage_count_for_process(self, process_id: UUID) -> int:
        count: int = (
            self.db.query(LessonProcess).filter(LessonProcess.process_id == process_id).count()
        )
        return count

    def _to_response(self, process: Process, usage_count: int) -> ProcessResponse:
        return ProcessResponse(
            id=process.id,
            slug=process.slug,
            name=process.name,
            description=process.description,
            icon=process.icon,
            mermaid_diagram=process.mermaid_diagram,
            code_snippets=process.code_snippets,
            is_published=process.is_published,
            sort_order=process.sort_order,
            usage_count=usage_count,
            created_at=process.created_at,
            updated_at=process.updated_at,
        )
