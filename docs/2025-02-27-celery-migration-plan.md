# Plan migracji: Celery → in-process background tasks

**Data:** 2025-02-27
**Problem:** Celery worker generuje ~75-112K komend Redis (BRPOP) dziennie przy 2 użytkownikach

## Diagnoza

Worker Celery na Fly.io (`efektywniejsi-worker`) ciągle polluje Redis (Upstash) komendą BRPOP co ~1 sekundę, czekając na zadania. Domyślny timeout BRPOP w kombu to ~1s i jest wbudowany w event loop Celery — nie da się go łatwo zwiększyć.

Faktyczny workload: ~5 tasków dziennie. Polling: ~86 400 BRPOP/dzień + heartbeat/eventy.

## Cel

Eliminacja Celery workera. Redis zostaje TYLKO do przechowywania refresh tokenów (~100-500 komend/dzień).

## Stan aktualny — 5 tasków Celery

| Task | Wzorzec | Call sites | Retry | Czas |
|------|---------|-----------|-------|------|
| `send_course_update_notification` | fire-and-forget | 3 (modules.py ×2, admin_lessons.py ×1) | 2×30s | 5-60s |
| `send_announcement_notification` | fire-and-forget | 1 (notifications.py) | 2×30s | 10-60s |
| `send_direct_message_notification` | fire-and-forget | 3 (message_service.py ×3) | 2×30s | 2-5s |
| `generate_sales_page_task` | async polling (AsyncResult) | 3 (sales_page_ai.py) | 1×10s | 5-30s |
| `cleanup_orphaned_files_task` | cron (beat 3:00 AM) + manual | 1+1 (admin_cleanup.py + beat) | 0 | 30-300s |

### Kluczowe obserwacje:
- 4/5 tasków to **fire-and-forget** — nie sprawdza się wyniku
- Tylko AI generation używa **AsyncResult polling** — ale task już zapisuje wynik do DB (`pending_response` w `AiChatSession`), więc AsyncResult jest redundantny
- Cleanup to jedyny cron task (raz dziennie o 3:00)

## Nowe moduły do utworzenia

### `app/core/background.py` — runner dla background tasków

Prosty moduł zastępujący Celery:

- `run_in_background(fn, *args, **kwargs)` — fire-and-forget w daemon thread (zamiennik `.delay()`)
- `submit_tracked_task(fn, *args, **kwargs) → task_id` — z śledzeniem statusu w dict (zamiennik AsyncResult)
- `get_task_status(task_id) → dict` — zamiennik `AsyncResult(task_id)`
- Wbudowany retry z exponential backoff dla notyfikacji

### `app/core/scheduler.py` — zamiennik Celery Beat

Prosty scheduler oparty o `asyncio.sleep()` uruchamiany w lifespan FastAPI:

- Uruchamia cleanup codziennie o 3:00 AM (Europe/Warsaw)
- Zero dodatkowych dependencji

## Fazy migracji

### Faza 1: Fire-and-forget (notyfikacje)

| Plik | Zmiana |
|------|--------|
| `app/notifications/tasks.py` | Usunąć `@celery_app.task`, zmienić na zwykłe funkcje, usunąć `self` param |
| `app/courses/routes/modules.py` (l.149, 306) | `.delay(...)` → `run_in_background(...)` |
| `app/courses/routes/admin_lessons.py` (l.61) | j.w. |
| `app/notifications/routes/notifications.py` (l.45) | `.delay(...)` → `run_in_background(...)` |
| `app/messaging/services/message_service.py` (l.65, 97, 333) | `.delay(...)` → `run_in_background(...)` |

### Faza 2: AI generation (async polling)

| Plik | Zmiana |
|------|--------|
| `app/ai/tasks.py` | Usunąć `@celery_app.task`, zwykła funkcja |
| `app/ai/routes/sales_page_ai.py` | `.delay(...)` → `submit_tracked_task(...)`, `AsyncResult(...)` → `get_task_status(...)` |

### Faza 3: Scheduled cleanup

| Plik | Zmiana |
|------|--------|
| `app/storage/tasks.py` | Usunąć `@celery_app.task`, zwykła funkcja |
| `app/storage/routes/admin_cleanup.py` | `.delay(...)` → `submit_tracked_task(...)` w async_mode |
| `app/main.py` | Dodać scheduler do lifespan |

### Faza 4: Usunięcie Celery

| Plik | Zmiana |
|------|--------|
| `app/core/celery_app.py` | USUNĄĆ |
| `pyproject.toml` | Usunąć `"celery[redis]>=5.4"` |
| `fly.worker.toml` | USUNĄĆ |
| `docker-compose.yml` | Usunąć serwis `worker` |

### Faza 5: Deploy i weryfikacja

1. `fly deploy -a efektywniejsi-api`
2. `fly apps destroy efektywniejsi-worker`
3. Weryfikacja:
   - Logi API: `fly logs -a efektywniejsi-api`
   - Upstash Daily Commands → powinno spaść do ~100-500/dzień
   - Test: AI generation, notyfikacje email, cleanup endpoint

## Szacowany efekt

| Metryka | Przed | Po |
|---------|-------|-----|
| Redis commands/dzień | ~75 000 | ~100-500 |
| Fly.io maszyny | 2 (API + Worker) | 1 (API) |
| Koszt workera | ~$3-5/mies | $0 |
| Zależności Python | celery, kombu, vine, amqp, billiard | usunięte |

## Ryzyka

1. **Restart API = utrata in-flight tasków** — przy 2 użytkownikach i rzadkich taskach, ryzyko minimalne
2. **Długie taski blokują thread** — AI generation (5-30s) w daemon thread nie blokuje event loop FastAPI
3. **Brak persystencji kolejki** — taski dispatched tuż przed crashem API zostaną utracone. Akceptowalne przy obecnej skali
