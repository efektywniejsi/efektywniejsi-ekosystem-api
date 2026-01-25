# Efektywniejsi Ekosystem API

FastAPI backend for the Efektywniejsi learning platform with authentication, course management, video streaming, gamification, and certificates.

## 🚀 Features

- **Authentication**: JWT-based auth with refresh tokens, password reset
- **Course Management**: Hierarchical courses (Course → Module → Lesson)
- **Video Streaming**: Mux integration for video hosting and playback
- **Progress Tracking**: Granular lesson progress with auto-completion
- **Gamification**: Points, levels, streaks with 24h grace period, achievements
- **Certificates**: Automated PDF certificate generation and verification
- **Attachments**: PDF downloads for lessons (enrollment-gated)
- **Admin Panel**: User management, course CRUD operations

## 🛠️ Tech Stack

- **Backend**: Python 3.12+, FastAPI 0.115.0, uvicorn
- **Database**: PostgreSQL 16, SQLAlchemy 2.0, Alembic migrations
- **Cache**: Redis 7
- **Security**: JWT (python-jose), Argon2 password hashing
- **Video**: Mux for video hosting
- **PDF**: reportlab, Pillow for certificate generation
- **Testing**: pytest, pytest-asyncio, testcontainers

## 📋 Quick Start

### 1. Prerequisites

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Docker Desktop
# https://www.docker.com/products/docker-desktop
```

### 2. Clone & Install

```bash
# Clone repository
git clone <repository-url>
cd efektywniejsi-ekosystem-api

# Install dependencies
uv sync

# Install dev dependencies (for tests)
uv sync --extra dev
```

### 3. Environment Setup

Create `.env` file in project root:

```env
# Database
DATABASE_URL=postgresql://efektywniejsi_user:devpassword123@localhost:5433/efektywniejsi_db

# Redis
REDIS_URL=redis://localhost:6381/0

# JWT
SECRET_KEY=your-secret-key-minimum-32-characters-long-please
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Frontend
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Email (development)
EMAIL_BACKEND=console
# EMAIL_BACKEND=smtp  # For production
# SMTP_HOST=smtp.example.com
# SMTP_PORT=587
# SMTP_USER=noreply@example.com
# SMTP_PASSWORD=your-smtp-password

# Uploads
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE_MB=50

# Mux (optional - for video)
# MUX_TOKEN_ID=your_mux_token_id
# MUX_TOKEN_SECRET=your_mux_token_secret
```

### 4. Start Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Wait for services to be ready (~5 seconds)
sleep 5

# Run database migrations
uv run alembic upgrade head
```

### 5. Seed Data

```bash
# Seed achievements (10 achievements)
uv run python app/scripts/seed_achievements.py

# Seed demo course (1 course, 5 lessons)
uv run python app/scripts/seed_demo_course.py

# Import courses from JSON (optional)
uv run python app/scripts/import_courses.py --file app/scripts/import_courses.json --skip-attachments

# Seed default users (admin + test user)
uv run python -m app.scripts.seeds.seed_users
```

### 6. Start API

```bash
# Development mode (auto-reload)
uv run uvicorn app.main:app --reload --port 8000

# Production mode
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**API Documentation**: http://localhost:8000/docs
**ReDoc**: http://localhost:8000/redoc

---

## 👤 Default Users

After running seed script:

| Email | Password | Role | Description |
|-------|----------|------|-------------|
| admin@efektywniejsi.pl | admin123 | admin | Full admin access |
| user@test.pl | testuser123 | paid | Regular paid user |

---

## 📚 API Endpoints

### Authentication `/api/v1/auth`

```bash
POST   /login         # Login with email/password → JWT tokens
POST   /refresh       # Refresh access token
POST   /logout        # Revoke refresh token
GET    /me            # Get current authenticated user
```

### Password Reset `/api/v1/password`

```bash
POST   /request-reset    # Request password reset email
POST   /reset            # Reset password with token
```

### Admin `/api/v1/admin` (requires admin role)

```bash
POST   /users         # Create new user
GET    /users         # List users (pagination, filters)
PATCH  /users/{id}    # Update user (role, email, password)
```

### Courses `/api/v1/courses`

```bash
GET    /courses                     # List all courses (filters: published, difficulty, category)
GET    /courses/{slug}              # Get course details with modules/lessons
POST   /courses                     # Create course (admin)
PATCH  /courses/{id}                # Update course (admin)
DELETE /courses/{id}                # Delete course (admin)

