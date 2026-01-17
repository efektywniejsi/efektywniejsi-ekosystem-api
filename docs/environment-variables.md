# Environment Variables Documentation

Complete reference for all environment variables used in Efektywniejsi Ekosystem API.

---

## Quick Reference

| Category | Variables | Required |
|----------|-----------|----------|
| Application | ENVIRONMENT, DEBUG, API_VERSION | No |
| Database | DATABASE_URL, DB_POOL_* | Yes (DATABASE_URL) |
| Redis | REDIS_URL, REDIS_PASSWORD | Yes (REDIS_URL) |
| JWT | SECRET_KEY, *_TOKEN_EXPIRE_* | Yes (SECRET_KEY) |
| Frontend | FRONTEND_URL, CORS_ORIGINS | Yes |
| Email | EMAIL_BACKEND, SMTP_* | Yes (EMAIL_BACKEND) |
| Uploads | UPLOAD_DIR, MAX_FILE_SIZE_MB | No |
| Mux | MUX_TOKEN_ID, MUX_TOKEN_SECRET | No |
| Monitoring | SENTRY_DSN, LOG_LEVEL | No |
| Rate Limiting | RATE_LIMIT_* | No |

---

## Application Settings

### ENVIRONMENT

**Description:** Application environment
**Type:** String
**Default:** `development`
**Allowed Values:** `development`, `staging`, `production`
**Required:** No

**Example:**
```env
ENVIRONMENT=production
```

**Usage:**
- Affects logging behavior
- Determines if debug mode is enabled
- Used in error reporting

---

### DEBUG

**Description:** Enable debug mode
**Type:** Boolean
**Default:** `false`
**Allowed Values:** `true`, `false`
**Required:** No

**Example:**
```env
DEBUG=false
```

**⚠️ Warning:** Never set to `true` in production!

**Effects:**
- Enables detailed error traces
- Disables some security features
- Shows internal server details in responses

---

### API_VERSION

**Description:** API version string
**Type:** String
**Default:** `v1`
**Required:** No

**Example:**
```env
API_VERSION=v1
```

---

## Database Configuration

### DATABASE_URL

**Description:** PostgreSQL connection string
**Type:** String (URL)
**Default:** None
**Required:** **Yes**

**Format:**
```
postgresql://[username]:[password]@[host]:[port]/[database]
```

**Examples:**

**Development:**
```env
DATABASE_URL=postgresql://efektywniejsi_user:devpassword123@localhost:5433/efektywniejsi_db
```

**Production (Managed):**
```env
DATABASE_URL=postgresql://admin:StrongPass123!@db-prod.example.com:5432/efektywniejsi_prod?sslmode=require
```

**Notes:**
- Always use SSL in production (`?sslmode=require`)
- Store passwords securely (use secrets management)
- Never commit to version control

---

### DB_POOL_SIZE

**Description:** Database connection pool size
**Type:** Integer
**Default:** `10`
**Range:** 5-50
**Required:** No

**Example:**
```env
DB_POOL_SIZE=20
```

**Recommendations:**
- Development: 5-10
- Production (single instance): 20-30
- Production (multiple instances): Calculate based on total connections available

**Formula:** `(DB max connections) / (number of API instances) - 10 (buffer)`

---

### DB_MAX_OVERFLOW

**Description:** Maximum overflow connections beyond pool size
**Type:** Integer
**Default:** `5`
**Range:** 0-20
**Required:** No

**Example:**
```env
DB_MAX_OVERFLOW=10
```

---

### DB_POOL_TIMEOUT

**Description:** Timeout in seconds for getting connection from pool
**Type:** Integer
**Default:** `30`
**Range:** 10-60
**Required:** No

**Example:**
```env
DB_POOL_TIMEOUT=30
```

---

### DB_POOL_RECYCLE

**Description:** Recycle connections after N seconds (prevents stale connections)
**Type:** Integer
**Default:** `3600` (1 hour)
**Required:** No

**Example:**
```env
DB_POOL_RECYCLE=3600
```

---

## Redis Configuration

### REDIS_URL

**Description:** Redis connection string
**Type:** String (URL)
**Default:** None
**Required:** **Yes**

**Format:**
```
redis://[host]:[port]/[db]
redis://:[password]@[host]:[port]/[db]
```

**Examples:**

**Development:**
```env
REDIS_URL=redis://localhost:6381/0
```

**Production:**
```env
REDIS_URL=redis://:StrongRedisPass123@redis-prod.example.com:6379/0
```

---

### REDIS_PASSWORD

**Description:** Redis password (alternative to URL format)
**Type:** String
**Default:** None
**Required:** No (if password in URL)

**Example:**
```env
REDIS_PASSWORD=StrongRedisPass123
```

---

