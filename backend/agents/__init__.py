import contextlib
import io
import os
import socket
import warnings

from agents import (
    set_default_openai_api,
    set_tracing_disabled,
    set_tracing_export_api_key,
)
from phoenix.otel import register

from backend.utils.keys import get_openrouter_api_key


# Helper to configure warnings for noisy dependencies
def _configure_warnings():
    # Global warning suppression for noisy dependencies (aiohttp, pydantic, etc.)
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module=r"aiohttp(\.connector)?",
    )
    warnings.filterwarnings(
        "ignore",
        message=r".*enable_cleanup_closed ignored because .*118960.*",
        category=DeprecationWarning,
    )
    # Suppress Pydantic serializer warnings that occur with agents framework
    # These warnings happen when serializing Message/Choices objects for tracing
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        module=r"pydantic\.main",
    )
    warnings.filterwarnings(
        "ignore",
        message=r"Pydantic serializer warnings:.*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=r".*PydanticSerializationUnexpectedValue.*",
        category=UserWarning,
    )


_configure_warnings()

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
