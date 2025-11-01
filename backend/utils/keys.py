"""Utility functions for retrieving API keys from environment or configuration files."""

import os
from pathlib import Path
from typing import Optional


def get_openrouter_api_key() -> Optional[str]:
    """Get OPENROUTER_API_KEY from environment or ~/.zshenv file."""
    # First check environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return api_key

    # Try loading from ~/.zshenv
    zshenv_path = Path.home() / ".zshenv"
    if zshenv_path.exists():
        try:
            with open(zshenv_path, "r") as f:
                for line in f:
                    line = line.strip()
                    # Handle both "export OPENROUTER_API_KEY=" and "OPENROUTER_API_KEY="
                    if line.startswith("export OPENROUTER_API_KEY="):
                        value = line.split("=", 1)[1].strip()
                    elif line.startswith("OPENROUTER_API_KEY="):
                        value = line.split("=", 1)[1].strip()
                    else:
                        continue

                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    return value
        except Exception:
            pass

    return None