## JWT & Security

### SECRET_KEY

**Description:** Secret key for JWT signing and other cryptographic operations
**Type:** String
**Default:** None
**Required:** **Yes**
**Minimum Length:** 32 characters
**Recommended Length:** 64 characters

**Generate:**
```bash
# Method 1: OpenSSL
openssl rand -hex 32

# Method 2: Python
python -c "import secrets; print(secrets.token_hex(32))"
```

**Example:**
```env
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

**⚠️ Critical Security Notes:**
- **Never** use default/example values
- **Never** commit to version control
- **Never** share between environments
- Change immediately if exposed
- Use different keys for dev/staging/prod

---

### ACCESS_TOKEN_EXPIRE_MINUTES

**Description:** Access token expiration time in minutes
**Type:** Integer
**Default:** `30`
**Range:** 5-120
**Required:** No

**Example:**
```env
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Recommendations:**
- Development: 60 (easier testing)
- Production: 15-30 (more secure)
- Mobile apps: 60 (better UX)

---

### REFRESH_TOKEN_EXPIRE_DAYS

**Description:** Refresh token expiration time in days
**Type:** Integer
**Default:** `30`
**Range:** 7-90
**Required:** No

**Example:**
```env
REFRESH_TOKEN_EXPIRE_DAYS=30
```

**Recommendations:**
- Standard: 30 days
- High security: 7 days
- Long-lived: 90 days

---

## Frontend Configuration

### FRONTEND_URL

**Description:** Frontend application URL
**Type:** String (URL)
**Default:** None
**Required:** **Yes**

**Examples:**

**Development:**
```env
FRONTEND_URL=http://localhost:5173
```

**Production:**
```env
FRONTEND_URL=https://app.yourdomain.com
```

**Usage:**
- Password reset email links
- CORS validation
- OAuth redirects

---

### CORS_ORIGINS

**Description:** Allowed CORS origins (JSON array)
**Type:** JSON Array of Strings
**Default:** `[]`
**Required:** **Yes**

**Examples:**

**Development:**
```env
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

**Production:**
```env
CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com","https://app.yourdomain.com"]
```

**Notes:**
- Must be valid JSON array
- Include all subdomains that need access
- Do **not** use `*` in production

---

## Email Configuration

### EMAIL_BACKEND

**Description:** Email backend type
**Type:** String
**Default:** `console`
**Allowed Values:** `console`, `smtp`
**Required:** **Yes**

**Examples:**

**Development (logs to console):**
```env
EMAIL_BACKEND=console
```

**Production (sends via SMTP):**
```env
EMAIL_BACKEND=smtp
```

---

### SMTP_HOST

**Description:** SMTP server hostname
**Type:** String
**Default:** None
**Required:** Yes (if EMAIL_BACKEND=smtp)

**Examples:**
```env
# SendGrid
SMTP_HOST=smtp.sendgrid.net

# Gmail
SMTP_HOST=smtp.gmail.com

# AWS SES
SMTP_HOST=email-smtp.us-east-1.amazonaws.com