POST   /courses/{id}/modules        # Add module to course (admin)
PATCH  /modules/{id}                # Update module (admin)
DELETE /modules/{id}                # Delete module (admin)

POST   /modules/{id}/lessons        # Add lesson to module (admin)
PATCH  /lessons/{id}                # Update lesson (admin)
DELETE /lessons/{id}                # Delete lesson (admin)
```

### Enrollments `/api/v1/enrollments`

```bash
POST   /courses/{id}/enroll      # Enroll in course
GET    /enrollments/me            # Get my enrollments
DELETE /courses/{id}/enroll      # Unenroll from course (optional)
```

### Lessons `/api/v1/lessons`

```bash
GET    /lessons/{id}              # Get lesson details (requires enrollment or preview)
GET    /courses/{slug}/lessons    # List all lessons for course
```

### Progress Tracking `/api/v1/progress`

```bash
POST   /progress/lessons/{id}              # Update lesson progress (throttled 5s)
                                            # Body: { watched_seconds, last_position_seconds, completion_percentage }
GET    /progress/lessons/{id}              # Get lesson progress
GET    /progress/courses/{id}              # Get course progress summary
POST   /progress/lessons/{id}/complete     # Mark lesson as complete (requires 95%)
```

### Attachments `/api/v1/attachments`

```bash
GET    /lessons/{id}/attachments           # List lesson attachments
GET    /attachments/{id}/download          # Download attachment (requires enrollment)
POST   /lessons/{id}/attachments           # Upload attachment (admin)
DELETE /attachments/{id}                   # Delete attachment (admin)
```

### Gamification `/api/v1/gamification`

```bash
GET    /gamification/me                    # Get my points, level, streak
GET    /gamification/achievements          # List all achievements
GET    /gamification/achievements/me       # Get my earned achievements
GET    /gamification/leaderboard           # Top users by points (optional)
```

### Certificates `/api/v1/certificates`

```bash
POST   /certificates/courses/{id}          # Generate certificate (requires course completion)
GET    /certificates/me                    # Get my certificates
GET    /certificates/{code}/download       # Download certificate PDF
GET    /certificates/{code}/verify         # Verify certificate (public, no auth)
```

---

## 🗄️ Database

### Migrations

```bash
# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Show current version
uv run alembic current

# Show migration history
uv run alembic history
```

### Schema Overview

**Core Tables:**
- `users` - User accounts
- `courses` - Course catalog
- `modules` - Course modules
- `lessons` - Video lessons
- `enrollments` - User course enrollments
- `lesson_progress` - Granular lesson tracking
- `attachments` - PDF attachments

**Gamification Tables:**
- `achievements` - Achievement definitions
- `user_achievements` - Earned achievements
- `user_points` - User points and level
- `points_history` - Points transaction log
- `user_streaks` - Daily activity streaks

**Certificate Tables:**
- `certificates` - Generated certificates

### Key Indexes

```sql
-- Composite indexes for performance
CREATE UNIQUE INDEX idx_enrollments_user_course ON enrollments(user_id, course_id);
CREATE UNIQUE INDEX idx_lesson_progress_user_lesson ON lesson_progress(user_id, lesson_id);
CREATE UNIQUE INDEX idx_user_achievements_user_achievement ON user_achievements(user_id, achievement_id);

-- Single column indexes
CREATE INDEX idx_lessons_mux_playback_id ON lessons(mux_playback_id);
CREATE INDEX idx_points_history_user_id ON points_history(user_id);
```

---

## 🎮 Gamification System

### Points

- **Lesson Completion**: 10 points
- **Course Completion**: 100 points
- **Achievements**: 50-2000 points (varies)

### Levels

| Level | Points Required |
|-------|-----------------|
| 1 | 0 |
| 2 | 100 |
| 3 | 300 |
| 4 | 600 |
| 5 | 1000 |
| 6 | 1500 |
| 7 | 2100 |
| 8 | 2800 |
| 9 | 3600 |
| 10 | 5000 |

### Streaks

**Definition**: Consecutive days with ≥60s video watched OR ≥1 lesson completed

**Grace Period**: 1 skip allowed per 30 days (2-day gap preserved)

**Achievements**:
- 3 days → 50 pts
- 7 days → 100 pts
- 14 days → 250 pts
- 30 days → 500 pts
- 60 days → 1000 pts
- 100 days → 2000 pts

---

## 🎥 Mux Integration

### Setup

1. Create Mux account: https://mux.com
2. Get API credentials from Settings → Access Tokens
3. Add to `.env`:
   ```env
   MUX_TOKEN_ID=your_token_id
   MUX_TOKEN_SECRET=your_token_secret
   ```

### Upload Videos

**Option 1: Mux Dashboard** (recommended for small batches)
- Upload via https://dashboard.mux.com
- Copy Playback ID and Asset ID

**Option 2: Mux API** (for automation)
```python
import mux_python

