# Efektywniejsi Ekosystem Auth API

FastAPI authentication API with JWT, password reset, and admin user management.

## Tech Stack

- Python 3.12+ / FastAPI 0.115.0 / uvicorn
- PostgreSQL 16 / SQLAlchemy 2.0 / Alembic
- Redis 7
- JWT (python-jose) / Argon2 password hashing

## Quick Start

```bash
# Install dependencies
uv sync

# Start services
docker-compose up -d postgres redis

# Run migrations
uv run alembic upgrade head

# Seed users
uv run python -m app.scripts.seeds.seed_users

# Start API
uv run uvicorn app.main:app --reload --port 8001
```

**API**: http://localhost:8001/docs

## Default Users

| Email | Password | Role |
|-------|----------|------|
| admin@efektywniejsi.pl | admin123 | admin |
| user@test.pl | testuser123 | paid |

## API Endpoints

### Authentication `/api/v1/auth`

```bash
POST   /login     # Login (email, password) -> tokens + user
POST   /refresh   # Refresh access token
POST   /logout    # Revoke refresh token
GET    /me        # Get current user
```

### Password Reset `/api/v1/password`

```bash
POST   /request-reset   # Request reset link (email)
POST   /reset           # Reset password (token, new_password)
```

### Admin `/api/v1/admin` (requires admin role)

```bash
POST   /users           # Create user
GET    /users           # List users (pagination, filters)
PATCH  /users/{id}      # Update user
```

## Configuration

Required in `.env`:

```env
DATABASE_URL=postgresql://efektywniejsi:devpassword123@localhost:5433/efektywniejsi_ekosystem_db
REDIS_URL=redis://localhost:6381/0
SECRET_KEY=your-secret-key-min-32-characters
FRONTEND_URL=http://localhost:5173
EMAIL_BACKEND=console
```

## Database Migrations

```bash
# Create migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head
```

## Ports

- API: 8001
- PostgreSQL: 5433
- Redis: 6381
