"""
Seed script for integrations.

Creates or updates integration records in the database.
Can be run multiple times safely - creates new integrations by slug,
or updates existing ones when run with --update flag.

Usage:
    uv run python app/scripts/seed_integrations.py           # Create only (skip existing)
    uv run python app/scripts/seed_integrations.py --update   # Create + update existing
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session

# Import all models to ensure SQLAlchemy relationships are resolved
import app.db.base  # noqa: F401

from app.db.session import get_db
from app.integrations.models import Integration, IntegrationType


INTEGRATIONS_DATA = [
    # ─────────────────────────────────────────────────────────────
    # AI Category
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "openai",
        "name": "OpenAI",
        "icon": "Brain",
        "category": "AI",
        "description": (
            "Platforma AI oferująca modele GPT-5, GPT-4.1, DALL-E, Whisper i GPT Image. "
            "Idealna do automatyzacji treści, analizy danych, generowania obrazów i asystentów AI."
        ),
        "auth_guide": """## Jak uzyskać klucz API OpenAI

### Krok 1: Utwórz konto
1. Wejdź na [platform.openai.com](https://platform.openai.com)
2. Kliknij **Sign Up** i utwórz konto

### Krok 2: Wygeneruj klucz API
1. Po zalogowaniu przejdź do **Dashboard** → **API Keys**
2. Kliknij **Create new secret key**
3. Wybierz projekt i nadaj nazwę kluczowi
4. Skopiuj klucz natychmiast — nie będzie pokazany ponownie!

### Krok 3: Dodaj środki
1. Przejdź do **Settings** → **Billing**
2. Kliknij **Add payment method** i dodaj kartę
3. Ustaw limit wydatków (Usage limits), aby kontrolować koszty

### Nagłówek autoryzacji
```
Authorization: Bearer sk-...
```

### Dostępne modele (2026)

| Rodzina | Modele | Zastosowanie |
|---------|--------|-------------|
| **GPT-5** | gpt-5, gpt-5-mini, gpt-5-nano | Zaawansowane rozumowanie |
| **GPT-4.1** | gpt-4.1, gpt-4.1-mini, gpt-4.1-nano | Ogólne zastosowania |
| **GPT Image 1** | gpt-image-1 | Generowanie obrazów |
| **Whisper** | whisper-1 | Transkrypcja audio |

### Przykład użycia (curl)
```bash
curl https://api.openai.com/v1/chat/completions \\
  -H "Authorization: Bearer $OPENAI_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4.1",
    "messages": [{"role": "user", "content": "Cześć!"}]
  }'
```

> ⚠️ **Ważne:** Klucz API zaczyna się od `sk-` i należy go trzymać w sekrecie! Nigdy nie umieszczaj go w kodzie frontendowym.
""",
        "official_docs_url": "https://platform.openai.com/docs",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 1,
        "integration_types": ["API", "MCP"],
    },
    {
        "slug": "anthropic",
        "name": "Anthropic Claude",
        "icon": "Brain",
        "category": "AI",
        "description": (
            "Claude — zaawansowany model AI od Anthropic z kontekstem do 1M tokenów. "
            "Znany z bezpieczeństwa, extended thinking i najwyższej jakości kodu."
        ),
        "auth_guide": """## Jak uzyskać klucz API Anthropic

### Krok 1: Utwórz konto
1. Wejdź na [console.anthropic.com](https://console.anthropic.com)
2. Kliknij **Sign Up** i utwórz konto
3. Zweryfikuj adres email

### Krok 2: Wygeneruj klucz API
1. Przejdź do **Settings** → **API Keys**
2. Kliknij **Create Key**
3. Nazwij klucz i skopiuj go (zaczyna się od `sk-ant-`)

### Krok 3: Dodaj środki
1. Przejdź do **Plans & Billing**
2. Dodaj kartę płatniczą
3. Doładuj kredyty (prepaid) lub włącz auto-recharge

### Nagłówek autoryzacji
```
x-api-key: sk-ant-...
anthropic-version: 2023-06-01
```

### Dostępne modele (2026)

| Model | API ID | Kontekst | Cena (in/out za MTok) |
|-------|--------|----------|----------------------|
| **Claude Opus 4.6** | `claude-opus-4-6` | 1M | $5 / $25 |
| **Claude Sonnet 4.6** | `claude-sonnet-4-6` | 1M | $3 / $15 |
| **Claude Haiku 4.5** | `claude-haiku-4-5-20251001` | 200k | $1 / $5 |

### Funkcje zaawansowane
- **Extended Thinking** — głębokie rozumowanie (wszystkie modele 4.5+)
- **Tool Use** — wywoływanie funkcji i narzędzi
- **Vision** — analiza obrazów
- **Batch API** — przetwarzanie wsadowe z 50% rabatem

### Przykład użycia (curl)
```bash
curl https://api.anthropic.com/v1/messages \\
  -H "x-api-key: $ANTHROPIC_API_KEY" \\
  -H "anthropic-version: 2023-06-01" \\
  -H "content-type: application/json" \\
  -d '{
    "model": "claude-sonnet-4-6",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Cześć!"}]
  }'
```

> ⚠️ **Ważne:** Klucz API zaczyna się od `sk-ant-` — trzymaj go w sekrecie!
""",
        "official_docs_url": "https://docs.anthropic.com",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 2,
        "integration_types": ["API", "MCP"],
    },
    {
        "slug": "perplexity",
        "name": "Perplexity AI",
        "icon": "Search",
        "category": "AI",
        "description": "Wyszukiwarka AI łącząca możliwości LLM z dostępem do aktualnych informacji z internetu.",
        "auth_guide": """## Jak uzyskać klucz API Perplexity

### Krok 1: Utwórz konto Pro
1. Wejdź na [perplexity.ai](https://perplexity.ai)
2. Potrzebujesz subskrypcji Pro dla API

### Krok 2: Wygeneruj klucz
1. Przejdź do Settings → API
2. Kliknij **Generate API Key**

### Główne zastosowania
- Wyszukiwanie informacji w czasie rzeczywistym
- Research i analiza trendów
- Fact-checking
""",
        "official_docs_url": "https://docs.perplexity.ai",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 3,
        "integration_types": ["API"],
    },
    # ─────────────────────────────────────────────────────────────
    # CRM Category
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "hubspot",
        "name": "HubSpot",
        "icon": "Users",
        "category": "CRM",
        "description": "Kompleksowa platforma CRM z automatyzacją marketingu, sprzedaży i obsługi klienta.",
        "auth_guide": """## Jak połączyć się z API HubSpot

### Opcja 1: Private App Token (Zalecana dla backend)
1. Wejdź do **Settings** → **Integrations** → **Private Apps**
2. Kliknij **Create a private app**
3. Nadaj nazwę i opis
4. W zakładce **Scopes** wybierz wymagane uprawnienia:
   - `crm.objects.contacts.read/write` — kontakty
   - `crm.objects.deals.read/write` — transakcje
   - `crm.objects.companies.read/write` — firmy
5. Kliknij **Create app** i skopiuj **Access Token**

### Opcja 2: OAuth 2.0 (dla aplikacji użytkowników)
1. Utwórz aplikację na [developers.hubspot.com](https://developers.hubspot.com)
2. W zakładce **Auth** ustaw:
   - **Client ID** i **Client Secret** (wygenerowane automatycznie)
   - **Redirect URL**: `https://twoja-domena.com/oauth/callback`
   - **Scopes**: wybierz wymagane uprawnienia
3. Zaimplementuj flow OAuth 2.0:
   ```
   GET https://app.hubspot.com/oauth/authorize
     ?client_id=YOUR_CLIENT_ID
     &redirect_uri=https://twoja-domena.com/oauth/callback
     &scope=crm.objects.contacts.read
   ```
4. Wymień kod na token:
   ```
   POST https://api.hubapi.com/oauth/v1/token
   ```

### Nagłówek autoryzacji
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Popularne endpointy
- `GET /crm/v3/objects/contacts` — lista kontaktów
- `GET /crm/v3/objects/deals` — transakcje
- `GET /crm/v3/objects/companies` — firmy
- `POST /crm/v3/objects/contacts` — utwórz kontakt

### Rate Limits
- Private Apps: 100 requestów / 10 sekund
- OAuth Apps: 100 requestów / 10 sekund
""",
        "official_docs_url": "https://developers.hubspot.com/docs/api/overview",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 10,
        "integration_types": ["API", "OAuth 2.0"],
    },
    {
        "slug": "pipedrive",
        "name": "Pipedrive",
        "icon": "Users",
        "category": "CRM",
        "description": "CRM zorientowany na sprzedaż z intuicyjnym pipeline'em i automatyzacją procesów.",
        "auth_guide": """## Jak uzyskać klucz API Pipedrive

### Krok 1: Znajdź Personal API Token
1. Zaloguj się do Pipedrive
2. Kliknij swój profil → **Settings**
3. Przejdź do **Personal preferences** → **API**
4. Skopiuj **Your personal API token**

### Krok 2: Użyj w zapytaniach
Dodaj token jako parametr `api_token` lub w nagłówku:
```
Authorization: Bearer YOUR_API_TOKEN
```

### Limity API
- 80 requestów na 2 sekundy (na token)
- Rate limiting zwraca HTTP 429
""",
        "official_docs_url": "https://developers.pipedrive.com/docs/api/v1",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 11,
        "integration_types": ["API", "OAuth 2.0"],
    },
    # ─────────────────────────────────────────────────────────────
    # Automation Category
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "make",
        "name": "Make (Integromat)",
        "icon": "Workflow",
        "category": "Automation",
        "description": "Platforma do tworzenia zaawansowanych automatyzacji z wizualnym edytorem scenariuszy.",
        "auth_guide": """## Jak połączyć Make z innymi serwisami

### Podstawy Make
Make używa **modułów** do łączenia się z różnymi serwisami. Każdy moduł wymaga połączenia (connection).

### Tworzenie połączenia
1. W scenariuszu dodaj moduł (np. Google Sheets)
2. Kliknij **Add** przy Connection
3. Autoryzuj dostęp przez OAuth lub podaj API key

### Webhooks
1. Dodaj moduł **Webhooks** → **Custom webhook**
2. Skopiuj wygenerowany URL
3. Użyj go jako endpoint w innych systemach

### API Make
Możesz też kontrolować Make przez API:
- Endpoint: `https://eu1.make.com/api/v2`
- Autoryzacja: Token w nagłówku `Authorization: Token YOUR_TOKEN`
""",
        "official_docs_url": "https://www.make.com/en/api-documentation",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 20,
        "integration_types": ["API", "OAuth 2.0"],
    },
    {
        "slug": "n8n",
        "name": "n8n",
        "icon": "Workflow",
        "category": "Automation",
        "description": "Open-source platforma automatyzacji z możliwością self-hostingu. Alternatywa dla Zapier i Make.",
        "auth_guide": """## Konfiguracja n8n

### Self-hosted vs Cloud
- **n8n Cloud**: Gotowe rozwiązanie na [n8n.io](https://n8n.io)
- **Self-hosted**: Darmowe, pełna kontrola

### Instalacja Docker
```bash
docker run -it --rm \\
  -p 5678:5678 \\
  -v n8n_data:/home/node/.n8n \\
  n8nio/n8n
```

### Credentials w n8n
1. Przejdź do **Settings** → **Credentials**
2. Kliknij **Add Credential**
3. Wybierz typ (np. HTTP Request, Google, Slack)
4. Wypełnij wymagane pola (API keys, OAuth)

### Webhooks
- Każdy workflow może mieć webhook trigger
- URL: `https://your-n8n.com/webhook/workflow-id`
""",
        "official_docs_url": "https://docs.n8n.io",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 21,
        "integration_types": ["API", "OAuth 2.0"],
    },
    # ─────────────────────────────────────────────────────────────
    # Communication Category
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "slack",
        "name": "Slack",
        "icon": "MessageSquare",
        "category": "Communication",
        "description": "Platforma komunikacji zespołowej z bogatym API do botów, webhooków i integracji OAuth 2.0.",
        "auth_guide": """## Jak utworzyć aplikację Slack

### Krok 1: Utwórz aplikację
1. Wejdź na [api.slack.com/apps](https://api.slack.com/apps)
2. Kliknij **Create New App** → **From scratch**
3. Nazwij aplikację i wybierz workspace

### Krok 2: Skonfiguruj uprawnienia (Bot Token)
1. Przejdź do **OAuth & Permissions**
2. Dodaj **Bot Token Scopes** (np. `chat:write`, `channels:read`)
3. Kliknij **Install to Workspace**
4. Skopiuj **Bot User OAuth Token** (zaczyna się od `xoxb-`)

### Krok 3: OAuth 2.0 (dla dystrybucji)
Jeśli budujesz aplikację dla wielu workspace'ów:
1. W **OAuth & Permissions** dodaj **Redirect URLs**
2. Zaimplementuj flow:
   ```
   GET https://slack.com/oauth/v2/authorize
     ?client_id=YOUR_CLIENT_ID
     &scope=chat:write,channels:read
     &redirect_uri=https://twoja-domena.com/oauth/callback
   ```
3. Wymień kod na token:
   ```
   POST https://slack.com/api/oauth.v2.access
   ```
4. Zapisz `access_token` z odpowiedzi

### Krok 4: Webhooks (proste powiadomienia)
1. **Incoming Webhooks** → Enable
2. **Add New Webhook to Workspace**
3. Wybierz kanał i skopiuj URL
4. Wyślij wiadomość:
   ```bash
   curl -X POST -H 'Content-type: application/json' \\
     --data '{"text":"Wiadomość z integracji!"}' \\
     YOUR_WEBHOOK_URL
   ```

### Popularne scopes
- `chat:write` — wysyłanie wiadomości
- `channels:read` — lista kanałów
- `users:read` — lista użytkowników
- `files:write` — przesyłanie plików
- `reactions:write` — dodawanie reakcji
""",
        "official_docs_url": "https://api.slack.com/docs",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 30,
        "integration_types": ["API", "OAuth 2.0", "MCP"],
    },
    {
        "slug": "discord",
        "name": "Discord",
        "icon": "MessageSquare",
        "category": "Communication",
        "description": "Platforma komunikacji dla społeczności z potężnym API do botów i integracji.",
        "auth_guide": """## Jak utworzyć bota Discord

### Krok 1: Utwórz aplikację
1. Wejdź na [discord.com/developers/applications](https://discord.com/developers/applications)
2. Kliknij **New Application**
3. Nazwij aplikację

### Krok 2: Utwórz bota i uzyskaj token
1. Przejdź do zakładki **Bot**
2. Kliknij **Add Bot** → **Yes, do it!**
3. Kliknij **Reset Token** i skopiuj **Bot Token**
4. Token wygląda jak: `MTIz...abc.XYZ...`

> ⚠️ **Ważne:** Traktuj Bot Token jak hasło! Nigdy nie udostępniaj go publicznie.

### Krok 3: Zaproś bota na serwer
1. Przejdź do **OAuth2** → **URL Generator**
2. Zaznacz scope `bot` i wymagane permissions (np. Send Messages, Read Messages)
3. Skopiuj wygenerowany URL i otwórz w przeglądarce
4. Wybierz serwer i autoryzuj

### Krok 4: Użyj token w kodzie
```python
import discord
client = discord.Client()

@client.event
async def on_ready():
    print(f'Bot zalogowany jako {client.user}')

client.run('YOUR_BOT_TOKEN')
```

### Nagłówek autoryzacji (REST API)
```
Authorization: Bot YOUR_BOT_TOKEN
```

### Webhooks (bez bota)
1. Na serwerze: **Edit Channel** → **Integrations** → **Webhooks**
2. **New Webhook** → skopiuj URL
3. Wyślij wiadomość:
   ```bash
   curl -X POST -H "Content-Type: application/json" \\
     -d '{"content": "Wiadomość z webhoooka!"}' \\
     YOUR_WEBHOOK_URL
   ```
""",
        "official_docs_url": "https://discord.com/developers/docs",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 31,
        "integration_types": ["API", "OAuth 2.0"],
    },
    {
        "slug": "telegram",
        "name": "Telegram Bot",
        "icon": "Send",
        "category": "Communication",
        "description": (
            "Telegram Bot API umożliwia tworzenie botów do automatyzacji, "
            "powiadomień i interakcji z użytkownikami przez Telegram."
        ),
        "auth_guide": """## Jak utworzyć bota Telegram i uzyskać token

### Krok 1: Utwórz bota przez BotFather
1. Otwórz Telegram i wyszukaj **@BotFather**
2. Wyślij komendę `/newbot`
3. Podaj **nazwę wyświetlaną** bota (np. "Mój Asystent")
4. Podaj **username** bota — musi kończyć się na `bot` (np. `moj_asystent_bot`)
5. BotFather zwróci **Bot Token** w formacie:
   ```
   4839574812:AAFD39kkdpWt3ywyRZergyOLMaJhac60qc
   ```

> ⚠️ **Ważne:** Token traktuj jak hasło! Przechowuj w zmiennych środowiskowych.

### Krok 2: Skonfiguruj bota
Przydatne komendy BotFather:
- `/setcommands` — zdefiniuj menu komend bota
- `/setdescription` — ustaw opis bota
- `/mybots` — zarządzaj istniejącymi botami

### Krok 3: Użyj Bot API

**Base URL:** `https://api.telegram.org/bot<TOKEN>/METHOD_NAME`

#### Wysyłanie wiadomości
```bash
curl "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \\
  -d "chat_id=CHAT_ID" \\
  -d "text=Cześć z bota!" \\
  -d "parse_mode=HTML"
```

#### Odbieranie wiadomości (Long Polling)
```bash
curl "https://api.telegram.org/bot$BOT_TOKEN/getUpdates?offset=0&timeout=30"
```

### Krok 4: Webhooks (produkcja)
Zamiast pollingu, użyj webhooków:
```bash
curl -F "url=https://twoja-domena.com/webhook/telegram" \\
  -F "secret_token=TWOJ_SEKRET" \\
  "https://api.telegram.org/bot$BOT_TOKEN/setWebhook"
```

**Wymagania webhooków:**
- **HTTPS** (TLS 1.2+)
- Porty: 443, 80, 88 lub 8443
- Odpowiedź w ciągu 60 sekund

**Weryfikacja:** Telegram wysyła nagłówek `X-Telegram-Bot-Api-Secret-Token` — porównaj go z ustawionym `secret_token`.

#### Sprawdź status webhooka
```bash
curl "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
```

### Popularne metody API
| Metoda | Opis |
|--------|------|
| `sendMessage` | Wyślij wiadomość tekstową |
| `sendPhoto` | Wyślij zdjęcie |
| `sendDocument` | Wyślij plik |
| `getUpdates` | Pobierz aktualizacje (polling) |
| `setWebhook` | Ustaw webhook |
| `getMe` | Informacje o bocie |
""",
        "official_docs_url": "https://core.telegram.org/bots/api",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 32,
        "integration_types": ["API"],
    },
    # ─────────────────────────────────────────────────────────────
    # Data Enrichment Category
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "clearbit",
        "name": "Clearbit",
        "icon": "Database",
        "category": "Data Enrichment",
        "description": "Wzbogacanie danych B2B - informacje o firmach i osobach na podstawie email/domeny.",
        "auth_guide": """## Jak uzyskać klucz API Clearbit

### Krok 1: Utwórz konto
1. Wejdź na [clearbit.com](https://clearbit.com)
2. Zarejestruj się (wymaga służbowego email)

### Krok 2: Znajdź klucz API
1. Zaloguj się do dashboardu
2. Przejdź do **API** w menu
3. Skopiuj **API Key**

### Główne endpointy
- **Person API**: `/v2/people/find?email=...`
- **Company API**: `/v2/companies/find?domain=...`
- **Enrichment API**: `/v2/combined/find?email=...`

### Przykład użycia
```bash
curl https://person.clearbit.com/v2/people/find \\
  -u YOUR_API_KEY: \\
  -d email=user@example.com
```
""",
        "official_docs_url": "https://clearbit.com/docs",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 40,
        "integration_types": ["API"],
    },
    {
        "slug": "apollo",
        "name": "Apollo.io",
        "icon": "Database",
        "category": "Data Enrichment",
        "description": (
            "Platforma sales intelligence z bazą 275M+ kontaktów B2B. "
            "Data Enrichment API do wzbogacania danych o osobach i firmach."
        ),
        "auth_guide": """## Jak uzyskać klucz API Apollo.io

### Krok 1: Utwórz konto
1. Wejdź na [apollo.io](https://www.apollo.io)
2. Zarejestruj się (darmowy plan dostępny, ale pełne API wymaga planu Organization)

### Krok 2: Wygeneruj klucz API
1. Przejdź do **Settings** → **Integrations** → **API Keys**
2. Kliknij **Create new key**
3. Nadaj nazwę i opis
4. Wybierz dostęp do konkretnych endpointów lub zaznacz **Set as master key**
5. Skopiuj klucz natychmiast — wyświetla się tylko raz!

> ⚠️ **Uwaga:** Musisz być adminem, aby tworzyć klucze API.

### Nagłówek autoryzacji
```
X-Api-Key: YOUR_API_KEY
```

### Data Enrichment — główne endpointy

#### Wzbogacanie danych o osobie
```bash
curl -X POST "https://api.apollo.io/api/v1/people/match" \\
  -H "X-Api-Key: $APOLLO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "jan.kowalski@firma.com",
    "reveal_personal_emails": true,
    "reveal_phone_number": true
  }'
```
Zwraca: imię, stanowisko, firma, emaile, telefony, historia zatrudnienia.

#### Wzbogacanie danych o firmie
```bash
curl "https://api.apollo.io/api/v1/organizations/enrich?domain=firma.com" \\
  -H "X-Api-Key: $APOLLO_API_KEY"
```
Zwraca: nazwa firmy, domena, przychody, liczba pracowników, branża, lokalizacja.

#### Bulk Enrichment
- **POST** `/api/v1/people/bulk_match` — do 10 osób na raz
- **POST** `/api/v1/organizations/bulk_enrich` — do 10 firm na raz

### Limity i kredyty
- Enrichment zużywa kredyty z Twojego planu
- Rate limit: ~600 zapytań/godzinę (zależy od planu)
- HTTP 429 — przekroczono limit

### Plany cenowe
| Plan | Cena (rocznie) | API |
|------|---------------|-----|
| Free | $0 | Podstawowe/ograniczone |
| Basic | $49/użytkownik/mies. | Bardzo ograniczone |
| Professional | $79/użytkownik/mies. | Ograniczone |
| Organization | $119/użytkownik/mies. | Pełny dostęp |
""",
        "official_docs_url": "https://docs.apollo.io",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 41,
        "integration_types": ["API"],
    },
    {
        "slug": "lusha",
        "name": "Lusha",
        "icon": "Database",
        "category": "Data Enrichment",
        "description": (
            "Platforma Data Enrichment B2B z API do wzbogacania danych kontaktowych — "
            "emaile, telefony, dane firmowe. Integracja z CRM i narzędziami outreach."
        ),
        "auth_guide": """## Jak uzyskać klucz API Lusha

### Krok 1: Wymagania
- Dostęp do API wymaga planu **Scale** (Enterprise) lub zakupu dodatku API
- Plany Free, Pro i Premium NIE mają dostępu do API

### Krok 2: Wygeneruj klucz
1. Zaloguj się do [dashboard.lusha.com](https://dashboard.lusha.com)
2. Przejdź do **API & Integrations** → **API**
3. Skopiuj **API Key**

> ⚠️ **Ważne:** Klucz API jest współdzielony na poziomie konta. Wygenerowanie nowego unieważnia poprzedni i przerywa aktywne integracje!

### Nagłówek autoryzacji
```
api_key: YOUR_API_KEY
```

### Endpointy Data Enrichment (API v2)

#### Wzbogacanie danych o osobie
```bash
curl -H "api_key: $LUSHA_API_KEY" \\
  "https://api.lusha.com/v2/person?email=jan@firma.com"
```

**Parametry wyszukiwania (wystarczy jeden):**
- `email` — adres email
- `firstName` + `lastName` + `companyName` — imię, nazwisko i firma
- `linkedinUrl` — profil LinkedIn

**Opcjonalne filtry:**
- `?filterBy=phoneNumbers` — zwróć tylko wyniki z telefonami
- `?filterBy=emailAddresses` — zwróć tylko wyniki z emailami

#### Wzbogacanie danych o firmie
```bash
curl -H "api_key: $LUSHA_API_KEY" \\
  "https://api.lusha.com/v2/company?domain=firma.com"
```

#### Bulk Enrichment
```bash
curl -X POST "https://api.lusha.com/person/bulk" \\
  -H "api_key: $LUSHA_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '[{"email": "jan@firma.com"}, {"email": "anna@firma.com"}]'
```
Do 100 kontaktów na raz.

### Kredyty
- 1 kredyt = 1 adres email
- 5 kredytów = 1 numer telefonu

### Rate Limits
| Plan | Na minutę | Na godzinę | Na dzień |
|------|----------|-----------|---------|
| Scale | 300 | 600 | 6000 |
| Professional | 200 | 400 | 2000 |

HTTP 429 — przekroczono limit.
""",
        "official_docs_url": "https://docs.lusha.com",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 42,
        "integration_types": ["API"],
    },
    # ─────────────────────────────────────────────────────────────
    # Database Category
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "airtable",
        "name": "Airtable",
        "icon": "Table",
        "category": "Database",
        "description": (
            "Elastyczna baza danych w formie arkusza kalkulacyjnego z potężnym API. "
            "Obsługuje Personal Access Tokens i OAuth 2.0."
        ),
        "auth_guide": """## Jak uzyskać token API Airtable

### Opcja 1: Personal Access Token (Zalecana)
1. Wejdź na [airtable.com/create/tokens](https://airtable.com/create/tokens)
2. Kliknij **Create new token**
3. Nadaj nazwę tokenowi
4. Wybierz **Scopes** (uprawnienia):
   - `data.records:read` — odczyt rekordów
   - `data.records:write` — zapis rekordów
   - `data.recordComments:read` — odczyt komentarzy
   - `schema.bases:read` — odczyt struktury bazy
   - `schema.bases:write` — modyfikacja struktury
   - `webhook:manage` — zarządzanie webhookami
5. Wybierz **bazy danych**, do których token ma dostęp
6. Kliknij **Create token** i skopiuj go

### Opcja 2: OAuth 2.0 (dla aplikacji)
Dla aplikacji dystrybuowanych do wielu użytkowników:
1. Zarejestruj aplikację w Airtable
2. Zaimplementuj standardowy flow OAuth 2.0

### Nagłówek autoryzacji
```
Authorization: Bearer YOUR_TOKEN
```

### Struktura URL API
```
https://api.airtable.com/v0/{baseId}/{tableName}
```

### Gdzie znaleźć Base ID?
1. Otwórz bazę w Airtable
2. Base ID jest w URL przeglądarki — zaczyna się od `app` (np. `appABC123def456`)

### Przykład: Pobierz rekordy
```bash
curl "https://api.airtable.com/v0/$BASE_ID/Tabela1" \\
  -H "Authorization: Bearer $AIRTABLE_TOKEN"
```

### Przykład: Utwórz rekord
```bash
curl -X POST "https://api.airtable.com/v0/$BASE_ID/Tabela1" \\
  -H "Authorization: Bearer $AIRTABLE_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "records": [
      {"fields": {"Nazwa": "Nowy rekord", "Status": "Aktywny"}}
    ]
  }'
```

### Rate Limits
- 5 requestów na sekundę na bazę
- HTTP 429 przy przekroczeniu
""",
        "official_docs_url": "https://airtable.com/developers/web/api/introduction",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 50,
        "integration_types": ["API", "OAuth 2.0"],
    },
    {
        "slug": "notion",
        "name": "Notion",
        "icon": "FileText",
        "category": "Productivity",
        "description": "All-in-one workspace do notatek, dokumentacji, baz danych i zarządzania projektami.",
        "auth_guide": """## Jak utworzyć integrację Notion

### Krok 1: Utwórz integrację
1. Wejdź na [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Kliknij **New integration**
3. Nazwij integrację i wybierz workspace
4. Skopiuj **Internal Integration Token**

### Krok 2: Połącz z bazą/stroną
1. Otwórz stronę/bazę w Notion
2. Kliknij **...** → **Add connections**
3. Wybierz swoją integrację

### Ważne!
Integracja ma dostęp TYLKO do stron, z którymi została połączona!

### Struktura API
- Endpoint: `https://api.notion.com/v1`
- Nagłówek: `Authorization: Bearer YOUR_TOKEN`
- Nagłówek: `Notion-Version: 2022-06-28`
""",
        "official_docs_url": "https://developers.notion.com",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 51,
        "integration_types": ["API", "OAuth 2.0", "MCP"],
    },
    # ─────────────────────────────────────────────────────────────
    # Productivity Category — Google Workspace
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "google-workspace",
        "name": "Google Workspace",
        "icon": "Globe",
        "category": "Productivity",
        "description": (
            "Kompleksowa integracja z usługami Google: Gmail, Google Sheets, Google Docs, "
            "Google Drive. Autoryzacja przez OAuth 2.0 lub Service Account."
        ),
        "auth_guide": """## Jak skonfigurować Google Workspace OAuth 2.0

### Krok 1: Utwórz projekt w Google Cloud
1. Wejdź na [console.cloud.google.com](https://console.cloud.google.com)
2. Kliknij **Select a project** → **New Project**
3. Nazwij projekt i kliknij **Create**

### Krok 2: Włącz wymagane API
1. Przejdź do **APIs & Services** → **Library**
2. Wyszukaj i włącz potrzebne API:
   - **Gmail API** — wysyłanie i odczyt emaili
   - **Google Sheets API** — operacje na arkuszach
   - **Google Docs API** — tworzenie i edycja dokumentów
   - **Google Drive API** — zarządzanie plikami

### Krok 3: Skonfiguruj OAuth Consent Screen
1. Przejdź do **Google Auth platform** → **Branding**
2. Wybierz typ użytkowników:
   - **Internal** — tylko użytkownicy w Twojej organizacji (nie wymaga weryfikacji)
   - **External** — wszyscy użytkownicy Google (wymaga weryfikacji dla wrażliwych scopes)
3. Wypełnij dane aplikacji i politykę prywatności
4. Dodaj testowych użytkowników (max 100) na czas developmentu

### Krok 4: Utwórz OAuth 2.0 Credentials
1. Przejdź do **Clients** → **Create Client**
2. Wybierz typ: **Web application**
3. Dodaj **Authorized redirect URIs** (np. `https://twoja-domena.com/oauth/callback`)
4. Skopiuj **Client ID** i **Client Secret**

### Flow autoryzacji OAuth 2.0
```
1. Przekieruj użytkownika:
   GET https://accounts.google.com/o/oauth2/v2/auth
     ?client_id=YOUR_CLIENT_ID
     &redirect_uri=https://twoja-domena.com/oauth/callback
     &response_type=code
     &scope=https://www.googleapis.com/auth/gmail.send
            https://www.googleapis.com/auth/spreadsheets
     &access_type=offline

2. Wymień kod na token:
   POST https://oauth2.googleapis.com/token
     client_id=YOUR_CLIENT_ID
     &client_secret=YOUR_CLIENT_SECRET
     &code=AUTH_CODE
     &grant_type=authorization_code
     &redirect_uri=https://twoja-domena.com/oauth/callback
```

### Alternatywa: Service Account (bez udziału użytkownika)
1. **IAM & Admin** → **Service Accounts** → **Create service account**
2. Pobierz plik JSON z kluczem prywatnym
3. W Google Workspace Admin: włącz **Domain-wide Delegation** dla service account
4. Service account może wtedy działać w imieniu dowolnego użytkownika w organizacji

### Scopes według usługi

#### Gmail
| Scope | Opis | Klasyfikacja |
|-------|------|-------------|
| `gmail.send` | Wysyłanie emaili | Wrażliwy |
| `gmail.readonly` | Odczyt emaili | Ograniczony |
| `gmail.modify` | Odczyt, wysyłanie, usuwanie | Ograniczony |
| `gmail.compose` | Tworzenie szkiców i wysyłanie | Ograniczony |
| `gmail.labels` | Zarządzanie etykietami | Niewrażliwy |

#### Google Sheets
| Scope | Opis | Klasyfikacja |
|-------|------|-------------|
| `spreadsheets` | Pełny dostęp do arkuszy | Wrażliwy |
| `spreadsheets.readonly` | Tylko odczyt arkuszy | Wrażliwy |
| `drive.file` | Dostęp do plików utworzonych przez aplikację | Niewrażliwy ✅ |

#### Google Docs
| Scope | Opis | Klasyfikacja |
|-------|------|-------------|
| `documents` | Pełny dostęp do dokumentów | Wrażliwy |
| `documents.readonly` | Tylko odczyt dokumentów | Wrażliwy |

#### Google Drive
| Scope | Opis | Klasyfikacja |
|-------|------|-------------|
| `drive.file` | Pliki utworzone/otwarte przez aplikację | Niewrażliwy ✅ |
| `drive.readonly` | Odczyt wszystkich plików | Ograniczony |
| `drive` | Pełny dostęp do Drive | Ograniczony |

> 💡 **Zalecenie:** Używaj `drive.file` zamiast `drive` lub `spreadsheets` — jest niewrażliwy i nie wymaga dodatkowej weryfikacji przez Google.

> ⚠️ **Uwaga:** Scopes oznaczone jako **Ograniczone** (np. Gmail) wymagają przejścia **audytu bezpieczeństwa Google**, co może zająć kilka tygodni.
""",
        "official_docs_url": "https://developers.google.com/workspace/guides/auth-overview",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 52,
        "integration_types": ["OAuth 2.0"],
    },
    # ─────────────────────────────────────────────────────────────
    # Payments Category
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "stripe",
        "name": "Stripe",
        "icon": "CreditCard",
        "category": "Payments",
        "description": "Globalna platforma płatności online z pełnym API do obsługi transakcji.",
        "auth_guide": """## Jak uzyskać klucze API Stripe

### Krok 1: Utwórz konto
1. Wejdź na [stripe.com](https://stripe.com)
2. Zarejestruj się i zweryfikuj konto

### Krok 2: Znajdź klucze
1. Zaloguj się do Dashboard
2. Przejdź do **Developers** → **API keys**
3. Zobaczysz dwa zestawy kluczy:
   - **Test mode**: Do developmentu (zaczynają się od `sk_test_`)
   - **Live mode**: Do produkcji (zaczynają się od `sk_live_`)

### Typy kluczy
- **Secret Key**: Do operacji po stronie serwera (trzymaj w sekrecie!)
- **Publishable Key**: Do użycia w frontend (bezpieczny do udostępnienia)

### Webhooks
1. **Developers** → **Webhooks**
2. **Add endpoint**
3. Podaj URL i wybierz wydarzenia
4. Skopiuj **Signing secret** do weryfikacji
""",
        "official_docs_url": "https://stripe.com/docs/api",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 60,
        "integration_types": ["API", "OAuth 2.0"],
    },
    # ─────────────────────────────────────────────────────────────
    # Forms Category
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "tally",
        "name": "Tally",
        "icon": "FileText",
        "category": "Forms",
        "description": (
            "Darmowy kreator formularzy z API i webhookami. "
            "Łatwa integracja z n8n, Make i innymi narzędziami automatyzacji."
        ),
        "auth_guide": """## Jak skonfigurować integrację Tally

### Krok 1: Uzyskaj klucz API
1. Zaloguj się do [tally.so](https://tally.so)
2. Przejdź do **Settings** → **API Keys**
3. Kliknij **Create API key**
4. Skopiuj klucz natychmiast — wyświetla się tylko raz!

> 💡 API jest **darmowe** dla wszystkich użytkowników Tally (obecnie w fazie beta).

### Nagłówek autoryzacji
```
Authorization: Bearer YOUR_API_KEY
```

### Rate Limit
- 100 requestów na minutę
- Zalecane: używaj webhooków zamiast odpytywania API

### Krok 2: Skonfiguruj Webhooks

#### Przez interfejs Tally
1. Opublikuj formularz
2. Przejdź do zakładki **Integrations**
3. Kliknij **Connect** obok Webhooks
4. Wklej URL endpointu (np. z n8n)

#### Przez API
```bash
curl -X POST "https://api.tally.so/webhooks" \\
  -H "Authorization: Bearer $TALLY_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://twoja-domena.com/webhook/tally",
    "formId": "FORM_ID"
  }'
```

### Format Webhook Payload
```json
{
  "eventId": "unique-id",
  "eventType": "FORM_RESPONSE",
  "createdAt": "2026-03-18T10:00:00Z",
  "data": {
    "responseId": "resp_id",
    "formId": "form_id",
    "fields": [
      {"key": "question_1", "label": "Imię", "value": "Jan"}
    ]
  }
}
```

### Weryfikacja webhooków (Signing Secret)
Włącz signing secret, potem weryfikuj nagłówek `Tally-Signature`:
```javascript
const crypto = require('crypto');
const signature = crypto
  .createHmac('sha256', signingSecret)
  .update(JSON.stringify(payload))
  .digest('base64');
// Porównaj z nagłówkiem Tally-Signature
```

### Krok 3: Integracja z n8n

#### Natywny trigger (zalecane)
1. W n8n dodaj node **Tally Trigger**
2. Utwórz credential z kluczem API Tally
3. Wybierz formularz z listy
4. Wyślij testową odpowiedź, aby pobrać przykładowe dane

#### Przez Webhook (alternatywa)
1. W n8n dodaj node **Webhook** (POST)
2. Skopiuj wygenerowany URL
3. W Tally: **Integrations** → **Webhooks** → wklej URL n8n

### Osadzanie formularzy
```html
<script src="https://tally.so/widgets/embed.js"></script>
```
Programowo:
```javascript
Tally.openPopup('FORM_ID', {
  hideTitle: true,
  onSubmit: (payload) => console.log('Odpowiedź:', payload)
});
```

### Główne endpointy API
| Metoda | Endpoint | Opis |
|--------|----------|------|
| `GET` | `/forms` | Lista formularzy |
| `GET` | `/forms/{id}` | Szczegóły formularza |
| `GET` | `/forms/{id}/submissions` | Odpowiedzi |
| `POST` | `/webhooks` | Utwórz webhook |
| `GET` | `/webhooks` | Lista webhooków |
| `DELETE` | `/webhooks/{id}` | Usuń webhook |

**Retry policy:** Przy błędzie webhook jest ponawiany 5 razy (5 min, 30 min, 1h, 6h, 24h).
""",
        "official_docs_url": "https://developers.tally.so/api-reference/introduction",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 71,
        "integration_types": ["API"],
    },
    {
        "slug": "typeform",
        "name": "Typeform",
        "icon": "FileText",
        "category": "Forms",
        "description": "Interaktywne formularze i ankiety z pięknym designem i potężnym API.",
        "auth_guide": """## Jak uzyskać token API Typeform

### Krok 1: Wygeneruj Personal Access Token
1. Zaloguj się do Typeform
2. Kliknij profil → **Settings**
3. Przejdź do **Personal tokens**
4. Kliknij **Generate a new token**
5. Wybierz scopes i skopiuj token

### Scopes
- `forms:read` - Odczyt formularzy
- `forms:write` - Tworzenie/edycja formularzy
- `responses:read` - Odczyt odpowiedzi
- `webhooks:read/write` - Zarządzanie webhookami

### Webhooks
1. Otwórz formularz → **Connect** → **Webhooks**
2. Dodaj URL endpointu
3. Każda odpowiedź wyśle POST request
""",
        "official_docs_url": "https://www.typeform.com/developers/",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 70,
        "integration_types": ["API", "OAuth 2.0"],
    },
    # ─────────────────────────────────────────────────────────────
    # Search Category
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "algolia",
        "name": "Algolia",
        "icon": "Search",
        "category": "Search",
        "description": "Błyskawiczny silnik wyszukiwania jako usługa, idealny do e-commerce i aplikacji.",
        "auth_guide": """## Jak uzyskać klucze API Algolia

### Krok 1: Utwórz konto
1. Wejdź na [algolia.com](https://www.algolia.com)
2. Zarejestruj się (darmowy plan do 10k rekordów)

### Krok 2: Utwórz aplikację
1. W dashboardzie kliknij **Create Application**
2. Nazwij aplikację

### Krok 3: Znajdź klucze
1. Przejdź do **Settings** → **API Keys**
2. Zobaczysz:
   - **Application ID**: Identyfikator aplikacji
   - **Search-Only API Key**: Do wyszukiwania (bezpieczny w frontend)
   - **Admin API Key**: Pełny dostęp (tylko backend!)

### Tworzenie indeksu
1. **Indices** → **Create Index**
2. Zaimportuj dane (JSON, CSV, lub przez API)
""",
        "official_docs_url": "https://www.algolia.com/doc/",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 80,
        "integration_types": ["API"],
    },
    # ─────────────────────────────────────────────────────────────
    # Customer Support Category
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "intercom",
        "name": "Intercom",
        "icon": "MessageSquare",
        "category": "Customer Support",
        "description": "Platforma customer engagement z live chat, help desk i automatyzacją.",
        "auth_guide": """## Jak uzyskać Access Token Intercom

### Opcja 1: Access Token (proste)
1. Zaloguj się do Intercom
2. Przejdź do **Settings** → **Developers** → **Developer Hub**
3. Utwórz nową aplikację
4. Skopiuj **Access Token**

### Opcja 2: OAuth 2.0 (dla aplikacji)
1. Zarejestruj aplikację w Developer Hub
2. Skonfiguruj OAuth redirect URLs
3. Zaimplementuj flow autoryzacji

### Główne obiekty API
- `/contacts` - Kontakty
- `/conversations` - Konwersacje
- `/tickets` - Tickety
- `/articles` - Artykuły Help Center

### Rate Limits
- 1000 requests/minute dla większości endpointów
""",
        "official_docs_url": "https://developers.intercom.com/docs",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 90,
        "integration_types": ["API", "OAuth 2.0"],
    },
    {
        "slug": "zendesk",
        "name": "Zendesk",
        "icon": "MessageSquare",
        "category": "Customer Support",
        "description": "Kompleksowa platforma obsługi klienta z ticketingiem i bazą wiedzy.",
        "auth_guide": """## Jak uzyskać dostęp do API Zendesk

### Opcja 1: API Token
1. Zaloguj się jako admin
2. **Admin** → **Channels** → **API**
3. Włącz **Token Access**
4. **Add API Token**
5. Skopiuj token

### Używanie tokenu
Autoryzacja: `{email}/token:{api_token}` zakodowane w Base64
```
Authorization: Basic base64({email}/token:{token})
```

### Opcja 2: OAuth 2.0
1. **Admin** → **Apps and integrations** → **APIs** → **Zendesk API**
2. **OAuth Clients** → **Add OAuth client**
3. Skonfiguruj redirect URLs

### Struktura URL
```
https://{subdomain}.zendesk.com/api/v2/{resource}
```
""",
        "official_docs_url": "https://developer.zendesk.com/api-reference/",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 91,
        "integration_types": ["API", "OAuth 2.0"],
    },
    # ─────────────────────────────────────────────────────────────
    # Tools Category
    # ─────────────────────────────────────────────────────────────
    {
        "slug": "github",
        "name": "GitHub",
        "icon": "Code",
        "category": "Tools",
        "description": "Platforma do hostingu kodu z Git, CI/CD i zarządzania projektami.",
        "auth_guide": """## Jak uzyskać token GitHub

### Personal Access Token (Classic)
1. Wejdź na [github.com/settings/tokens](https://github.com/settings/tokens)
2. **Generate new token** → **Classic**
3. Wybierz scopes:
   - `repo` - Dostęp do repozytoriów
   - `workflow` - GitHub Actions
   - `read:org` - Organizacje
4. Skopiuj token

### Fine-grained Personal Access Token (Nowy)
1. **Generate new token** → **Fine-grained**
2. Wybierz repozytoria
3. Ustaw szczegółowe uprawnienia
4. Skopiuj token

### GitHub App (dla integracji)
1. **Settings** → **Developer settings** → **GitHub Apps**
2. **New GitHub App**
3. Skonfiguruj uprawnienia i webhooks
4. Zainstaluj na repozytoriach
""",
        "official_docs_url": "https://docs.github.com/en/rest",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 100,
        "integration_types": ["API", "OAuth 2.0", "MCP"],
    },
    {
        "slug": "google-sheets",
        "name": "Google Sheets",
        "icon": "Table",
        "category": "Tools",
        "description": "Arkusze kalkulacyjne w chmurze z potężnym API do automatyzacji.",
        "auth_guide": """## Jak uzyskać dostęp do Google Sheets API

### Krok 1: Utwórz projekt Google Cloud
1. Wejdź na [console.cloud.google.com](https://console.cloud.google.com)
2. Utwórz nowy projekt

### Krok 2: Włącz API
1. **APIs & Services** → **Enable APIs**
2. Wyszukaj i włącz **Google Sheets API**
3. Włącz też **Google Drive API** (do tworzenia arkuszy)

### Krok 3: Utwórz credentials

#### Dla serwera (Service Account):
1. **Credentials** → **Create Credentials** → **Service Account**
2. Pobierz plik JSON z kluczem
3. Udostępnij arkusz emailowi service account

#### Dla aplikacji użytkownika (OAuth 2.0):
1. **Create Credentials** → **OAuth client ID**
2. Skonfiguruj consent screen
3. Pobierz client ID i secret

> 💡 Patrz integracja **Google Workspace** po szczegółowy opis OAuth 2.0 i scopes.

### Struktura URL
```
https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}
```
""",
        "official_docs_url": "https://developers.google.com/sheets/api",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 101,
        "integration_types": ["API", "OAuth 2.0", "MCP"],
    },
]


def _update_integration(db: Session, existing: Integration, data: dict) -> bool:
    """Update an existing integration with new data. Returns True if updated."""
    changed = False
    update_fields = [
        "name", "icon", "category", "description", "auth_guide",
        "official_docs_url", "video_tutorial_url", "is_published", "sort_order",
    ]

    for field in update_fields:
        if field in data:
            new_val = str(data[field]) if data[field] is not None else None
            old_val = getattr(existing, field)
            if field == "official_docs_url" and old_val is not None:
                old_val = str(old_val)
            if new_val != old_val:
                setattr(existing, field, data[field])
                changed = True

    # Update integration types
    new_types = set(data.get("integration_types", []))
    current_types = {t.type_name for t in existing.integration_types}

    if new_types != current_types:
        # Remove old types
        for t in list(existing.integration_types):
            if t.type_name not in new_types:
                db.delete(t)
        # Add new types
        for type_name in new_types - current_types:
            db.add(IntegrationType(integration_id=existing.id, type_name=type_name))
        changed = True

    return changed


def seed_integrations(db: Session, *, update_existing: bool = False) -> None:
    """Seed integrations into the database."""
    created_count = 0
    updated_count = 0
    skipped_count = 0

    for data in INTEGRATIONS_DATA:
        # Check if exists
        existing = db.query(Integration).filter(Integration.slug == data["slug"]).first()

        if existing:
            if update_existing:
                if _update_integration(db, existing, data):
                    print(f"🔄 Updated: {data['slug']} ({data['name']})")
                    updated_count += 1
                else:
                    print(f"⏭️  No changes: {data['slug']}")
                    skipped_count += 1
            else:
                print(f"⏭️  Skipping existing: {data['slug']}")
                skipped_count += 1
            continue

        # Extract integration_types before creating Integration
        integration_types = data.pop("integration_types", [])

        # Create integration
        integration = Integration(**data)
        db.add(integration)
        db.flush()

        # Add integration types
        for type_name in integration_types:
            db.add(IntegrationType(integration_id=integration.id, type_name=type_name))

        print(f"✅ Created: {data['slug']} ({data['name']})")
        created_count += 1

        # Restore for next iteration (in case of error/retry)
        data["integration_types"] = integration_types

    db.commit()

    print("\n" + "=" * 60)
    print("Seeding complete!")
    print(f"   Created: {created_count}")
    if update_existing:
        print(f"   Updated: {updated_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total:   {created_count + updated_count + skipped_count}")
    print("=" * 60)


def main() -> None:
    """Main entry point."""
    update_existing = "--update" in sys.argv

    print("=" * 60)
    print("Integration Seeding Script")
    if update_existing:
        print("Mode: CREATE + UPDATE existing")
    else:
        print("Mode: CREATE only (use --update to update existing)")
    print("=" * 60)
    print()

    db = next(get_db())
    try:
        seed_integrations(db, update_existing=update_existing)
    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
