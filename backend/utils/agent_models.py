from agents.extensions.models.litellm_model import LitellmModel

from backend.utils.keys import get_openrouter_api_key

GEMINI_FLASH_LITE_MODEL = LitellmModel(
    model="openrouter/google/gemini-2.5-flash-lite",
    base_url="https://openrouter.ai/api/v1",
    api_key=get_openrouter_api_key(),
)