# Mailgun
SMTP_HOST=smtp.mailgun.org
```

---

### SMTP_PORT

**Description:** SMTP server port
**Type:** Integer
**Default:** `587`
**Common Values:** 587 (TLS), 465 (SSL), 25 (plain)
**Required:** Yes (if EMAIL_BACKEND=smtp)

**Example:**
```env
SMTP_PORT=587
```

---

### SMTP_USER

**Description:** SMTP authentication username
**Type:** String
**Default:** None
**Required:** Yes (if EMAIL_BACKEND=smtp)

**Examples:**

**SendGrid:**
```env
SMTP_USER=apikey
```

**Gmail:**
```env
SMTP_USER=your-email@gmail.com
```

---

### SMTP_PASSWORD

**Description:** SMTP authentication password/API key
**Type:** String
**Default:** None
**Required:** Yes (if EMAIL_BACKEND=smtp)

**Example:**
```env
SMTP_PASSWORD=SG.abc123def456xyz789
```

**Security:**
- Use API keys instead of passwords when possible
- Store securely (secrets manager)
- Rotate periodically

---

### SMTP_FROM_EMAIL

**Description:** "From" email address for outgoing emails
**Type:** String (email)
**Default:** None
**Required:** Yes (if EMAIL_BACKEND=smtp)

**Example:**
```env
SMTP_FROM_EMAIL=noreply@yourdomain.com
```

**Notes:**
- Must be verified with SMTP provider
- Should be a no-reply address
- Must match your domain

---

### SMTP_FROM_NAME

**Description:** "From" display name for outgoing emails
**Type:** String
**Default:** `"Efektywniejsi"`
**Required:** No

**Example:**
```env
SMTP_FROM_NAME="Efektywniejsi Platform"
```

---

### SMTP_USE_TLS

**Description:** Use TLS encryption for SMTP
**Type:** Boolean
**Default:** `true`
**Required:** No

**Example:**
```env
SMTP_USE_TLS=true
```

**Note:** Always use `true` in production

---

## File Upload Configuration

### UPLOAD_DIR

**Description:** Directory for uploaded files (attachments, certificates)
**Type:** String (path)
**Default:** `/app/uploads`
**Required:** No

**Examples:**

**Development:**
```env
UPLOAD_DIR=./uploads
```

**Production (Docker):**
```env
UPLOAD_DIR=/app/uploads
```

**Notes:**
- Must be writable by application user
- Should be backed up regularly
- Consider using S3 for production

---

### MAX_FILE_SIZE_MB

**Description:** Maximum file upload size in megabytes
**Type:** Integer
**Default:** `50`
**Range:** 1-100
**Required:** No

**Example:**
```env
MAX_FILE_SIZE_MB=50
```

**Notes:**
- Also configure nginx `client_max_body_size`
- Larger files = more memory usage
- PDF attachments typically 1-10 MB

---

## Mux Video Configuration

### MUX_TOKEN_ID

**Description:** Mux API token ID
**Type:** String
**Default:** None
**Required:** No (optional feature)

**Example:**
```env
MUX_TOKEN_ID=a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```

**Get From:** https://dashboard.mux.com → Settings → Access Tokens

---

### MUX_TOKEN_SECRET

**Description:** Mux API token secret
**Type:** String
**Default:** None
**Required:** No (if MUX_TOKEN_ID set, then required)

**Example:**
```env
MUX_TOKEN_SECRET=AbCdEfGhIjKlMnOpQrStUvWxYz0123456789
```

**Security:**
- Never expose in logs or errors
- Store in secrets manager
- Rotate periodically

---

## Monitoring & Logging

### SENTRY_DSN

**Description:** Sentry error tracking DSN
**Type:** String (URL)
**Default:** None
**Required:** No

**Example:**
```env
SENTRY_DSN=https://abc123def456@o123456.ingest.sentry.io/7890123
```

**Get From:** https://sentry.io → Project Settings → Client Keys (DSN)

**Benefits:**
- Real-time error tracking
- Performance monitoring
- User session replay
- Release tracking

---

### LOG_LEVEL

**Description:** Logging verbosity level
**Type:** String
**Default:** `INFO`
**Allowed Values:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
**Required:** No

**Examples:**

**Development:**
```env
LOG_LEVEL=DEBUG
```

**Production:**
```env
LOG_LEVEL=INFO
```

**Troubleshooting:**
```env
LOG_LEVEL=DEBUG
```

---

## Rate Limiting

### RATE_LIMIT_ENABLED

**Description:** Enable rate limiting
**Type:** Boolean
**Default:** `true`
**Required:** No

**Example:**
```env
RATE_LIMIT_ENABLED=true
```

---

### RATE_LIMIT_PER_HOUR

**Description:** Maximum requests per hour per user/IP
**Type:** Integer
**Default:** `1000`
**Required:** No

**Example:**
```env
RATE_LIMIT_PER_HOUR=1000
```

**Recommendations:**
- Development: 10000 (unlimited)
- Production: 1000-5000 (based on usage)
- Public endpoints: 100-500

---

## Environment Templates

### Development `.env`

```env
# Application
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_URL=postgresql://efektywniejsi_user:devpassword123@localhost:5433/efektywniejsi_db

# Redis
REDIS_URL=redis://localhost:6381/0

# JWT
SECRET_KEY=dev-key-change-in-production-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# Frontend
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Email (console only)
EMAIL_BACKEND=console

# Uploads
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=50

# Logging
LOG_LEVEL=DEBUG
```

---

### Production `.env`

```env
# Application
ENVIRONMENT=production
DEBUG=false

# Database
DATABASE_URL=postgresql://admin:CHANGE_ME@db-prod.example.com:5432/efektywniejsi_prod?sslmode=require
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://:CHANGE_ME@redis-prod.example.com:6379/0

# JWT (CHANGE ALL THESE!)
SECRET_KEY=GENERATE_STRONG_64_CHAR_KEY_HERE
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Frontend
FRONTEND_URL=https://yourdomain.com
CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]

# Email (SMTP)
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.CHANGE_ME
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME="Efektywniejsi"
SMTP_USE_TLS=true

# Uploads
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE_MB=50

# Mux
MUX_TOKEN_ID=your_mux_token_id
MUX_TOKEN_SECRET=your_mux_token_secret

