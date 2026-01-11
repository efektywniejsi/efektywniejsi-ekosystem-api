# Testing Guide - Course System E2E Tests

## Przegląd

Ten dokument opisuje testy end-to-end dla systemu kursów, obejmujące enrollment, progress tracking, gamification i certyfikaty.

---

## Struktura Testów

```
tests/courses/
├── __init__.py
├── conftest.py                    # Test fixtures
├── test_enrollment_flow.py        # Enrollment tests (8 tests)
├── test_progress_tracking.py      # Progress tracking tests (9 tests)
├── test_gamification.py           # Gamification tests (10 tests)
└── test_certificates.py           # Certificate tests (8 tests)
```

**Łącznie: 35 testów E2E**

---

## Test Fixtures

### Podstawowe Fixtures (z `tests/conftest.py`)

- `postgres_container` - PostgreSQL testcontainer
- `redis_container` - Redis testcontainer
- `test_database_url` - URL do testowej bazy
- `test_engine` - SQLAlchemy engine
- `db_session` - Database session z rollback
- `test_client` - AsyncClient dla API
- `test_user` - Test user (role: paid)
- `test_admin` - Admin user (role: admin)
- `test_user_token` - JWT access token dla test_user
- `test_admin_token` - JWT access token dla test_admin

### Course Fixtures (z `tests/courses/conftest.py`)

- `test_course` - Pojedynczy kurs testowy
- `test_module` - Moduł testowy
- `test_lesson` - Lekcja testowa (300s)
- `test_preview_lesson` - Lekcja preview (180s)
- `test_achievement` - Achievement testowy
- `test_enrollment` - Enrollment test_user → test_course
- `test_course_with_modules` - Kompletny kurs (2 moduły, 3 lekcje)

---

## Uruchomienie Testów

### Wszystkie testy courses

```bash
uv run python -m pytest tests/courses/ -v
```

### Pojedynczy plik testowy

```bash
uv run python -m pytest tests/courses/test_enrollment_flow.py -v
```

### Pojedynczy test

```bash
uv run python -m pytest tests/courses/test_enrollment_flow.py::test_enroll_in_course -v
```

### Z coverage

```bash
uv run python -m pytest tests/courses/ --cov=app/courses --cov-report=html
```

### Z output capture (pokazuje printy)

```bash
uv run python -m pytest tests/courses/ -v -s
```

---

## Test Enrollment Flow (8 testów)

### `test_enrollment_flow.py`

#### ✅ test_enroll_in_course
- User może zapisać się na kurs
- Zwraca enrollment z course_id i enrolled_at

#### ✅ test_cannot_enroll_twice
- User nie może zapisać się dwa razy na ten sam kurs
- Zwraca 400 "already enrolled"

#### ✅ test_get_my_enrollments
- User może pobrać listę swoich enrollments
- Zawiera szczegóły kursu (slug, title)

#### ✅ test_enroll_without_auth
- Enrollment wymaga autentykacji
- Zwraca 401 bez tokenu

#### ✅ test_enroll_nonexistent_course
- Enrollment na nieistniejący kurs zwraca 404

#### ✅ test_enrollment_grants_access_to_lessons
- Enrollment daje dostęp do lekcji kursu
- User może pobrać szczegóły lekcji

#### ✅ test_no_enrollment_no_access
- Bez enrollment user nie ma dostępu do lekcji
- Zwraca 403 "not enrolled"

#### ✅ test_preview_lessons_accessible_without_enrollment
- Preview lessons dostępne bez enrollment
- `is_preview: true` lekcje są publiczne

---

## Test Progress Tracking (9 testów)

### `test_progress_tracking.py`

#### ✅ test_update_lesson_progress
- User może aktualizować postęp lekcji
- Zapisuje watched_seconds, last_position, completion_percentage

#### ✅ test_progress_auto_completes_at_95_percent
- Lekcja automatycznie completed przy ≥95%
- `is_completed: true`, `completed_at` ustawiony

#### ✅ test_get_lesson_progress
- User może pobrać swój postęp w lekcji
- Zwraca watched_seconds i completion_percentage

#### ✅ test_mark_lesson_complete
- User może ręcznie oznaczyć lekcję jako completed
- Wymaga ≥95% completion_percentage

