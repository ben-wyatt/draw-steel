"""Utility functions for calculating LLM API costs."""

import sys
from typing import Optional

import requests

# Cache for model pricing to avoid repeated API calls
_model_pricing_cache: dict[str, Optional[dict[str, float]]] = {}


def get_model_pricing(model: str, api_key: str) -> Optional[dict[str, float]]:
    """
    Get pricing for a model from OpenRouter API.

    Args:
        model: Model identifier (e.g., "google/gemini-2.5-flash-lite")
        api_key: OpenRouter API key

    Returns:
        Dict with 'input' and 'output' prices per token, or None if unavailable
    """
    # Check cache first
    if model in _model_pricing_cache:
        return _model_pricing_cache[model]

    try:
        # Query OpenRouter models API (may work without auth)
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        models_data = response.json()

        # Find the model in the list
        for model_info in models_data.get("data", []):
            model_id = model_info.get("id")
            if model_id == model:
                pricing = model_info.get("pricing", {})
                # OpenRouter uses "prompt" for input and "completion" for output
                # Pricing values may be strings, so convert to float
                try:
                    input_price = float(
                        pricing.get("prompt", 0.0)
                    )  # per million tokens
                    output_price = float(
                        pricing.get("completion", 0.0)
                    )  # per million tokens
                except (ValueError, TypeError):
                    # If conversion fails, treat as 0
                    input_price = 0.0
                    output_price = 0.0

                if input_price > 0 or output_price > 0:
                    result = {"input": input_price, "output": output_price}
                    _model_pricing_cache[model] = result  # type: ignore[assignment]
                    return result
                else:
                    # Model found but pricing is 0 or missing
                    # Cache a None result to avoid repeated lookups
                    _model_pricing_cache[model] = None  # type: ignore[assignment]
                    return None

        # Model not found - try checking if model names are similar (for debugging)
        available_models = [m.get("id") for m in models_data.get("data", [])]
        matching_models = [
            m
            for m in available_models
            if model.lower() in m.lower() or m.lower() in model.lower()
        ]

        if matching_models:
            # Debug: print similar models found
            print(
                f"Model '{model}' not found. Similar models: {matching_models[:3]}",
                file=sys.stderr,
            )

        # Cache None to avoid repeated failed lookups
        _model_pricing_cache[model] = None  # type: ignore[assignment]
        return None
    except requests.exceptions.RequestException as e:
        # Log the specific error for debugging
        print(f"Error fetching model pricing from OpenRouter: {e}", file=sys.stderr)
        return None
    except Exception as e:
        # Log unexpected errors
        print(
            f"Unexpected error in get_model_pricing: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return None


def calculate_cost(
    input_tokens: int, output_tokens: int, pricing: Optional[dict[str, float]]
) -> Optional[float]:
    """
    Calculate cost based on token usage and pricing.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        pricing: Dict with 'input' and 'output' prices per token (from OpenRouter API)

    Returns:
        Total cost in USD, or None if pricing unavailable
    """
    if not pricing:
        return None

    # OpenRouter API returns pricing per token, not per million tokens
    input_cost = input_tokens * pricing.get("input", 0.0)
    output_cost = output_tokens * pricing.get("output", 0.0)
    return input_cost + output_cost
