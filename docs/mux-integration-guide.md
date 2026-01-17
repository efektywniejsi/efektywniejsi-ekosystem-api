# Mux Integration Guide

## Przegląd

Ten dokument opisuje proces integracji wideo z platformą Mux, uploadowania plików wideo oraz mapowania placeholder Mux IDs na rzeczywiste playback IDs.

---

## Krok 1: Setup Mux Account

### 1.1 Utworzenie konta Mux

1. Wejdź na https://mux.com
2. Zarejestruj się lub zaloguj
3. Przejdź do **Settings → Access Tokens**
4. Utwórz nowy token z uprawnieniami:
   - ✅ Mux Video: Full Access
   - ✅ Mux Data: Read

### 1.2 Konfiguracja .env

Dodaj klucze API do `.env`:

```bash
# Mux Configuration
MUX_TOKEN_ID=your_token_id_here
MUX_TOKEN_SECRET=your_token_secret_here
```

**⚠️ WAŻNE**: Nie commituj `.env` do repozytorium!

---

## Krok 2: Upload Wideo do Mux

### Metoda 1: Upload przez Mux Dashboard (Rekomendowane dla małych ilości)

1. Przejdź do https://dashboard.mux.com
2. Kliknij **Video → Assets**
3. Kliknij **Upload a file**
4. Wybierz plik wideo z dysku
5. Poczekaj na przetworzenie (~5-10 min dla HD wideo)
6. Po zakończeniu skopiuj:
   - **Playback ID** (np. `abc123xyz456def789`)
   - **Asset ID** (opcjonalnie, np. `asset-abc-123`)

### Metoda 2: Upload przez Mux API (Dla wielu plików)

**Instalacja Mux Python SDK:**
```bash
pip install mux-python
```

**Przykładowy skrypt upload:**
```python
import mux_python
from mux_python.rest import ApiException

configuration = mux_python.Configuration()
configuration.username = "MUX_TOKEN_ID"
configuration.password = "MUX_TOKEN_SECRET"

# Create API instances
assets_api = mux_python.AssetsApi(mux_python.ApiClient(configuration))

# Upload z URL
create_asset_request = mux_python.CreateAssetRequest(
    input=[mux_python.InputSettings(url="https://storage.example.com/video.mp4")],
    playback_policy=[mux_python.PlaybackPolicy.PUBLIC],
)

try:
    create_asset_response = assets_api.create_asset(create_asset_request)
    asset = create_asset_response.data

    print(f"Asset ID: {asset.id}")
    print(f"Playback ID: {asset.playback_ids[0].id}")
    print(f"Status: {asset.status}")
except ApiException as e:
    print(f"Exception: {e}")
```

### Metoda 3: Direct Upload (Dla dużych plików)

```python
# Utworzenie direct upload URL
upload_api = mux_python.DirectUploadsApi(mux_python.ApiClient(configuration))

create_upload_request = mux_python.CreateUploadRequest(
    new_asset_settings=mux_python.CreateAssetRequest(
        playback_policy=[mux_python.PlaybackPolicy.PUBLIC]
    ),
    cors_origin="https://yourdomain.com"
)

upload = upload_api.create_direct_upload(create_upload_request)
print(f"Upload URL: {upload.data.url}")

# Użyj tego URL do uploadu z frontendu lub curl
# curl -X PUT -H "Content-Type: video/mp4" --upload-file video.mp4 {upload.data.url}
```

---

## Krok 3: Mapowanie Placeholder IDs

### 3.1 Utworzenie pliku mapowania

Utwórz plik `/app/scripts/mux_id_mapping.json`:

```json
{
  "mappings": [
    {
      "placeholder": "TO_BE_REPLACED_001",
      "mux_playback_id": "abc123xyz456def789",
      "mux_asset_id": "asset-abc-123",
      "video_title": "Wprowadzenie do kursu - Masterclass Low-code",
      "duration_seconds": 420
    },
    {
      "placeholder": "TO_BE_REPLACED_002",
      "mux_playback_id": "def456ghi789jkl012",
      "mux_asset_id": "asset-def-456",
      "video_title": "Konfiguracja środowiska n8n",
      "duration_seconds": 960
    },
    {
      "placeholder": "TO_BE_REPLACED_003",
      "mux_playback_id": "ghi789jkl012mno345",
      "mux_asset_id": "asset-ghi-789",
      "video_title": "Webhooks i triggery",
      "duration_seconds": 780
    }
  ]
}
```

