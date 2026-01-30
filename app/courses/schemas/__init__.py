"""Course schemas."""

from app.courses.schemas.certificate import (
    CertificateResponse,
    CertificateVerifyResponse,
    CertificateWithCourseResponse,
)
from app.courses.schemas.course import (
    CourseCreate,
    CourseDetailResponse,
    CourseResponse,
    CourseUpdate,
    EnrollmentResponse,
    EnrollmentWithCourseResponse,
    LessonCreate,
    LessonResponse,
    LessonUpdate,
    LessonWithProgressResponse,
    ModuleCreate,
    ModuleResponse,
    ModuleUpdate,
    ModuleWithLessonsResponse,
)
from app.courses.schemas.gamification import (
    AchievementResponse,
    GamificationSummaryResponse,
    UserAchievementResponse,
    UserPointsResponse,
    UserStreakResponse,
)
from app.courses.schemas.progress import (
    CourseProgressSummary,
    LessonProgressResponse,
    ProgressUpdateRequest,
)

__all__ = [
    "CourseCreate",
    "CourseUpdate",
    "CourseResponse",
    "CourseDetailResponse",
    "ModuleCreate",
    "ModuleUpdate",
    "ModuleResponse",
    "ModuleWithLessonsResponse",
    "LessonCreate",
    "LessonUpdate",
    "LessonResponse",
    "LessonWithProgressResponse",
    "EnrollmentResponse",
    "EnrollmentWithCourseResponse",
    "ProgressUpdateRequest",
    "LessonProgressResponse",
    "CourseProgressSummary",
    "AchievementResponse",
    "UserAchievementResponse",
    "UserStreakResponse",
    "UserPointsResponse",
    "GamificationSummaryResponse",
    "CertificateResponse",
    "CertificateWithCourseResponse",
    "CertificateVerifyResponse",
]
