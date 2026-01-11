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
    CourseWithProgressResponse,
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
    PointsHistoryResponse,
    UserAchievementResponse,
    UserPointsResponse,
    UserStreakResponse,
)
from app.courses.schemas.progress import (
    CourseProgressSummary,
    LessonProgressResponse,
    LessonProgressWithLesson,
    ProgressUpdateRequest,
)

__all__ = [
    # Course schemas
    "CourseCreate",
    "CourseUpdate",
    "CourseResponse",
    "CourseDetailResponse",
    "CourseWithProgressResponse",
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
    # Progress schemas
    "ProgressUpdateRequest",
    "LessonProgressResponse",
    "CourseProgressSummary",
    "LessonProgressWithLesson",
    # Gamification schemas
    "AchievementResponse",
    "UserAchievementResponse",
    "UserStreakResponse",
    "UserPointsResponse",
    "PointsHistoryResponse",
    "GamificationSummaryResponse",
    # Certificate schemas
    "CertificateResponse",
    "CertificateWithCourseResponse",
    "CertificateVerifyResponse",
]
