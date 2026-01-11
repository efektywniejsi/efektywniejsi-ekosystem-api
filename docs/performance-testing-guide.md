# Performance Testing Guide

## Przegląd

Ten dokument opisuje testy wydajnościowe dla systemu kursów, szczególnie dla progress tracking i video playback.

---

## Kluczowe Metryki

### API Response Time Targets

| Endpoint | Target | Max Acceptable |
|----------|--------|----------------|
| GET /api/v1/courses | <100ms | 500ms |
| GET /api/v1/lessons/{id} | <150ms | 750ms |
| POST /api/v1/progress/lessons/{id} | <200ms | 1000ms |
| GET /api/v1/gamification/me | <100ms | 500ms |
| POST /api/v1/certificates/courses/{id} | <2000ms | 5000ms |

### Video Progress Updates

**Throttling**: Każde 5 sekund (nie częściej)

**Target**:
- Pojedynczy update: <200ms
- 1000 concurrent users: <1000ms p95

---

## Test Scenarios

### 1. Concurrent Video Watchers

**Scenariusz**: 100 users oglądających wideo jednocześnie

```python
# Locust test example
from locust import HttpUser, task, between

class VideoWatcher(HttpUser):
    wait_time = between(5, 10)  # Symuluje throttling 5s

    @task
    def update_progress(self):
        self.client.post(
            f"/api/v1/progress/lessons/{lesson_id}",
            json={
                "watched_seconds": 60,
                "last_position_seconds": 60,
                "completion_percentage": 20,
            },
            headers={"Cookie": f"access_token={self.token}"},
        )
```

**Kryteria sukcesu**:
- p50 < 200ms
- p95 < 500ms
- p99 < 1000ms
- Error rate < 0.1%

### 2. Course Listing Load

**Scenariusz**: 500 concurrent users browsing courses

```python
class CourseBrowser(HttpUser):
    @task
    def browse_courses(self):
        self.client.get("/api/v1/courses?is_published=true")
```

**Kryteria sukcesu**:
- p50 < 100ms
- p95 < 300ms
- Throughput > 100 req/s

### 3. Enrollment Spike

**Scenariusz**: 200 users enrolling simultaneously

```python
class Enrollee(HttpUser):
    @task
    def enroll(self):
        self.client.post(
            f"/api/v1/courses/{course_id}/enroll",
            headers={"Cookie": f"access_token={self.token}"},
        )
```

**Kryteria sukcesu**:
- No database deadlocks
- All enrollments succeed or fail gracefully
- p95 < 1000ms

---

## Database Query Performance

### Critical Queries to Optimize

#### 1. Course Progress Calculation

```sql
-- Should use composite index: (user_id, lesson_id)
SELECT
    COUNT(*) as total_lessons,
    COUNT(CASE WHEN lp.is_completed THEN 1 END) as completed_lessons
FROM lessons l
LEFT JOIN lesson_progress lp ON l.id = lp.lesson_id AND lp.user_id = :user_id
JOIN modules m ON l.module_id = m.id
WHERE m.course_id = :course_id;
```

**Target**: <50ms

#### 2. User Gamification Data

```sql
-- Should use index on user_id for all tables
SELECT
    up.total_points, up.level,
    us.current_streak, us.longest_streak,
    COUNT(ua.id) as achievements_count
FROM user_points up
LEFT JOIN user_streaks us ON up.user_id = us.user_id
LEFT JOIN user_achievements ua ON up.user_id = ua.user_id
WHERE up.user_id = :user_id;
```

**Target**: <30ms

#### 3. Enrollment Check

```sql
-- Should use composite index: (user_id, course_id)
SELECT id FROM enrollments
WHERE user_id = :user_id AND course_id = :course_id;
```

**Target**: <10ms

---

## Database Indexes Verification

### Required Indexes

```sql
-- Lessons
CREATE INDEX idx_lessons_mux_playback_id ON lessons(mux_playback_id);
CREATE INDEX idx_lessons_module_id ON lessons(module_id);

-- Enrollments
CREATE UNIQUE INDEX idx_enrollments_user_course ON enrollments(user_id, course_id);
CREATE INDEX idx_enrollments_user_id ON enrollments(user_id);

-- Lesson Progress
CREATE UNIQUE INDEX idx_lesson_progress_user_lesson ON lesson_progress(user_id, lesson_id);
CREATE INDEX idx_lesson_progress_user_id ON lesson_progress(user_id);

-- User Achievements
CREATE UNIQUE INDEX idx_user_achievements_user_achievement ON user_achievements(user_id, achievement_id);
CREATE INDEX idx_user_achievements_user_id ON user_achievements(user_id);

-- Points History
CREATE INDEX idx_points_history_user_id ON points_history(user_id);
CREATE INDEX idx_points_history_created_at ON points_history(created_at DESC);
```

### Verify Indexes

```bash
uv run python app/scripts/verify_indexes.py
```

---

