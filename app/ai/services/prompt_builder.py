"""Assembles system prompts for AI sales page generation."""

import json
from typing import Any

from app.ai.models.brand_guidelines import BrandGuidelines
from app.courses.schemas.sales_page import SECTION_CONFIG_MAP


def _schema_reference() -> str:
    """Generate a reference of all section types and their config fields."""
    lines: list[str] = []
    for section_type, config_cls in SECTION_CONFIG_MAP.items():
        fields_info: list[str] = []
        for name, field in config_cls.model_fields.items():
            annotation = field.annotation
            type_name = getattr(annotation, "__name__", str(annotation))
            default = field.default
            if default is not None and default != "":
                fields_info.append(f"    - {name}: {type_name} (default: {default!r})")
            else:
                fields_info.append(f"    - {name}: {type_name}")
        lines.append(f"  {section_type}:")
        lines.extend(fields_info)
    return "\n".join(lines)


def _brand_guidelines_context(guidelines: BrandGuidelines) -> str:
    """Format brand guidelines for the system prompt."""
    parts: list[str] = []
    if guidelines.tone:
        parts.append(f"- Ton komunikacji: {guidelines.tone}")
    if guidelines.style:
        parts.append(f"- Styl: {guidelines.style}")
    if guidelines.target_audience:
        parts.append(f"- Grupa docelowa: {guidelines.target_audience}")
    if guidelines.unique_selling_proposition:
        parts.append(f"- USP: {guidelines.unique_selling_proposition}")
    if guidelines.language:
        parts.append(f"- Język: {guidelines.language}")
    if guidelines.avoid_phrases:
        parts.append(f"- Unikaj fraz: {guidelines.avoid_phrases}")
    if guidelines.preferred_phrases:
        parts.append(f"- Preferowane frazy: {guidelines.preferred_phrases}")
    if guidelines.company_description:
        parts.append(f"- Opis firmy: {guidelines.company_description}")
    if guidelines.additional_instructions:
        parts.append(f"- Dodatkowe instrukcje: {guidelines.additional_instructions}")

    if not parts:
        return ""
    return "## Wytyczne marki\n" + "\n".join(parts)


def _product_context_course(course_data: dict[str, Any]) -> str:
    """Format course data for the system prompt."""
    lines = [
        "## Dane produktu (kurs)",
        f"- Tytuł: {course_data.get('title', '')}",
        f"- Opis: {course_data.get('description', '')}",
    ]
    if course_data.get("difficulty"):
        lines.append(f"- Poziom trudności: {course_data['difficulty']}")
    if course_data.get("estimated_hours"):
        lines.append(f"- Szacowany czas: {course_data['estimated_hours']}h")
    if course_data.get("category"):
        lines.append(f"- Kategoria: {course_data['category']}")

    modules = course_data.get("modules", [])
    if modules:
        lines.append("\n### Program kursu:")
        for mod in modules:
            lines.append(f"  Moduł: {mod.get('title', '')}")
            if mod.get("description"):
                lines.append(f"    Opis: {mod['description']}")
            lessons = mod.get("lessons", [])
            for lesson in lessons:
                duration = lesson.get("duration_seconds", 0)
                mins = duration // 60 if duration else 0
                lines.append(f"    - {lesson.get('title', '')} ({mins} min)")

    return "\n".join(lines)


def _product_context_bundle(bundle_data: dict[str, Any]) -> str:
    """Format bundle data for the system prompt."""
    lines = [
        "## Dane produktu (pakiet/oferta)",
        f"- Nazwa: {bundle_data.get('title', '')}",
        f"- Opis: {bundle_data.get('description', '')}",
    ]
    if bundle_data.get("price"):
        price_pln = bundle_data["price"] / 100
        lines.append(f"- Cena: {price_pln:.2f} PLN")
    if bundle_data.get("original_price"):
        orig_pln = bundle_data["original_price"] / 100
        lines.append(f"- Cena oryginalna: {orig_pln:.2f} PLN")
    if bundle_data.get("difficulty"):
        lines.append(f"- Poziom trudności: {bundle_data['difficulty']}")
    if bundle_data.get("category"):
        lines.append(f"- Kategoria: {bundle_data['category']}")

    bundle_items = bundle_data.get("bundle_items", [])
    if bundle_items:
        lines.append("\n### Zawartość pakietu:")
        for item in bundle_items:
            child = item.get("child_package", {})
            lines.append(f"  - {child.get('title', 'Pakiet')}")

    course_items = bundle_data.get("course_items", [])
    if course_items:
        lines.append("\n### Kursy w pakiecie:")
        for item in course_items:
            course = item.get("course", {})
            lines.append(f"  - {course.get('title', 'Kurs')}")

    return "\n".join(lines)