configuration = mux_python.Configuration()
configuration.username = "MUX_TOKEN_ID"
configuration.password = "MUX_TOKEN_SECRET"

assets_api = mux_python.AssetsApi(mux_python.ApiClient(configuration))
create_asset_request = mux_python.CreateAssetRequest(
    input=[mux_python.InputSettings(url="https://storage.example.com/video.mp4")],
    playback_policy=[mux_python.PlaybackPolicy.PUBLIC],
)

asset = assets_api.create_asset(create_asset_request).data
print(f"Playback ID: {asset.playback_ids[0].id}")
```

### Update Placeholder IDs

```bash
# List lessons with placeholder IDs
uv run python app/scripts/list_placeholder_lessons.py

# Create mapping file
cp app/scripts/mux_id_mapping.json.template app/scripts/mux_id_mapping.json
# Edit file with real Mux IDs

# Update database (dry-run first)
uv run python app/scripts/update_mux_ids.py --mapping mux_id_mapping.json --dry-run

# Apply updates
uv run python app/scripts/update_mux_ids.py --mapping mux_id_mapping.json
```

**Full Guide**: `/docs/mux-integration-guide.md`

---

## 🧪 Testing

### Run Tests

```bash
# Install dev dependencies
uv sync --extra dev

# Run all tests
uv run python -m pytest tests/ -v

# Run course tests only
uv run python -m pytest tests/courses/ -v

# Run with coverage
uv run python -m pytest tests/courses/ --cov=app/courses --cov-report=html

# Run specific test
uv run python -m pytest tests/courses/test_enrollment_flow.py::test_enroll_in_course -v
```

### Test Coverage

**35 E2E tests** covering:
- ✅ Enrollment flow (8 tests)
- ✅ Progress tracking (9 tests)
- ✅ Gamification (10 tests)
- ✅ Certificates (8 tests)

**Guides**:
- `/docs/testing-guide.md` - Complete testing guide
- `/docs/performance-testing-guide.md` - Performance & load testing

---

## 📦 Scripts

### Data Seeding

```bash
# Seed achievements (10 achievements)
uv run python app/scripts/seed_achievements.py

# Seed demo course
uv run python app/scripts/seed_demo_course.py

# Import courses from JSON
uv run python app/scripts/import_courses.py --file import_courses.json --dry-run
uv run python app/scripts/import_courses.py --file import_courses.json --skip-attachments
```

### Mux Integration

```bash
# List lessons needing Mux IDs
uv run python app/scripts/list_placeholder_lessons.py

# Update Mux IDs from mapping
uv run python app/scripts/update_mux_ids.py --mapping mux_id_mapping.json --dry-run
uv run python app/scripts/update_mux_ids.py --mapping mux_id_mapping.json
```

### Verification

```bash
# Verify demo course
uv run python app/scripts/verify_demo_course.py

# Verify imported courses
uv run python app/scripts/verify_imported_courses.py
```

### Test Data Management

```bash
# Create test enrollments for user@test.pl (dry-run)
uv run python app/scripts/seed_test_enrollments.py

# Create test enrollments (execute)
uv run python app/scripts/seed_test_enrollments.py --execute

# Clear test data for user@test.pl (dry-run)
uv run python app/scripts/clear_test_data.py

# Clear test data (execute)
uv run python app/scripts/clear_test_data.py --execute

# Clear test data for specific user
uv run python app/scripts/clear_test_data.py --user admin@efektywniejsi.pl --execute
```

---

## 🚀 Deployment

### Docker Production

```bash
# Build image
docker build -t efektywniejsi-api:latest .

