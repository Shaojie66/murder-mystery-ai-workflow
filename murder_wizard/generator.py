"""LLM generation utilities."""

import os
import anthropic

API_KEY = os.environ.get("MURDER_WIZARD_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-4-20250514"


def generate_with_llm(system_prompt: str, user_prompt: str, max_retries: int = 3) -> str:
    """Generate content using Claude API."""
    if not API_KEY:
        raise ValueError("MURDER_WIZARD_API_KEY or ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=API_KEY)

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"Retry {attempt + 2}/{max_retries} after error: {e}")

    return ""
