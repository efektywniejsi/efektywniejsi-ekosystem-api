# API Endpoints Documentation

Complete API reference for Efektywniejsi Ekosystem API.

**Base URL**: `http://localhost:8001/api/v1` (development)

**Interactive Docs**: http://localhost:8001/docs

---

## Table of Contents

1. [Authentication](#authentication)
2. [Password Reset](#password-reset)
3. [Admin](#admin)
4. [Courses](#courses)
5. [Enrollments](#enrollments)
6. [Lessons](#lessons)
7. [Progress Tracking](#progress-tracking)
8. [Attachments](#attachments)
9. [Gamification](#gamification)
10. [Certificates](#certificates)
11. [Common Responses](#common-responses)
12. [Error Codes](#error-codes)

---

## Authentication

### POST `/auth/login`

Login with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "paid",
    "created_at": "2026-01-11T10:00:00Z"
  }
}
```

**Cookies Set:**
- `access_token` (HttpOnly, Secure)
- `refresh_token` (HttpOnly, Secure)

**Errors:**
- `401 Unauthorized` - Invalid credentials
- `422 Unprocessable Entity` - Validation error

**Example:**
```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.pl","password":"testuser123"}'
```

---

### POST `/auth/refresh`

Refresh access token using refresh token.

**Authentication:** Requires `refresh_token` cookie

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Errors:**
- `401 Unauthorized` - Invalid/expired refresh token

**Example:**
```bash
curl -X POST http://localhost:8001/api/v1/auth/refresh \
  --cookie "refresh_token=eyJ0eXAiOiJKV1Qi..."
```

---

### POST `/auth/logout`

Revoke refresh token.

**Authentication:** Requires `refresh_token` cookie

**Response:** `200 OK`
```json
{
  "message": "Successfully logged out"
}
```

**Example:**
```bash
curl -X POST http://localhost:8001/api/v1/auth/logout \
  --cookie "refresh_token=eyJ0eXAiOiJKV1Qi..."
```

---

### GET `/auth/me`

Get current authenticated user.

**Authentication:** Required (access_token cookie or Bearer token)

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "name": "John Doe",
  "role": "paid",
  "created_at": "2026-01-11T10:00:00Z"
}
```

**Example:**
```bash
curl -X GET http://localhost:8001/api/v1/auth/me \
  --cookie "access_token=eyJ0eXAiOiJKV1Qi..."
```

---

## Password Reset

### POST `/password/request-reset`

Request password reset email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:** `200 OK`
```json
{
  "message": "If an account exists, a password reset link has been sent"
}
```

**Note:** Always returns 200 to prevent email enumeration.

**Example:**
```bash
curl -X POST http://localhost:8001/api/v1/password/request-reset \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'
```

---

### POST `/password/reset`

Reset password with token.

**Request Body:**
```json
{
  "token": "abc123def456",
  "new_password": "newpassword123"
}
```

**Response:** `200 OK`
```json
{
  "message": "Password has been reset successfully"
}
```

**Errors:**
- `400 Bad Request` - Invalid/expired token
- `422 Unprocessable Entity` - Password validation error

---

## Admin

**All admin endpoints require `role: admin`**

### POST `/admin/users`

Create new user.

**Authentication:** Admin required

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "name": "New User",
  "role": "paid"
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "email": "newuser@example.com",
  "name": "New User",
  "role": "paid",
  "created_at": "2026-01-11T10:00:00Z"
}
```

**Errors:**
- `403 Forbidden` - Not admin
- `409 Conflict` - Email already exists

---

### GET `/admin/users`

List all users with pagination.

**Authentication:** Admin required

**Query Parameters:**
- `page` (integer, default: 1)
- `per_page` (integer, default: 20, max: 100)
- `role` (string, optional: "admin", "paid", "trial")
- `search` (string, optional: search in email/name)

**Response:** `200 OK`
```json
{
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "name": "John Doe",
      "role": "paid",
      "created_at": "2026-01-11T10:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

**Example:**
```bash
curl -X GET "http://localhost:8001/api/v1/admin/users?page=1&per_page=20&role=paid" \
  --cookie "access_token=eyJ0eXAiOiJKV1Qi..."
```

---

### PATCH `/admin/users/{user_id}`

Update user.

**Authentication:** Admin required

**Request Body:** (all fields optional)
```json
{
  "email": "newemail@example.com",
  "name": "Updated Name",
  "role": "admin",
  "password": "newpassword123"
}
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "newemail@example.com",
  "name": "Updated Name",
  "role": "admin",
  "created_at": "2026-01-11T10:00:00Z"
}
```

**Errors:**
- `403 Forbidden` - Not admin
- `404 Not Found` - User not found
- `409 Conflict` - Email already taken

---

## Courses

### GET `/courses`

List all courses.

**Authentication:** Optional (shows only published if not authenticated)

**Query Parameters:**
- `is_published` (boolean, optional)
- `difficulty` (string, optional: "beginner", "intermediate", "advanced")
- `category` (string, optional)
- `is_featured` (boolean, optional)

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "slug": "masterclass-lowcode",
    "title": "Masterclass Low-code",
    "description": "Kompleksowy kurs automatyzacji...",
    "thumbnail_url": null,
    "difficulty": "intermediate",
    "estimated_hours": 12,
    "is_published": true,
    "is_featured": true,
    "category": "masterclass",
    "created_at": "2026-01-11T10:00:00Z"
  }
]
```

**Example:**
```bash
curl -X GET "http://localhost:8001/api/v1/courses?is_published=true&difficulty=intermediate"
```

---

### GET `/courses/{slug}`

Get course details with modules and lessons.

**Authentication:** Optional (shows all if authenticated/admin, only preview if not)

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "slug": "masterclass-lowcode",
  "title": "Masterclass Low-code",
  "description": "Kompleksowy kurs automatyzacji...",
  "difficulty": "intermediate",
  "estimated_hours": 12,
  "is_published": true,
  "is_featured": true,
  "category": "masterclass",
  "modules": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "Moduł 1: Wprowadzenie",
      "description": "Podstawy automatyzacji...",
      "sort_order": 0,
      "lessons": [
        {
          "id": "550e8400-e29b-41d4-a716-446655440002",
          "title": "Wprowadzenie do kursu",
          "description": "Czego się nauczysz...",
          "duration_seconds": 420,
          "is_preview": true,
          "sort_order": 0
        }
      ]
    }
  ]
}
```

**Errors:**
- `404 Not Found` - Course not found

---

### POST `/courses` (Admin)

Create new course.

**Authentication:** Admin required

**Request Body:**
```json
{
  "slug": "new-course",
  "title": "New Course",
  "description": "Course description",
  "difficulty": "beginner",
  "estimated_hours": 8,
  "is_published": false,
  "is_featured": false,
  "category": "tutorial",
  "thumbnail_url": null
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "slug": "new-course",
  "title": "New Course",
  ...
}
```

---

## Enrollments

### POST `/courses/{course_id}/enroll`

Enroll in course.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "course_id": "550e8400-e29b-41d4-a716-446655440001",
  "enrolled_at": "2026-01-11T10:00:00Z",
  "completed_at": null,
  "certificate_issued_at": null
}
```

**Errors:**
- `400 Bad Request` - Already enrolled
- `404 Not Found` - Course not found

**Example:**
```bash
curl -X POST http://localhost:8001/api/v1/courses/550e8400-e29b-41d4-a716-446655440001/enroll \
  --cookie "access_token=eyJ0eXAiOiJKV1Qi..."
```

---

### GET `/enrollments/me`

Get my enrollments.

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440010",
    "course": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "slug": "masterclass-lowcode",
      "title": "Masterclass Low-code",
      "thumbnail_url": null
    },
    "enrolled_at": "2026-01-11T10:00:00Z",
    "completed_at": null,
    "progress_percentage": 35
  }
]
```

---

## Lessons

### GET `/lessons/{lesson_id}`

Get lesson details.

**Authentication:** Required (unless preview lesson)

**Authorization:** Must be enrolled in course OR lesson is preview

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "title": "Wprowadzenie do kursu",
  "description": "Czego się nauczysz...",
  "mux_playback_id": "abc123xyz456",
  "mux_asset_id": "asset-abc-123",
  "duration_seconds": 420,
  "is_preview": true,
  "module_id": "550e8400-e29b-41d4-a716-446655440001",
  "progress": {
    "watched_seconds": 120,
    "last_position_seconds": 120,
    "completion_percentage": 28,
    "is_completed": false
  }
}
```

**Errors:**
- `403 Forbidden` - Not enrolled and not preview
- `404 Not Found` - Lesson not found

---

## Progress Tracking

### POST `/progress/lessons/{lesson_id}`

Update lesson progress.

**Authentication:** Required

**Authorization:** Must be enrolled in course

**Request Body:**
```json
{
  "watched_seconds": 120,
  "last_position_seconds": 120,
  "completion_percentage": 40
}
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440020",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "lesson_id": "550e8400-e29b-41d4-a716-446655440002",
  "watched_seconds": 120,
  "last_position_seconds": 120,
  "completion_percentage": 40,
  "is_completed": false,
  "completed_at": null,
  "last_updated_at": "2026-01-11T10:05:00Z"
}
```

**Note:** Auto-completes at ≥95% completion

**Throttling:** Frontend should throttle to max 1 request per 5 seconds

---

### GET `/progress/lessons/{lesson_id}`

Get lesson progress.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440020",
  "watched_seconds": 120,
  "last_position_seconds": 120,
  "completion_percentage": 40,
  "is_completed": false,
  "completed_at": null
}
```

---

### GET `/progress/courses/{course_id}`

Get course progress summary.

**Authentication:** Required

**Authorization:** Must be enrolled

**Response:** `200 OK`
```json
{
  "course_id": "550e8400-e29b-41d4-a716-446655440001",
  "total_lessons": 15,
  "completed_lessons": 6,
  "completion_percentage": 40,
  "total_duration_seconds": 7200,
  "watched_seconds": 2880
}
```

---

### POST `/progress/lessons/{lesson_id}/complete`

Mark lesson as complete.

**Authentication:** Required

**Authorization:** Must be enrolled AND have ≥95% completion

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440020",
  "is_completed": true,
  "completion_percentage": 100,
  "completed_at": "2026-01-11T10:10:00Z"
}
```

**Errors:**
- `400 Bad Request` - Less than 95% completion
- `403 Forbidden` - Not enrolled

---

## Attachments

### GET `/lessons/{lesson_id}/attachments`

List lesson attachments.

**Authentication:** Optional (shows all if enrolled, empty if not)

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440030",
    "title": "Checklist konfiguracji",
    "file_name": "checklist-konfiguracji.pdf",
    "file_size_bytes": 524288,
    "mime_type": "application/pdf",
    "sort_order": 0,
    "created_at": "2026-01-11T10:00:00Z"
  }
]
```

---

### GET `/attachments/{attachment_id}/download`

Download attachment file.

**Authentication:** Required

**Authorization:** Must be enrolled in course

**Response:** `200 OK`
- Content-Type: application/pdf
- Content-Disposition: attachment; filename="checklist.pdf"
- Binary PDF data

**Errors:**
- `403 Forbidden` - Not enrolled
- `404 Not Found` - Attachment not found

**Example:**
```bash
curl -X GET http://localhost:8001/api/v1/attachments/550e8400-e29b-41d4-a716-446655440030/download \
  --cookie "access_token=eyJ0eXAiOiJKV1Qi..." \
  -o checklist.pdf
```

---

## Gamification

### GET `/gamification/me`

Get my gamification data.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_points": 850,
  "level": 4,
  "points_to_next_level": 150,
  "current_streak": 12,
  "longest_streak": 25,
  "grace_period_available": true,
  "achievements_count": 8,
  "recent_achievements": [
    {
      "achievement": {
        "code": "streak_7_days",
        "title": "Tydzień mocy",
        "description": "7 dni konsekwentnej nauki",
        "icon": "flame",
        "points_reward": 100
      },
      "earned_at": "2026-01-10T10:00:00Z"
    }
  ]
}
```

---

### GET `/gamification/achievements`

List all available achievements.

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440040",
    "code": "streak_7_days",
    "title": "Tydzień mocy",
    "description": "7 dni konsekwentnej nauki",
    "icon": "flame",
    "points_reward": 100,
    "category": "streak",
    "is_active": true
  }
]
```

---

### GET `/gamification/achievements/me`

Get my earned achievements.

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440050",
    "achievement": {
      "code": "first_lesson_completed",
      "title": "Pierwszy krok",
      "description": "Ukończona pierwsza lekcja",
      "icon": "zap",
      "points_reward": 10
    },
    "earned_at": "2026-01-09T15:30:00Z",
    "progress_value": null
  }
]
```

---

## Certificates

### POST `/certificates/courses/{course_id}`

Generate certificate for completed course.

**Authentication:** Required

**Authorization:** Must have completed all lessons in course

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440060",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "course_id": "550e8400-e29b-41d4-a716-446655440001",
  "certificate_code": "EFKT-2026-ABCD1234",
  "issued_at": "2026-01-11T10:00:00Z",
  "file_path": "/uploads/certificates/cert-abc123.pdf"
}
```

**Errors:**
- `400 Bad Request` - Course not completed OR already has certificate
- `403 Forbidden` - Not enrolled

---

### GET `/certificates/me`

Get my certificates.

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440060",
    "course": {
      "title": "Masterclass Low-code",
      "slug": "masterclass-lowcode"
    },
    "certificate_code": "EFKT-2026-ABCD1234",
    "issued_at": "2026-01-11T10:00:00Z"
  }
]
```

---

### GET `/certificates/{certificate_code}/download`

Download certificate PDF.

**Authentication:** Required (must be certificate owner)

**Response:** `200 OK`
- Content-Type: application/pdf
- Content-Disposition: attachment; filename="certificate-EFKT-2026-ABCD1234.pdf"
- Binary PDF data

**Example:**
```bash
curl -X GET http://localhost:8001/api/v1/certificates/EFKT-2026-ABCD1234/download \
  --cookie "access_token=eyJ0eXAiOiJKV1Qi..." \
  -o certificate.pdf
