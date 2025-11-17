import contextlib
import io
import os
import socket
import warnings

_orig_showwarning = warnings.showwarning


def _filtered_showwarning(message, category, filename, lineno, file=None, line=None):
    """Filter out noisy warnings from Pydantic, aiohttp, and asyncio."""
    text = str(message)
    filename_str = str(filename) if filename else ""

    # Suppress Pydantic serializer warnings (harmless artifacts of using OpenRouter)
    if (
        "Pydantic serializer warnings" in text
        or "PydanticSerializationUnexpectedValue" in text
        or "pydantic" in filename_str.lower()
    ):
        if issubclass(category, UserWarning):
            return

    # Suppress aiohttp deprecation warnings
    if (
        "enable_cleanup_closed ignored because" in text
        or "aiohttp" in filename_str.lower()
    ):
        if issubclass(category, DeprecationWarning):
            return

    # Suppress ResourceWarnings about unclosed transports (common with async code)
    if "unclosed transport" in text or "asyncio" in filename_str.lower():
        if issubclass(category, ResourceWarning):
            return

    return _orig_showwarning(message, category, filename, lineno, file=file, line=line)


warnings.showwarning = _filtered_showwarning

# Also use filterwarnings as a backup
warnings.filterwarnings("ignore", category=UserWarning, module=r"pydantic")
warnings.filterwarnings(
    "ignore", message=r".*Pydantic.*serializer.*", category=UserWarning
)
warnings.filterwarnings(
    "ignore", message=r".*PydanticSerializationUnexpectedValue.*", category=UserWarning
)
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"aiohttp")
warnings.filterwarnings(
    "ignore", message=r".*enable_cleanup_closed.*", category=DeprecationWarning
)
warnings.filterwarnings(
    "ignore", category=ResourceWarning, message=r".*unclosed transport.*"
)
warnings.filterwarnings("ignore", category=ResourceWarning, module=r"asyncio")

from agents import (  # noqa: E402
    set_default_openai_api,
    set_tracing_disabled,
    set_tracing_export_api_key,
)
from phoenix.otel import register  # noqa: E402

from backend.utils.keys import get_openrouter_api_key  # noqa: E402


# Helper to configure warnings for noisy dependencies (can be called again if needed)
def _configure_warnings():
    # Suppress all Pydantic serializer warnings (harmless artifacts of using OpenRouter)
    warnings.filterwarnings("ignore", category=UserWarning, module=r"pydantic\.main")
    warnings.filterwarnings(
        "ignore", message=r".*Pydantic.*serializer.*", category=UserWarning
    )
    warnings.filterwarnings(
        "ignore",
        message=r".*PydanticSerializationUnexpectedValue.*",
        category=UserWarning,
    )
    warnings.filterwarnings("ignore", category=UserWarning, module=r"pydantic")

    # Suppress aiohttp deprecation warnings
    warnings.filterwarnings(
        "ignore", category=DeprecationWarning, module=r"aiohttp\.connector"
    )
    warnings.filterwarnings(
        "ignore", message=r".*enable_cleanup_closed.*", category=DeprecationWarning
    )
    warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"aiohttp")

    # Suppress ResourceWarnings about unclosed transports (common with async code)
    warnings.filterwarnings(
        "ignore", category=ResourceWarning, message=r".*unclosed transport.*"
    )
    warnings.filterwarnings(
        "ignore", category=ResourceWarning, module=r"asyncio\.selector_events"
    )
    warnings.filterwarnings(
        "ignore", category=ResourceWarning, module=r"asyncio\.sslproto"
    )
    warnings.filterwarnings("ignore", category=ResourceWarning, module=r"asyncio")


set_default_openai_api("responses")


def is_phoenix_running(host: str = "localhost", port: int = 6006) -> bool:
    """Check if Phoenix is running by attempting to connect to the port."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def init_tracing_quietly() -> None:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        register(
            project_name="draw-steel-agents",
            auto_instrument=True,
            endpoint="http://localhost:6006/v1/traces",
        )
    _configure_warnings()


# check if arize phoenix is running, if not, disable tracing
if is_phoenix_running():
    os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "http://localhost:6006"
    set_tracing_export_api_key(str(get_openrouter_api_key()))
    init_tracing_quietly()
else:
    set_tracing_disabled(True)


"""
The warning supression is really stupid and hacky.

TODO: make warning supression more elegant.
"""