# Monitoring
SENTRY_DSN=https://YOUR_SENTRY_DSN@sentry.io/PROJECT_ID
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_HOUR=1000
```

---

## Security Best Practices

### 1. Never Commit Secrets

**Bad ❌:**
```bash
git add .env
git commit -m "Add config"
```

**Good ✅:**
```bash
# .gitignore
.env
.env.*
!.env.example
```

---

### 2. Use Secrets Management

**Cloud Providers:**
- AWS Secrets Manager
- Google Cloud Secret Manager
- Azure Key Vault
- HashiCorp Vault

**Example (AWS):**
```bash
# Store secret
aws secretsmanager create-secret \
  --name prod/efektywniejsi/database-url \
  --secret-string "postgresql://..."

# Retrieve in application
import boto3
secret = boto3.client('secretsmanager').get_secret_value(
    SecretId='prod/efektywniejsi/database-url'
)['SecretString']
```

---

### 3. Rotate Secrets Regularly

| Secret | Rotation Frequency |
|--------|-------------------|
| SECRET_KEY | Every 90 days |
| SMTP_PASSWORD | Every 90 days |
| MUX_TOKEN_SECRET | Every 90 days |
| Database passwords | Every 180 days |

---

### 4. Environment Separation

Use completely different values for each environment:

```env
# ❌ Bad - Same key everywhere
SECRET_KEY=abc123

# ✅ Good - Different keys per environment
# dev: SECRET_KEY=dev_key_xyz
# staging: SECRET_KEY=stag_key_abc
# prod: SECRET_KEY=prod_key_def
```

---

### 5. Validate on Startup

**app/core/config.py:**
```python
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str

    @validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters')
        if v == 'changeme' or v == 'your-secret-key':
            raise ValueError('SECRET_KEY must be changed from default')
        return v
```

---

## Troubleshooting

### Environment Variables Not Loading

**Issue:** Variables not recognized

**Solutions:**
```bash
# Check file exists
ls -la .env

# Check file has content
cat .env

# Ensure no BOM (Byte Order Mark)
file .env  # Should show "ASCII text", not "UTF-8 Unicode (with BOM)"

# Load explicitly in Docker
docker-compose --env-file .env.production up
```

---

### Invalid JSON in CORS_ORIGINS

**Issue:** `JSONDecodeError: Expecting value`

**Bad:**
```env
CORS_ORIGINS=[http://localhost:5173]  # ❌ Missing quotes
```

**Good:**
```env
CORS_ORIGINS=["http://localhost:5173"]  # ✅ Valid JSON
```

---

### Database Connection Fails

**Issue:** `psycopg2.OperationalError: could not connect`

**Check:**
```bash
# Test connection
psql "$DATABASE_URL"

# Check format
# ✅ Good: postgresql://user:pass@host:5432/db
# ❌ Bad: postgres://... (use postgresql://)
```

---

## Reference

### All Variables Alphabetically

| Variable | Type | Required | Default |
|----------|------|----------|---------|
| ACCESS_TOKEN_EXPIRE_MINUTES | Integer | No | 30 |
| CORS_ORIGINS | JSON Array | Yes | [] |
| DATABASE_URL | String | Yes | - |
| DB_MAX_OVERFLOW | Integer | No | 5 |
| DB_POOL_RECYCLE | Integer | No | 3600 |
| DB_POOL_SIZE | Integer | No | 10 |
| DB_POOL_TIMEOUT | Integer | No | 30 |
| DEBUG | Boolean | No | false |
| EMAIL_BACKEND | String | Yes | console |
| ENVIRONMENT | String | No | development |
| FRONTEND_URL | String | Yes | - |
| LOG_LEVEL | String | No | INFO |
| MAX_FILE_SIZE_MB | Integer | No | 50 |
| MUX_TOKEN_ID | String | No | - |
| MUX_TOKEN_SECRET | String | No | - |
| RATE_LIMIT_ENABLED | Boolean | No | true |
| RATE_LIMIT_PER_HOUR | Integer | No | 1000 |
| REDIS_PASSWORD | String | No | - |
| REDIS_URL | String | Yes | - |
| REFRESH_TOKEN_EXPIRE_DAYS | Integer | No | 30 |
| SECRET_KEY | String | Yes | - |
| SENTRY_DSN | String | No | - |
| SMTP_FROM_EMAIL | String | Conditional | - |
| SMTP_FROM_NAME | String | No | Efektywniejsi |
| SMTP_HOST | String | Conditional | - |
| SMTP_PASSWORD | String | Conditional | - |
| SMTP_PORT | Integer | Conditional | 587 |
| SMTP_USE_TLS | Boolean | No | true |
| SMTP_USER | String | Conditional | - |
| UPLOAD_DIR | String | No | /app/uploads |

**Conditional** = Required if EMAIL_BACKEND=smtp

---

**Last Updated:** 2026-01-11