```

---

### GET `/certificates/{certificate_code}/verify`

Verify certificate authenticity.

**Authentication:** NOT required (public endpoint)

**Response:** `200 OK`
```json
{
  "valid": true,
  "certificate_code": "EFKT-2026-ABCD1234",
  "user_name": "John Doe",
  "course_title": "Masterclass Low-code",
  "issued_at": "2026-01-11T10:00:00Z"
}
```

**Errors:**
- `404 Not Found` - Certificate not found
```json
{
  "valid": false,
  "message": "Certificate not found"
}
```

**Example:**
```bash
curl -X GET http://localhost:8001/api/v1/certificates/EFKT-2026-ABCD1234/verify
```

---

## Common Responses

### Success Response

**Status:** `200 OK`, `201 Created`

Body contains the requested resource or confirmation message.

---

### Validation Error

**Status:** `422 Unprocessable Entity`

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

### Authentication Error

**Status:** `401 Unauthorized`

```json
{
  "detail": "Could not validate credentials"
}
```

---

### Authorization Error

**Status:** `403 Forbidden`

```json
{
  "detail": "Not authorized to access this resource"
}
```

---

### Not Found Error

**Status:** `404 Not Found`

```json
{
  "detail": "Resource not found"
}
```

---

### Conflict Error

**Status:** `409 Conflict`

```json
{
  "detail": "Resource already exists"
}
```

---

## Error Codes

| Status Code | Meaning |
|-------------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid request data |
| 401 | Unauthorized - Authentication required or failed |
| 403 | Forbidden - Authenticated but not authorized |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource conflict (e.g., duplicate) |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error - Server error |

---

## Rate Limiting

**Default Limits:**
- Authenticated requests: 1000 requests / hour
- Unauthenticated requests: 100 requests / hour
- Progress updates: 1 request / 5 seconds per lesson (client-side throttling)

**Headers:**
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

---

## Authentication Methods

### Cookie-based (Recommended for web)

```bash
curl -X GET http://localhost:8001/api/v1/auth/me \
  --cookie "access_token=eyJ0eXAiOiJKV1Qi..."
```

### Bearer Token

```bash
curl -X GET http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1Qi..."
```

---

## Pagination

Endpoints that return lists support pagination:

**Query Parameters:**
- `page` (integer, default: 1)
- `per_page` (integer, default: 20, max: 100)

**Response includes:**
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

---

## Versioning

API version is included in URL: `/api/v1/...`

Future versions will use `/api/v2/...` etc.

---

**Last Updated:** 2026-01-11
