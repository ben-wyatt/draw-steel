from agents.extensions.models.litellm_model import LitellmModel

from backend.utils.keys import get_gemini_api_key, get_openrouter_api_key

# GEMINI
GEMINI_FLASH_LITE_MODEL = LitellmModel(
    model="openrouter/google/gemini-2.5-flash-lite",
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)

GEMINI_FLAST_MODEL = LitellmModel(
    model="openrouter/google/gemini-2.5-flash-preview-09-2025",
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)

GEMINI_PRO_MODEL = LitellmModel(
    model="openrouter/google/gemini-3-pro-preview",
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)

GEMINI_PRO_FREE = LitellmModel(
    model="gemini/gemini-3-pro-preview",
    api_key=get_gemini_api_key(),
)

# CLAUDE

CLAUDE_HAIKU_MODEL = LitellmModel(
    model="openrouter/anthropic/claude-haiku-4.5",
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)

CLAUDE_SONNET_MODEL = LitellmModel(
    model="openrouter/anthropic/claude-sonnet-4.5",
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)

# GPT
GPT_MODEL = LitellmModel(
    model="openrouter/openai/gpt-5.1",
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)

GPT_MINI_MODEL = LitellmModel(
    model="openrouter/openai/gpt-5.1-mini",
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)

GPT_NANO_MODEL = LitellmModel(
    model="openrouter/openai/gpt-5.1-nano",
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)

# Model name mapping
MODEL_MAP = {
    "gemini-flash-lite": GEMINI_FLASH_LITE_MODEL,
    "gemini-flash": GEMINI_FLAST_MODEL,
    "gemini-pro": GEMINI_PRO_MODEL,
    "claude-haiku": CLAUDE_HAIKU_MODEL,
    "claude-sonnet": CLAUDE_SONNET_MODEL,
    "gpt": GPT_MODEL,
    "gpt-mini": GPT_MINI_MODEL,
    "gpt-nano": GPT_NANO_MODEL,
    "gemini-pro-free": GEMINI_PRO_FREE,
}
