import anthropic

from app.core.config import settings


def call_anthropic(
    system_prompt: str,
    messages: list[dict[str, str]],
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> tuple[str, int | None, str]:
    """Call Anthropic Messages API.

    Returns:
        Tuple of (response_text, tokens_used, model_name)
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=max_tokens or settings.ANTHROPIC_MAX_TOKENS,
        temperature=temperature if temperature is not None else 1.0,
        system=system_prompt,
        messages=messages,
    )

    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    tokens_used = None
    if response.usage:
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

    return text, tokens_used, response.model