## Caching Strategy

### Redis Caching

#### 1. Course List

```python
# Cache key: "courses:published"
# TTL: 10 minutes
# Invalidate on: course publish/unpublish
```

#### 2. User Gamification

```python
# Cache key: f"gamification:{user_id}"
# TTL: 5 minutes
# Invalidate on: progress update, achievement unlock
```

#### 3. Achievement List

```python
# Cache key: "achievements:active"
# TTL: 1 hour
# Invalidate on: achievement create/update
```

---

## Load Testing Tools

### Locust (Rekomendowane)

**Install**:
```bash
pip install locust
```

**Run**:
```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

**Dashboard**: http://localhost:8089

### k6

**Install**:
```bash
brew install k6
```

**Run**:
```bash
k6 run tests/performance/script.js
```

---

## Monitoring

### Key Metrics to Monitor

1. **API Response Time** (p50, p95, p99)
2. **Database Connection Pool** (active, idle, waiting)
3. **Redis Operations** (GET/SET latency)
4. **Memory Usage** (heap, RSS)
5. **CPU Usage** (user, system)

### Tools

- **DataDog** / **New Relic**: Application monitoring
- **Grafana**: Dashboards
- **Prometheus**: Metrics collection
- **Sentry**: Error tracking

---

## Optimization Checklist

### Backend

- [ ] Database indexes verified
- [ ] Query N+1 problems resolved
- [ ] Redis caching implemented
- [ ] Connection pooling configured
- [ ] Background jobs for heavy operations

### Frontend

- [ ] Video player throttles progress updates (5s)
- [ ] Debounce on search inputs
- [ ] Lazy loading for course lists
- [ ] Image optimization (WebP, lazy load)
- [ ] Bundle size < 500KB (gzipped)

### Infrastructure

- [ ] CDN for static assets
- [ ] Database read replicas
- [ ] Horizontal scaling (multiple API instances)
- [ ] Load balancer (nginx/HAProxy)
- [ ] Rate limiting per user/IP

---

## Performance Testing Schedule

### Development

- Run basic load tests before each PR merge
- Target: 100 concurrent users

### Staging

- Weekly full load test (500 concurrent users)
- Monthly stress test (1000+ concurrent users)

### Production

- Continuous monitoring
- Alerts on p95 > thresholds
- Monthly capacity planning review

---

## Bottleneck Investigation

### Slow API Response

1. Check logs for query time
2. Run EXPLAIN ANALYZE on slow queries
3. Check Redis hit rate
4. Profile with py-spy or cProfile

### High Database Load

1. Check active connections
2. Identify long-running queries
3. Review query plans (EXPLAIN)
4. Consider read replicas

### Memory Leaks

1. Profile with memory_profiler
2. Check for circular references
3. Review background job cleanup
4. Monitor container restarts

---

## Sample Locust Test

```python
"""
Performance test for video progress tracking.

Usage:
    locust -f tests/performance/video_progress.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between
import random


class VideoProgressUser(HttpUser):
    wait_time = between(5, 7)  # Simulates 5s throttle

    def on_start(self):
        # Login and get token
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        self.token = response.cookies.get("access_token")

        # Enroll in course
        self.course_id = "..."  # Get from fixtures
        self.lesson_id = "..."  # Get from fixtures

    @task(10)
    def update_progress(self):
        """Update lesson progress (90% of actions)."""
        position = random.randint(10, 300)
        percentage = int((position / 300) * 100)

        self.client.post(
            f"/api/v1/progress/lessons/{self.lesson_id}",
            json={
                "watched_seconds": position,
                "last_position_seconds": position,
                "completion_percentage": percentage,
            },
            cookies={"access_token": self.token},
        )

    @task(1)
    def get_course_progress(self):
        """Get overall course progress (10% of actions)."""
        self.client.get(
            f"/api/v1/progress/courses/{self.course_id}",
            cookies={"access_token": self.token},
        )
```

---

## Wyniki Przykładowych Testów

### Baseline (localhost, no optimizations)

| Metric | Value |
|--------|-------|
| Users | 100 |
| RPS | 45 |
| p50 | 180ms |
| p95 | 450ms |
| p99 | 800ms |
| Errors | 0.2% |

### After Optimization (indexes + caching)

| Metric | Value |
|--------|-------|
| Users | 100 |
| RPS | 120 |
| p50 | 65ms |
| p95 | 150ms |
| p99 | 300ms |
| Errors | 0% |

**Improvement**: 2.7x throughput, 2.8x faster p50

---

## Podsumowanie

✅ Key targets:
- Progress updates: <200ms p95
- Course listing: <100ms p50
- Gamification data: <100ms p50
- Certificate generation: <2s p50

✅ Optimization priorities:
1. Database indexes
2. Redis caching
3. Progress update throttling
4. Connection pooling

✅ Monitoring:
- Continuous metrics collection
- Alerts on threshold breaches
- Weekly performance review