#### ✅ test_cannot_mark_complete_without_95_percent
- Nie można oznaczyć completed poniżej 95%
- Zwraca 400 z komunikatem o 95%

#### ✅ test_get_course_progress
- User może pobrać ogólny postęp w kursie
- Zawiera total_lessons, completed_lessons, completion_percentage

#### ✅ test_progress_increments_watched_seconds
- watched_seconds inkrementuje się poprawnie
- Kolejne updaty sumują się

#### ✅ test_progress_without_enrollment_fails
- Nie można aktualizować postępu bez enrollment
- Zwraca 403

#### ✅ test_progress_updates_streak
- Aktualizacja postępu triggeruje streak update
- Daily activity zwiększa streak

---

## Test Gamification (10 testów)

### `test_gamification.py`

#### ✅ test_get_user_gamification_data
- User może pobrać swoje dane gamifikacji
- Zawiera total_points, level, current_streak, longest_streak

#### ✅ test_get_available_achievements
- Lista wszystkich dostępnych achievements
- Zawiera achievements z seed script

#### ✅ test_get_user_achievements
- Lista achievements zdobytych przez usera
- Zawiera earned_at timestamp

#### ✅ test_points_awarded_on_lesson_completion
- Punkty przyznawane przy ukończeniu lekcji
- 10 pts za lesson completion

#### ✅ test_streak_updates_on_activity
- Streak aktualizuje się przy daily activity
- Inkrementuje o 1 jeśli last_activity_date = yesterday

#### ✅ test_streak_resets_after_gap
- Streak resetuje się po >2 dni przerwy
- current_streak = 1, longest_streak zachowany

#### ✅ test_grace_period_preserves_streak
- 24h grace period (2 dni gap) zachowuje streak
- current_streak inkrementuje, grace_period_used_at ustawiony

#### ✅ test_level_up_on_points_threshold
- User level up przy osiągnięciu progu punktów
- Level 1→2 przy 100 pts

#### ✅ test_points_history_tracked
- Historia punktów jest zapisywana
- PointsHistory zawiera points, reason, reference_type

#### ✅ test_achievements_unlock_automatically
- Achievements odblokowują się automatycznie
- Np. "first_lesson_completed" po pierwszej lekcji

---

## Test Certificates (8 testów)

### `test_certificates.py`

#### ✅ test_generate_certificate_after_course_completion
- Certyfikat generuje się po ukończeniu wszystkich lekcji
- Zawiera certificate_code, issued_at

#### ✅ test_cannot_generate_certificate_without_completion
- Nie można wygenerować certyfikatu bez ukończenia
- Zwraca 400 "not completed"

#### ✅ test_get_user_certificates
- User może pobrać listę swoich certyfikatów
- Zawiera certificate_code, course details

#### ✅ test_download_certificate
- User może pobrać PDF certyfikatu
- Content-Type: application/pdf

#### ✅ test_verify_certificate_public
- Publiczna weryfikacja certyfikatu (bez auth)
- Zwraca valid: true/false, course_title

#### ✅ test_verify_invalid_certificate
- Weryfikacja invalid code zwraca 404

#### ✅ test_cannot_generate_duplicate_certificate
- User nie może wygenerować 2x certyfikatu dla tego samego kursu
- Zwraca 400 "already has a certificate"

#### ✅ test_certificate_updates_enrollment
- Generowanie certyfikatu aktualizuje enrollment
- Ustawia completed_at i certificate_issued_at

---

## Testowane Scenariusze E2E

### Scenariusz 1: Nowy User - Complete Flow

1. **Enrollment**: User zapisuje się na kurs
2. **Access**: User ma dostęp do lekcji
3. **Progress**: User ogląda lekcje, postęp się zapisuje
4. **Streak**: Daily activity buduje streak
5. **Completion**: Po 95%+ lekcja auto-complete
6. **Points**: User dostaje 10 pts za każdą lekcję
7. **Achievement**: Unlock "first_lesson_completed"
8. **Certificate**: Po ukończeniu wszystkich → generowanie certyfikatu

### Scenariusz 2: Preview Lessons

