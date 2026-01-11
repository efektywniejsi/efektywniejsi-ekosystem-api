import io
import secrets
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.auth.models.user import User
from app.core.config import settings
from app.courses.models import Certificate, Course, Enrollment


class CertificateService:
    @staticmethod
    def generate_certificate_code() -> str:
        """Generate a unique certificate code."""
        return secrets.token_urlsafe(16)

    @staticmethod
    def generate_certificate_pdf(user: User, course: Course, certificate_code: str) -> bytes:
        """Generate a certificate PDF."""
        # Create a buffer for PDF
        buffer = io.BytesIO()

        # Create canvas (A4 landscape)
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(buffer, pagesize=landscape(A4))

        # Set font and colors
        # Background gradient effect (using rectangles with different opacity)
        c.setFillColorRGB(0.05, 0.05, 0.1)  # Dark background
        c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        # Violet accent border
        c.setStrokeColorRGB(0.54, 0.36, 0.96)  # Violet color
        c.setLineWidth(3)
        c.rect(1 * cm, 1 * cm, page_width - 2 * cm, page_height - 2 * cm, fill=0, stroke=1)

        # Inner border (cyan)
        c.setStrokeColorRGB(0.4, 0.82, 0.87)  # Cyan color
        c.setLineWidth(1)
        c.rect(1.5 * cm, 1.5 * cm, page_width - 3 * cm, page_height - 3 * cm, fill=0, stroke=1)

        # Title - "CERTIFICATE OF COMPLETION"
        c.setFillColorRGB(1, 1, 1)  # White text
        c.setFont("Helvetica-Bold", 36)
        title = "CERTIFICATE OF COMPLETION"
        title_width = c.stringWidth(title, "Helvetica-Bold", 36)
        c.drawString((page_width - title_width) / 2, page_height - 4 * cm, title)

        # Subtitle line
        c.setStrokeColorRGB(0.54, 0.36, 0.96)
        c.setLineWidth(2)
        c.line(8 * cm, page_height - 5 * cm, page_width - 8 * cm, page_height - 5 * cm)

        # "This certifies that"
        c.setFont("Helvetica", 18)
        c.setFillColorRGB(0.8, 0.8, 0.8)
        text = "This certifies that"
        text_width = c.stringWidth(text, "Helvetica", 18)
        c.drawString((page_width - text_width) / 2, page_height - 7 * cm, text)

        # User name (highlighted)
        c.setFont("Helvetica-Bold", 32)
        c.setFillColorRGB(0.4, 0.82, 0.87)  # Cyan for name
        user_name = user.name
        name_width = c.stringWidth(user_name, "Helvetica-Bold", 32)
        c.drawString((page_width - name_width) / 2, page_height - 9 * cm, user_name)

        # Name underline
        c.setStrokeColorRGB(0.4, 0.82, 0.87)
        c.setLineWidth(1)
        name_x_start = (page_width - name_width) / 2
        c.line(
            name_x_start, page_height - 9.5 * cm, name_x_start + name_width, page_height - 9.5 * cm
        )

        # "has successfully completed"
        c.setFont("Helvetica", 18)
        c.setFillColorRGB(0.8, 0.8, 0.8)
        text = "has successfully completed"
        text_width = c.stringWidth(text, "Helvetica", 18)
        c.drawString((page_width - text_width) / 2, page_height - 11 * cm, text)

        # Course title (highlighted)
        c.setFont("Helvetica-Bold", 28)
        c.setFillColorRGB(0.54, 0.36, 0.96)  # Violet for course
        course_title = course.title
        course_width = c.stringWidth(course_title, "Helvetica-Bold", 28)
        c.drawString((page_width - course_width) / 2, page_height - 13 * cm, course_title)

        # Date
        c.setFont("Helvetica", 14)
        c.setFillColorRGB(0.7, 0.7, 0.7)
        date_str = datetime.utcnow().strftime("%B %d, %Y")
        text = f"Issued on {date_str}"
        text_width = c.stringWidth(text, "Helvetica", 14)
        c.drawString((page_width - text_width) / 2, page_height - 15.5 * cm, text)

        # Certificate code (bottom)
        c.setFont("Courier", 10)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        code_text = f"Certificate Code: {certificate_code}"
        code_width = c.stringWidth(code_text, "Courier", 10)
        c.drawString((page_width - code_width) / 2, 2 * cm, code_text)

        # Verification URL
        c.setFont("Helvetica", 9)
        verify_text = f"Verify at: {settings.FRONTEND_URL}/verify/{certificate_code}"
        verify_width = c.stringWidth(verify_text, "Helvetica", 9)
        c.drawString((page_width - verify_width) / 2, 1.5 * cm, verify_text)

        # Logo/Badge (optional - using text for now)
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0.54, 0.36, 0.96)
        logo_text = "EFEKTYWNIEJSI"
        logo_width = c.stringWidth(logo_text, "Helvetica-Bold", 14)
        c.drawString((page_width - logo_width) / 2, page_height - 2 * cm, logo_text)

        # Finalize PDF
        c.showPage()
        c.save()

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    @staticmethod
    def create_certificate(user_id: UUID, course_id: UUID, db: Session) -> Certificate:
        """Create a certificate for a user who completed a course."""
        # Check if user completed the course
        enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
            .first()
        )

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        if not enrollment.completed_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course not completed yet",
            )

        # Check if certificate already exists
        existing_certificate = (
            db.query(Certificate)
            .filter(Certificate.user_id == user_id, Certificate.course_id == course_id)
            .first()
        )

        if existing_certificate:
            return existing_certificate

        # Get user and course
        user = db.query(User).filter(User.id == user_id).first()
        course = db.query(Course).filter(Course.id == course_id).first()

        if not user or not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User or course not found",
            )

        # Generate certificate code
        certificate_code = CertificateService.generate_certificate_code()

        # Generate PDF
        pdf_bytes = CertificateService.generate_certificate_pdf(user, course, certificate_code)

        # Save PDF to filesystem
        upload_dir = Path(settings.UPLOAD_DIR) / "certificates"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / f"{certificate_code}.pdf"
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        # Create certificate record
        certificate = Certificate(
            user_id=user_id,
            course_id=course_id,
            certificate_code=certificate_code,
            issued_at=datetime.utcnow(),
            file_path=str(file_path),
        )
        db.add(certificate)

        # Update enrollment
        enrollment.certificate_issued_at = datetime.utcnow()

        db.commit()
        db.refresh(certificate)

        return certificate

    @staticmethod
    def verify_certificate(certificate_code: str, db: Session) -> dict:
        """Verify a certificate by its code."""
        certificate = (
            db.query(Certificate).filter(Certificate.certificate_code == certificate_code).first()
        )

        if not certificate:
            return {
                "valid": False,
                "certificate_code": certificate_code,
                "user_name": "",
                "course_title": "",
                "issued_at": None,
                "message": "Certificate not found",
            }

        # Get user and course
        user = db.query(User).filter(User.id == certificate.user_id).first()
        course = db.query(Course).filter(Course.id == certificate.course_id).first()

        return {
            "valid": True,
            "certificate_code": certificate_code,
            "user_name": user.name if user else "Unknown",
            "course_title": course.title if course else "Unknown",
            "issued_at": certificate.issued_at,
            "message": "Certificate is valid",
        }
