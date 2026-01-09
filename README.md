# Efektywniejsi Ekosystem Auth API

FastAPI authentication API for Efektywniejsi Ekosystem with JWT tokens, password reset, and admin user management.

## Features

- JWT authentication (access + refresh tokens)
- 2 user roles: **admin** and **paid**
- Password reset via email
- Admin user management
- PostgreSQL database with Alembic migrations
- Redis for refresh token storage
- Email service abstraction (console/SMTP)

## Tech Stack

- **Python**: 3.12+
- **FastAPI**: 0.115.0
- **PostgreSQL**: 16
- **Redis**: 7
- **SQLAlchemy**: 2.0.35
- **Alembic**: 1.13.3 (migrations)
- **JWT**: python-jose
- **Password hashing**: Argon2
- **Email**: aiosmtplib

## Project Structure

```
efektywniejsi-ekosystem-api/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── core/
│   │   ├── config.py             # Settings
│   │   ├── security.py           # JWT & password hashing
│   │   └── redis.py              # Redis client
│   ├── db/
│   │   ├── session.py            # Database session
│   │   └── base.py               # Base model
│   ├── auth/
│   │   ├── models/user.py        # User model
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── routes/               # API endpoints
│   │   └── services/             # Business logic
│   └── scripts/seeds/
│       └── seed_users.py         # Seed admin user
├── alembic/                      # Database migrations
├── docker-compose.yml            # Docker setup
└── .env                          # Environment variables
```

## Quick Start

### 1. Clone and Setup

```bash
cd /Users/kgarbacinski/coding-projects/efektywniejsi/efektywniejsi-ekosystem-api

# Copy environment variables
cp .env.example .env

# Install dependencies
uv sync
```

### 2. Start Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run migrations
uv run alembic upgrade head

# Seed admin user
uv run python -m app.scripts.seeds.seed_users
```

### 3. Run API

```bash
# Development mode
uv run uvicorn app.main:app --reload --port 8001

# Or with Docker
docker-compose up -d
```

### 4. Access API

- **API**: http://localhost:8001
- **Docs**: http://localhost:8001/docs
- **Health**: http://localhost:8001/health

## API Endpoints

### Authentication (`/api/v1/auth`)

#### `POST /api/v1/auth/login`
Login and get JWT tokens.

**Request:**
```json
{
  "email": "admin@efektywniejsi.pl",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "admin@efektywniejsi.pl",
    "name": "Admin",
    "role": "admin"
  }
}
```

#### `POST /api/v1/auth/refresh`
Refresh access token.

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

#### `POST /api/v1/auth/logout`
Logout and revoke refresh token.

**Headers:** `Authorization: Bearer <access_token>`

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

#### `GET /api/v1/auth/me`
Get current user info.

**Headers:** `Authorization: Bearer <access_token>`

### Password Reset (`/api/v1/password`)

#### `POST /api/v1/password/request-reset`
Request password reset link.

**Request:**
```json
{
  "email": "user@test.pl"
}
```

**Note:** Always returns success message to prevent user enumeration.

#### `POST /api/v1/password/reset`
Reset password with token.

**Request:**
```json
{
  "token": "token-from-email",
  "new_password": "newSecurePassword123"
}
```

### Admin (`/api/v1/admin`) - Requires Admin Role

#### `POST /api/v1/admin/users`
Create a new user.

**Headers:** `Authorization: Bearer <admin_access_token>`

**Request:**
```json
{
  "email": "newuser@test.pl",
  "name": "New User",
  "password": "temporaryPassword123",
  "role": "paid",
  "send_welcome_email": true
}
```

#### `GET /api/v1/admin/users`
List all users with pagination.

**Query Parameters:**
- `skip`: Pagination offset (default: 0)
- `limit`: Max results (default: 100)
- `role`: Filter by role ("admin" or "paid")
- `is_active`: Filter by active status

#### `PATCH /api/v1/admin/users/{user_id}`
Update a user.

**Request:**
```json
{
  "name": "Updated Name",
  "role": "admin",
  "is_active": false
}
```

## Testing with cURL

### 1. Login as Admin

```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@efektywniejsi.pl","password":"admin123"}'

