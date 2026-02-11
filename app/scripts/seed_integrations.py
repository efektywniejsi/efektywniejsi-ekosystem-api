"""
Seed script for integrations.

Creates sample integration records in the database.
Can be run multiple times - skips existing integrations by slug.

Usage:
    uv run python app/scripts/seed_integrations.py
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
        "description": "Platforma AI oferująca modele GPT-4, DALL-E i Whisper. Idealna do automatyzacji treści, analizy danych i asystentów AI.",
        "auth_guide": """## Jak uzyskać klucz API OpenAI

### Krok 1: Utwórz konto
1. Wejdź na [platform.openai.com](https://platform.openai.com)
2. Kliknij "Sign Up" i utwórz konto

### Krok 2: Wygeneruj klucz API
1. Po zalogowaniu przejdź do **API Keys** w menu
2. Kliknij **Create new secret key**
3. Nazwij klucz i skopiuj go natychmiast (nie będzie pokazany ponownie!)

### Krok 3: Dodaj środki
1. Przejdź do **Billing** → **Add payment method**
2. Dodaj kartę i ustaw limit wydatków

> ⚠️ **Ważne:** Klucz API zaczyna się od `sk-` i należy go trzymać w sekrecie!
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
        "description": "Claude - zaawansowany model AI od Anthropic, znany z bezpieczeństwa i długiego kontekstu (200k tokenów).",
        "auth_guide": """## Jak uzyskać klucz API Anthropic

### Krok 1: Uzyskaj dostęp
1. Wejdź na [console.anthropic.com](https://console.anthropic.com)
2. Utwórz konto lub zaloguj się

### Krok 2: Wygeneruj klucz
1. Przejdź do **API Keys**
2. Kliknij **Create Key**
3. Skopiuj klucz (zaczyna się od `sk-ant-`)

### Modele dostępne
- `claude-3-opus-20240229` - Najbardziej zaawansowany
- `claude-3-sonnet-20240229` - Balans jakości i szybkości
- `claude-3-haiku-20240307` - Najszybszy i najtańszy
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
        "auth_guide": """## Jak uzyskać klucz API HubSpot

### Opcja 1: Private App (Zalecana)
1. Wejdź do **Settings** → **Integrations** → **Private Apps**
2. Kliknij **Create a private app**
3. Nadaj nazwę i wybierz wymagane uprawnienia (scopes)
4. Skopiuj **Access Token**

### Opcja 2: OAuth 2.0
1. Utwórz aplikację w **App Marketplace**
2. Skonfiguruj OAuth flow
3. Użytkownik autoryzuje dostęp

### Popularne endpointy
- `/crm/v3/objects/contacts` - Kontakty
- `/crm/v3/objects/deals` - Transakcje
- `/crm/v3/objects/companies` - Firmy
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
        "description": "Platforma komunikacji zespołowej z bogatym API do botów i integracji.",
        "auth_guide": """## Jak utworzyć aplikację Slack

### Krok 1: Utwórz aplikację
1. Wejdź na [api.slack.com/apps](https://api.slack.com/apps)
2. Kliknij **Create New App** → **From scratch**
3. Nazwij aplikację i wybierz workspace

### Krok 2: Skonfiguruj uprawnienia
1. Przejdź do **OAuth & Permissions**
2. Dodaj **Bot Token Scopes** (np. `chat:write`, `channels:read`)
3. Kliknij **Install to Workspace**
4. Skopiuj **Bot User OAuth Token** (zaczyna się od `xoxb-`)

### Krok 3: Webhooks (opcjonalnie)
1. **Incoming Webhooks** → Enable
2. **Add New Webhook to Workspace**
3. Wybierz kanał i skopiuj URL

### Popularne scopes
- `chat:write` - Wysyłanie wiadomości
- `channels:read` - Lista kanałów
- `users:read` - Lista użytkowników
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
        "description": "Platforma komunikacji dla społeczności z potężnym API do botów.",
        "auth_guide": """## Jak utworzyć bota Discord

### Krok 1: Utwórz aplikację
1. Wejdź na [discord.com/developers/applications](https://discord.com/developers/applications)
2. Kliknij **New Application**
3. Nazwij aplikację

### Krok 2: Utwórz bota
1. Przejdź do zakładki **Bot**
2. Kliknij **Add Bot**
3. Skopiuj **Token** (Reset Token jeśli nie widzisz)

### Krok 3: Zaproś bota na serwer
1. Przejdź do **OAuth2** → **URL Generator**
2. Zaznacz scope `bot` i wymagane permissions
3. Skopiuj URL i otwórz w przeglądarce
4. Wybierz serwer

### Webhooks (prostsze)
1. Na serwerze: **Edit Channel** → **Integrations** → **Webhooks**
2. **New Webhook** → skopiuj URL
""",
        "official_docs_url": "https://discord.com/developers/docs",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 31,
        "integration_types": ["API", "OAuth 2.0"],
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
        "description": "Platforma sales intelligence z bazą 275M+ kontaktów B2B i narzędziami outreach.",
        "auth_guide": """## Jak uzyskać klucz API Apollo

### Krok 1: Utwórz konto
1. Wejdź na [apollo.io](https://www.apollo.io)
2. Zarejestruj się (darmowy plan dostępny)

### Krok 2: Wygeneruj klucz
1. Kliknij swój profil → **Settings**
2. Przejdź do **Integrations** → **API Keys**
3. Kliknij **Create API Key**
4. Skopiuj klucz

### Popularne endpointy
- `/v1/people/match` - Wyszukiwanie osób
- `/v1/organizations/enrich` - Dane firmy
- `/v1/email_accounts` - Zarządzanie kontami email

### Limity
- Darmowy plan: 50 kredytów/miesiąc
- Płatne plany: więcej kredytów i dostęp do pełnego API
""",
        "official_docs_url": "https://apolloio.github.io/apollo-api-docs/",
        "video_tutorial_url": None,
        "is_published": True,
        "sort_order": 41,
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
        "description": "Elastyczna baza danych w formie arkusza kalkulacyjnego z potężnym API.",
        "auth_guide": """## Jak uzyskać token API Airtable

### Opcja 1: Personal Access Token (Zalecana)
1. Wejdź na [airtable.com/create/tokens](https://airtable.com/create/tokens)
2. Kliknij **Create new token**
3. Wybierz scopes (np. `data.records:read`, `data.records:write`)
4. Wybierz bazy, do których token ma dostęp
5. Skopiuj token

### Opcja 2: OAuth 2.0
Dla aplikacji użytkowników - wymaga rejestracji aplikacji.

### Struktura URL API
```
https://api.airtable.com/v0/{baseId}/{tableName}
```

### Nagłówek autoryzacji
```
Authorization: Bearer YOUR_TOKEN
```

### Gdzie znaleźć Base ID?
1. Otwórz bazę w Airtable
2. Kliknij **Help** → **API documentation**
3. Base ID jest w URL (zaczyna się od `app`)
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


def seed_integrations(db: Session) -> None:
    """Seed integrations into the database."""
    created_count = 0
    skipped_count = 0

    for data in INTEGRATIONS_DATA:
        # Check if exists
        existing = db.query(Integration).filter(Integration.slug == data["slug"]).first()

        if existing:
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
    print("🎉 Seeding complete!")
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total:   {created_count + skipped_count}")
    print("=" * 60)


def main() -> None:
    """Main entry point."""
    print("=" * 60)
    print("🔌 Integration Seeding Script")
    print("=" * 60)
    print()

    db = next(get_db())
    try:
        seed_integrations(db)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