**Pola:**
- `placeholder`: Obecny placeholder ID w bazie
- `mux_playback_id`: **Wymagane** - rzeczywisty Mux Playback ID
- `mux_asset_id`: Opcjonalne - Mux Asset ID
- `video_title`: Dla referencji (nie używane w updacie)
- `duration_seconds`: Opcjonalne - rzeczywista długość wideo (jeśli różni się od placeholder)

### 3.2 Pobranie aktualnych placeholder IDs z bazy

```bash
uv run python app/scripts/list_placeholder_lessons.py
```

Output:
```
Lessons with placeholder Mux IDs:
==================================================
[1] TO_BE_REPLACED_001
    Lekcja: Wprowadzenie do kursu
    Kurs: Masterclass Low-code
    Duration: 420s (7m)

[2] TO_BE_REPLACED_002
    Lekcja: Konfiguracja środowiska n8n
    Kurs: Masterclass Low-code
    Duration: 960s (16m)
...
```

---

## Krok 4: Aktualizacja Bazy Danych

### 4.1 Dry-run (walidacja)

Przed rzeczywistą aktualizacją zrób dry-run:

```bash
uv run python app/scripts/update_mux_ids.py --mapping mux_id_mapping.json --dry-run
```

Output:
```
🔍 DRY RUN MODE
============================================================
Loaded 9 mappings from mux_id_mapping.json

[DRY RUN] Would update lesson: Wprowadzenie do kursu
   Old Mux ID: TO_BE_REPLACED_001
   New Mux ID: abc123xyz456def789
   Asset ID:   asset-abc-123

[DRY RUN] Would update lesson: Konfiguracja środowiska n8n
   Old Mux ID: TO_BE_REPLACED_002
   New Mux ID: def456ghi789jkl012
...

SUMMARY:
   Lessons updated: 9
   Lessons skipped: 0
   Errors: 0
```

### 4.2 Faktyczna aktualizacja

Jeśli dry-run wygląda poprawnie, uruchom bez flagi:

```bash
uv run python app/scripts/update_mux_ids.py --mapping mux_id_mapping.json
```

### 4.3 Weryfikacja po aktualizacji

```bash
uv run python app/scripts/list_placeholder_lessons.py
```

Powinien pokazać: **"No lessons with placeholder Mux IDs found"**

---

## Krok 5: Testowanie Wideo Playback

### 5.1 Test przez API

```bash
# Pobierz lekcję
curl http://localhost:8000/api/v1/lessons/{lesson_id} | jq '.mux_playback_id'

# Powinien zwrócić rzeczywisty Mux ID (nie placeholder)
```

### 5.2 Test przez Frontend

1. Wejdź na stronę kursu: `/nauka/masterclass-lowcode`
2. Kliknij w pierwszą lekcję
3. Wideo powinno się załadować i odtwarzać przez Mux Player
4. Sprawdź konsolę - nie powinno być błędów 404 lub Mux errors

### 5.3 Test Mux Playback URL

Otwórz w przeglądarce:
```
https://stream.mux.com/{mux_playback_id}.m3u8
```

Jeśli plik `.m3u8` się ściągnie → Playback ID jest poprawny.

---

## Krok 6: Monitoring & Analytics

### 6.1 Mux Dashboard

Przejdź do **Mux Dashboard → Data**:
- View count per asset
- Watch time
- Quality metrics (buffering, startup time)
- Geographic distribution

### 6.2 Mux Data API (Opcjonalnie)

Jeśli chcesz pokazywać analytics w admin panelu:

```python
import mux_python

data_api = mux_python.MetricsApi(mux_python.ApiClient(configuration))

# Get views for asset
response = data_api.get_metric_timeseries_data(
    metric_id="video-startup-time",
    timeframe=["7:days"],
    filters=["asset_id:asset-abc-123"]
)
```

---

## Troubleshooting