# Save access_token and refresh_token from response
```

### 2. Get Current User

```bash
curl -X GET http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. Create New User (Admin)

```bash
curl -X POST http://localhost:8001/api/v1/admin/users \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "name": "Test User",
    "password": "password123",
    "role": "paid",
    "send_welcome_email": true
  }'
```

### 4. Request Password Reset

```bash
curl -X POST http://localhost:8001/api/v1/password/request-reset \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@example.com"}'

# Check console logs for reset token
```

### 5. Reset Password

```bash
curl -X POST http://localhost:8001/api/v1/password/reset \
  -H "Content-Type: application/json" \
  -d '{
    "token": "TOKEN_FROM_EMAIL",
    "new_password": "newPassword123"
  }'
```

## Configuration

### Environment Variables (`.env`)

```env
# Database
DATABASE_URL=postgresql://efektywniejsi:devpassword123@localhost:5433/efektywniejsi_ekosystem_db

# Redis
REDIS_URL=redis://localhost:6381/0

# JWT
SECRET_KEY=your-secret-key-min-32-characters
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email
EMAIL_BACKEND=console  # "console" or "smtp"
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@efektywniejsi.pl

# Frontend
FRONTEND_URL=http://localhost:5173

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000","http://localhost:3001"]

# API
DEBUG=True
```

## Default Users

After running `seed_users.py`:

| Email | Password | Role |
|-------|----------|------|
| admin@efektywniejsi.pl | admin123 | admin |
| user@test.pl | testuser123 | paid |
| user2@test.pl | testuser123 | paid |

**⚠️ IMPORTANT:** Change default passwords in production!

## Database Migrations

```bash
# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

## Development

### Run Tests (Coming Soon)

```bash
uv run pytest
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type check
uv run mypy app/
```

## Production Deployment

### Security Checklist

- [ ] Change `SECRET_KEY` to 32+ character random string
- [ ] Set `DEBUG=False`
- [ ] Configure real SMTP credentials (`EMAIL_BACKEND=smtp`)
- [ ] Enable HTTPS only
- [ ] Change all default passwords
- [ ] Set up rate limiting (5 login attempts per 15 min)
- [ ] Set up monitoring and logging
- [ ] Regular dependency updates
- [ ] Consider adding CAPTCHA on password reset

### Docker Production

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## Architecture Decisions

- **JWT**: Access tokens (30 min) + refresh tokens (7 days)
- **Redis**: Store refresh token hashes for revocation
- **Argon2**: Memory-hard password hashing
- **Email Abstraction**: Console for dev, SMTP for production
- **No Self-Registration**: Admin creates all user accounts
- **Password Reset**: 1-hour expiry, single-use tokens

## Differences from `platforma-api`

**Shared patterns:**
- Identical JWT structure
- Same Argon2 password hashing
- Redis for refresh tokens
- SQLAlchemy + Alembic
- Role-based authorization

**New features:**
- Password reset via email
- Email service abstraction
- Admin user management (create, list, update)

**Simplifications:**
- No purchases/catalog
- No relationships in User model
- Simpler UserResponse (no purchases)

## Ports

To avoid conflicts with `platforma-api`:
- API: **8001** (instead of 8000)
- PostgreSQL: **5433** (instead of 5432)
- Redis: **6381** (instead of 6380)

## Troubleshooting

### Port already in use
```bash
# Check what's using the port
lsof -ti:8001 | xargs kill -9

# Or change port in docker-compose.yml
```

### Database connection error
```bash
# Ensure PostgreSQL is running
docker-compose ps

# Check logs
docker-compose logs postgres
```

### Redis connection error
```bash
# Ensure Redis is running
docker-compose ps

# Test connection
redis-cli -p 6381 ping
```

## License

Proprietary - Efektywniejsi © 2026

## Support

For issues and questions, contact the development team.