# Run container
docker run -d \
  --name efektywniejsi-api \
  -p 8000:8000 \
  --env-file .env.production \
  efektywniejsi-api:latest
```

### Environment Variables (Production)

```env
# Database (use production credentials)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Redis
REDIS_URL=redis://redis-host:6379/0

# JWT (CHANGE THESE!)
SECRET_KEY=<generate-strong-random-key-64-chars>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Frontend
FRONTEND_URL=https://yourdomain.com
CORS_ORIGINS=["https://yourdomain.com"]

# Email (SMTP)
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@yourdomain.com
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME="Efektywniejsi"

# Uploads
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE_MB=50

# Mux
MUX_TOKEN_ID=your_production_mux_token_id
MUX_TOKEN_SECRET=your_production_mux_token_secret
```

**Full Guide**: `/docs/deployment-guide.md`

---

## 📖 Documentation

- **API Endpoints**: `/docs/api-endpoints.md` - Complete API reference
- **Testing**: `/docs/testing-guide.md` - E2E testing guide
- **Performance**: `/docs/performance-testing-guide.md` - Load testing & optimization
- **Mux Integration**: `/docs/mux-integration-guide.md` - Video upload & management
- **Sprint 6 Plan**: `/docs/sprint-6-plan.md` - Implementation roadmap

---

## 🏗️ Project Structure

```
efektywniejsi-ekosystem-api/
├── app/
│   ├── auth/                   # Authentication module
│   │   ├── models.py           # User model
│   │   ├── routes/             # Auth endpoints
│   │   └── services/           # Auth business logic
│   ├── courses/                # Course system
│   │   ├── models/             # Course, Module, Lesson, etc.
│   │   ├── routes/             # Course endpoints
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/           # Business logic
│   ├── core/                   # Core utilities
│   │   ├── config.py           # Settings
│   │   ├── security.py         # JWT, hashing
│   │   └── redis.py            # Redis client
│   ├── db/                     # Database
│   │   ├── base.py             # Base model
│   │   └── session.py          # DB session
│   ├── scripts/                # Utility scripts
│   │   ├── seed_achievements.py
│   │   ├── seed_demo_course.py
│   │   ├── import_courses.py
│   │   └── ... (12 total)
│   └── main.py                 # FastAPI app
├── tests/                      # Test suite
│   ├── auth/                   # Auth tests
│   ├── courses/                # Course E2E tests (35 tests)
│   └── conftest.py             # Test fixtures
├── alembic/                    # Database migrations
│   └── versions/               # Migration files
├── docs/                       # Documentation
│   ├── api-endpoints.md
│   ├── testing-guide.md
│   ├── performance-testing-guide.md
│   ├── mux-integration-guide.md
│   ├── deployment-guide.md
│   └── sprint-6-plan.md
├── docker-compose.yml          # Dev services
├── Dockerfile                  # Production image
├── pyproject.toml              # Dependencies
├── .env                        # Environment variables
└── README.md                   # This file
```

---

## 🤝 Contributing

### Code Style

```bash
# Format code
uv run ruff format .

# Lint
uv run ruff check .

# Type check
uv run mypy app/
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## 📝 License

[Add your license here]

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check connection
psql $DATABASE_URL -c "SELECT 1"
```

### Redis Connection Issues

```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli -u $REDIS_URL ping
```

### Migration Conflicts

```bash
# Show current version
uv run alembic current

# Show pending migrations
uv run alembic heads

# Resolve conflicts manually in alembic/versions/
```

---

## 🆘 Support

For issues and questions:
- **GitHub Issues**: [repository-url]/issues
- **Documentation**: `/docs/` directory
- **API Docs**: http://localhost:8000/docs

---

## 🎯 Roadmap

- [x] Authentication system
- [x] Course management
- [x] Video integration (Mux)
- [x] Progress tracking
- [x] Gamification (points, streaks, achievements)
- [x] Certificate generation
- [x] E2E test suite (35 tests)
- [ ] Frontend E2E tests (Playwright)
- [ ] Admin dashboard UI
- [ ] WebSocket notifications
- [ ] Analytics dashboard
- [ ] Mobile app API support

---

**Version**: 1.0.0 (Sprint 6 Complete)
**Last Updated**: 2026-01-11