def _few_shot_examples(examples: list[dict[str, Any]]) -> str:
    """Format existing sales pages as few-shot examples."""
    if not examples:
        return ""

    lines = ["## Przykłady istniejących stron sprzedażowych (użyj jako inspirację):"]
    for i, example in enumerate(examples, 1):
        lines.append(f"\n### Przykład {i}:")
        lines.append(f"```json\n{json.dumps(example, ensure_ascii=False, indent=2)}\n```")

    return "\n".join(lines)


def build_system_prompt(
    entity_type: str,
    product_data: dict[str, Any],
    guidelines: BrandGuidelines | None = None,
    examples: list[dict[str, Any]] | None = None,
    theme: str = "dark",
) -> str:
    """Assemble the full system prompt for sales page generation."""
    parts: list[str] = []

    # Base instruction
    parts.append("""Jesteś ekspertem od tworzenia stron sprzedażowych (landing pages).
Twoim zadaniem jest wygenerowanie kompletnej strony sprzedażowej w formacie JSON.

## Wymagany format odpowiedzi

WAŻNE: Twoja odpowiedź MUSI zawierać dwa elementy:
1. Blok JSON z danymi strony sprzedażowej w formacie ```json ... ```
2. Krótkie wyjaśnienie (po bloku JSON) co zostało wygenerowane/zmienione

Format JSON musi być zgodny ze schematem SalesPageData:
```
{
  "version": 1,
  "sections": [
    {
      "id": "<uuid>",
      "type": "<section_type>",
      "sort_order": <number>,
      "visible": true,
      "config": { ... }
    }
  ],
  "settings": {
    "theme": "<dark|light>",
    "custom_css": ""
  }
}
```""")

    # Schema reference
    parts.append(f"""## Dostępne typy sekcji i ich konfiguracja

{_schema_reference()}""")

    # Brand guidelines
    if guidelines:
        brand_ctx = _brand_guidelines_context(guidelines)
        if brand_ctx:
            parts.append(brand_ctx)

    # Product context
    if entity_type == "course":
        parts.append(_product_context_course(product_data))
    else:
        parts.append(_product_context_bundle(product_data))

    # Few-shot examples
    if examples:
        parts.append(_few_shot_examples(examples))

    # Rules
    parts.append(f"""## Zasady

1. Pisz WYŁĄCZNIE po polsku (chyba że instrukcja mówi inaczej)
2. Tekst musi być perswazyjny, profesjonalny i angażujący
3. Dla pól z URL do obrazów: zostaw puste string ("") \
i dodaj pole "_image_description" z opisem sugerowanego obrazu
4. Testimoniale powinny wyglądać realistycznie (polskie imiona i nazwiska)
5. Każda sekcja musi mieć unikalny UUID (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
6. sort_order musi być sekwencyjny (0, 1, 2, ...)
7. Ustaw theme na "{theme}"
8. Generuj sekcje odpowiednie do kontekstu produktu
9. NIE generuj sekcji custom_html ani rich_text, chyba że użytkownik wyraźnie o to prosi
10. Maksymalnie 30 sekcji na stronę
11. Odpowiedz NAJPIERW blokiem JSON, potem wyjaśnieniem""")

    return "\n\n".join(parts)


def build_iterative_user_message(
    user_prompt: str,
    current_page_data: dict[str, Any] | None = None,
) -> str:
    """Build user message for iterative mode, optionally including current page state."""
    if current_page_data is None:
        return user_prompt

    sections_summary: list[str] = []
    for section in current_page_data.get("sections", []):
        sections_summary.append(
            f"  - [{section.get('sort_order', '?')}] {section.get('type', '?')} "
            f"(id: {section.get('id', '?')})"
        )

    summary = "\n".join(sections_summary) if sections_summary else "  (brak sekcji)"

    return f"""Aktualny stan strony:
Sekcje:
{summary}
Theme: {current_page_data.get("settings", {}).get("theme", "dark")}

Pełne dane aktualnej strony:
```json
{json.dumps(current_page_data, ensure_ascii=False, indent=2)}
```

Instrukcja użytkownika: {user_prompt}"""
