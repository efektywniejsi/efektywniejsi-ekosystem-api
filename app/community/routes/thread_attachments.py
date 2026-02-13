from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models.user import User
from app.community.models.thread import CommunityThread
from app.community.models.thread_attachment import ThreadAttachment
from app.core.storage import generate_unique_filename, get_storage
from app.db.session import get_db

router = APIRouter()

ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/zip",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
]

MAX_FILES_PER_THREAD = 5
MAX_FILE_SIZE_MB = 10


@router.post(
    "/threads/{thread_id}/attachments",
    status_code=status.HTTP_201_CREATED,
)
async def upload_thread_attachment(
    thread_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    thread = db.query(CommunityThread).filter(CommunityThread.id == thread_id).first()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wątek nie znaleziony",
        )

    if thread.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tylko autor wątku lub administrator może dodawać załączniki",
        )

    existing_count = (
        db.query(ThreadAttachment).filter(ThreadAttachment.thread_id == thread_id).count()
    )
    if existing_count >= MAX_FILES_PER_THREAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_FILES_PER_THREAD} attachments per thread",
        )

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid file type. Allowed: PDF, ZIP, PNG, JPG, GIF, WebP. "
                f"Received: {file.content_type}"
            ),
        )

    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Rozmiar pliku przekracza maksymalny dozwolony rozmiar {MAX_FILE_SIZE_MB}MB",
        )

    unique_filename = generate_unique_filename(file.filename or "file.bin")
    storage = get_storage()
    stored_path = storage.upload(file_content, "thread-attachments", unique_filename)

    attachment = ThreadAttachment(
        thread_id=thread_id,
        uploader_id=current_user.id,
        file_name=file.filename or unique_filename,
        file_path=stored_path,
        file_size_bytes=file_size,
        mime_type=file.content_type or "application/octet-stream",
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "id": str(attachment.id),
        "thread_id": str(attachment.thread_id),
        "file_name": attachment.file_name,
        "file_size_bytes": attachment.file_size_bytes,
        "mime_type": attachment.mime_type,
        "created_at": attachment.created_at,
    }


@router.get("/threads/{thread_id}/attachments")
def list_thread_attachments(
    thread_id: UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[dict]:
    thread = db.query(CommunityThread).filter(CommunityThread.id == thread_id).first()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wątek nie znaleziony",
        )

    attachments = (
        db.query(ThreadAttachment)
        .filter(ThreadAttachment.thread_id == thread_id)
        .order_by(ThreadAttachment.created_at)
        .all()
    )

    return [
        {
            "id": str(a.id),
            "thread_id": str(a.thread_id),
            "file_name": a.file_name,
            "file_size_bytes": a.file_size_bytes,
            "mime_type": a.mime_type,
            "created_at": a.created_at,
        }
        for a in attachments
    ]


@router.get("/thread-attachments/{attachment_id}/download")
def download_thread_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> RedirectResponse:
    attachment = db.query(ThreadAttachment).filter(ThreadAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    storage = get_storage()
    if not storage.exists(attachment.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plik nie znaleziony na serwerze",
        )

    url = storage.download_url(attachment.file_path)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.delete(
    "/thread-attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_thread_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    attachment = db.query(ThreadAttachment).filter(ThreadAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    if attachment.uploader_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tylko właściciel załącznika lub administrator może go usunąć",
        )

    storage = get_storage()
    storage.delete(attachment.file_path)

    db.delete(attachment)
    db.commit()