1. User (bez enrollment) może oglądać preview lessons
2. User nie może oglądać non-preview lessons bez enrollment
3. Po enrollment user ma dostęp do wszystkich lekcji

### Scenariusz 3: Streak Management

1. **Day 1**: User ogląda lekcję → streak = 1
2. **Day 2**: User ogląda lekcję → streak = 2
3. **Day 3**: Brak aktywności
4. **Day 4**: Brak aktywności (gap = 2 dni)
5. **Day 5**: User wraca → grace period używany → streak = 3
6. **Day 8**: Gap > 2 dni → streak reset → streak = 1

### Scenariusz 4: Gamification Progression

1. User: 0 pts, level 1
2. Ukończenie 10 lekcji → 100 pts → level 2
3. Achievement "streak_7_days" → +100 pts → 200 pts
4. Achievement "first_course_completed" → +100 pts → 300 pts
5. Level 3 at 300 pts

---

## Metryki Testowe

### Coverage Targets

- **Enrollment routes**: 100%
- **Progress routes**: 100%
- **Gamification routes**: 100%
- **Certificate routes**: 100%
- **Services**: ≥90%

### Test Performance

- Single test: <2s
- Suite enrollment: <10s
- Suite progress: <15s
- Suite gamification: <20s
- Suite certificates: <15s
- **Total suite**: <60s (1 minute)

---

## Troubleshooting

### Testcontainers nie startują

**Problem**: `Permission denied` lub `Docker not running`

**Rozwiązanie**:
```bash
# Sprawdź czy Docker jest uruchomiony
docker ps

# Restart Docker Desktop
```

### Tests fail z connection error

**Problem**: `Connection refused` do PostgreSQL/Redis

**Rozwiązanie**:
```bash
# Sprawdź porty testcontainers
docker ps | grep postgres
docker ps | grep redis

# Upewnij się że porty są exposed
```

### Database state issues

**Problem**: Testy fail z "already exists" errors

**Rozwiązanie**:
```bash
# Fixtures używają rollback - każdy test ma czystą bazę
# Jeśli problem persists, sprawdź czy:
# 1. db_session.commit() jest zastąpiony przez flush
# 2. Fixtures nie commitują transakcji
```

### Import errors

**Problem**: `ModuleNotFoundError: No module named 'app'`

**Rozwiązanie**:
```bash
# Uruchom z root directory projektu
cd /path/to/efektywniejsi-ekosystem-api
uv run python -m pytest tests/courses/
```

---

## Best Practices

### 1. Test Isolation
- Każdy test ma własną transakcję (auto-rollback)
- Nie używaj `db_session.commit()` - użyj `flush()`
- Fixtures są idempotentne

### 2. Async Tests
- Wszystkie testy API są async (`@pytest.mark.asyncio`)
- Użyj `await` dla test_client requests

### 3. Naming Convention
- `test_<feature>_<scenario>`
- Np. `test_enroll_in_course`, `test_cannot_enroll_twice`

### 4. Assertions
- Sprawdzaj status codes
- Sprawdzaj response data structure
- Sprawdzaj business logic (streak, points, etc.)

### 5. Test Data
- Użyj fixtures dla test data
- Nie hardcode IDs (użyj relationships)
- Cleanup jest automatyczny (rollback)

---

## Continuous Integration

### GitHub Actions (przykład)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Run tests
        run: uv run python -m pytest tests/courses/ -v --cov=app/courses

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Następne Kroki

### Dodatkowe Testy Do Utworzenia

1. **Integration tests** z rzeczywistym Mux API (mock)
2. **Load tests** dla progress updates (locust/k6)
3. **Frontend E2E tests** (Playwright/Cypress)
4. **API contract tests** (Pact)

### Performance Testing

Zobacz: `/docs/performance-testing-guide.md` (do utworzenia)

---

## Podsumowanie

✅ **35 testów E2E** pokrywających:
- Enrollment flow
- Progress tracking
- Gamification system
- Certificate management

Testy używają:
- ✅ Testcontainers (PostgreSQL, Redis)
- ✅ AsyncClient dla API
- ✅ Fixtures dla test data
- ✅ Automatic rollback

**Gotowe do uruchomienia** po wykonaniu:
```bash
uv sync --extra dev
uv run python -m pytest tests/courses/ -v
```