### Problem: "Playback ID not found" w Mux Player

**Przyczyny:**
1. Playback ID jest niepoprawny (literówka)
2. Asset jeszcze się przetwarza (status: `preparing`)
3. Playback policy nie jest `public`

**Rozwiązanie:**
```bash
# Sprawdź status assetu w Mux Dashboard
# Lub przez API:
assets_api.get_asset(asset_id)
# Status powinien być: "ready"
```

### Problem: Wideo nie odtwarza się (403 Forbidden)

**Przyczyny:**
1. Playback policy ustawiony na `signed` zamiast `public`
2. CORS issues (jeśli używasz poddomeny)

**Rozwiązanie:**
```python
# Zmień playback policy na public
assets_api.update_asset_master_access(
    asset_id,
    update_asset_master_access_request=mux_python.UpdateAssetMasterAccessRequest(
        master_access="public"
    )
)
```

### Problem: Stara wersja wideo się odtwarza

**Przyczyny:**
- Browser cache / CDN cache

**Rozwiązanie:**
- Hard refresh (Cmd+Shift+R / Ctrl+Shift+R)
- Wyczyść cache przeglądarki
- Mux CDN cache czyści się automatycznie (~5 minut)

### Problem: Wideo ładuje się bardzo wolno

**Przyczyny:**
1. Asset nie ma odpowiednich renditions (1080p, 720p, 480p)
2. Mux jeszcze przetwarza asset

**Rozwiązanie:**
- Sprawdź `master_access` i `mp4_support` w asset settings
- Poczekaj na pełne przetworzenie (check status)
- Włącz auto-generated subtitles dla lepszego UX

---

## Best Practices

### 1. Naming Convention dla Asset

Używaj opisowych nazw przy uploadzie:
```python
create_asset_request = mux_python.CreateAssetRequest(
    input=[...],
    playback_policy=[mux_python.PlaybackPolicy.PUBLIC],
    passthrough="course:masterclass-lowcode|lesson:wprowadzenie|order:1"
)
```

To pomaga w identyfikacji w Mux Dashboard.

### 2. Video Encoding Settings

**Rekomendowane:**
- Format: MP4 (H.264)
- Resolution: 1080p (1920x1080)
- Bitrate: 5-8 Mbps
- Frame rate: 30 fps
- Audio: AAC, 128 kbps, stereo

Mux automatycznie tworzy adaptive bitrate renditions.

### 3. Backup Original Files

Zawsze zachowaj oryginalne pliki wideo lokalnie lub w S3. Mux nie jest backup storage.

### 4. Cost Optimization

- Usuń stare/nieużywane assety (kosztują storage)
- Używaj `mp4_support: "standard"` zamiast `audio_only` jeśli nie potrzebujesz
- Monitor usage w Mux Dashboard

---

## Appendix: Scripts Reference

### A.1 List Placeholder Lessons

**Plik:** `/app/scripts/list_placeholder_lessons.py`

Lista wszystkich lekcji z placeholder Mux IDs.

### A.2 Update Mux IDs

**Plik:** `/app/scripts/update_mux_ids.py`

Aktualizuje Mux IDs w bazie na podstawie pliku mapowania.

**Parametry:**
- `--mapping` - ścieżka do JSON mapowania (default: `mux_id_mapping.json`)
- `--dry-run` - walidacja bez zmian w bazie

### A.3 Mux Upload Helper

**Plik:** `/app/scripts/mux_upload_helper.py` (opcjonalny)

Helper do batch uploadu wielu plików wideo.

---

## Podsumowanie

1. ✅ Utworzenie konta Mux i pobranie API keys
2. ✅ Upload wideo przez Dashboard lub API
3. ✅ Skopiowanie Playback IDs i Asset IDs
4. ✅ Utworzenie pliku `mux_id_mapping.json`
5. ✅ Dry-run update script
6. ✅ Faktyczna aktualizacja bazy
7. ✅ Weryfikacja przez API i Frontend
8. ✅ Monitoring w Mux Dashboard

Po wykonaniu tych kroków wszystkie lekcje będą miały rzeczywiste Mux IDs i wideo będzie się poprawnie odtwarzać.
