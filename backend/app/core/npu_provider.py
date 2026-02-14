"""NPU Provider Detection and Session Management.

Auto-detects available ONNX Runtime execution providers (NPU, GPU, CPU)
and creates inference sessions with graceful fallback. Supports Apple
Neural Engine, Intel NPU, Qualcomm NPU, AMD Ryzen AI, CUDA GPUs,
and DirectML, falling back to CPU when no accelerator is available.
"""

import logging
import os

import onnxruntime as ort

logger = logging.getLogger(__name__)

# Provider priority: NPU-class first, then GPU, then CPU
PROVIDER_PRIORITY = [
    "CoreMLExecutionProvider",
    "OpenVINOExecutionProvider",
    "QNNExecutionProvider",
    "VitisAIExecutionProvider",
    "DmlExecutionProvider",
    "CUDAExecutionProvider",
    "CPUExecutionProvider",
]

# Provider-specific session options.
# Empty dicts use the provider's defaults, which is preferred when the
# provider auto-selects the best compute unit (e.g. CoreML picks the
# Neural Engine automatically on Apple Silicon).
_PROVIDER_OPTIONS: dict[str, dict[str, object]] = {
    "CoreMLExecutionProvider": {},
    "OpenVINOExecutionProvider": {"device_type": "NPU", "precision": "FP16"},
    "QNNExecutionProvider": {"backend_path": "QnnHtp.dll"},
    "VitisAIExecutionProvider": {},
    "DmlExecutionProvider": {"device_id": 0},
    "CUDAExecutionProvider": {"device_id": 0},
    "CPUExecutionProvider": {},
}


def detect_available_providers() -> list[str]:
    """Return available ONNX providers ordered by priority.

    Queries ``ort.get_available_providers()`` and returns the intersection
    with ``PROVIDER_PRIORITY``, preserving priority order.
    """
    available = set(ort.get_available_providers())
    return [p for p in PROVIDER_PRIORITY if p in available]


def get_provider_options(provider: str) -> dict[str, object]:
    """Return provider-specific session options.

    Args:
        provider: ONNX Runtime execution provider name.

    Returns:
        Options dict suitable for the provider's entry in the providers list.
    """
    return dict(_PROVIDER_OPTIONS.get(provider, {}))


def select_providers(override: str | None = None) -> list[str]:
    """Select execution providers to use.

    Reads the ``DYSLEX_ONNX_PROVIDERS`` environment variable (comma-separated)
    if *override* is ``None``.  Otherwise uses the supplied override string.
    Falls back to auto-detection when neither is set.  Always appends
    ``CPUExecutionProvider`` as a final fallback.

    Args:
        override: Comma-separated provider names, or ``None`` to read from
            env / auto-detect.

    Returns:
        Ordered list of provider names to try.
    """
    raw = override or os.environ.get("DYSLEX_ONNX_PROVIDERS", "")
    if raw.strip():
        providers = [p.strip() for p in raw.split(",") if p.strip()]
    else:
        providers = detect_available_providers()

    # Always ensure CPU fallback
    if "CPUExecutionProvider" not in providers:
        providers.append("CPUExecutionProvider")

    return providers


def create_session(
    model_path: str,
    providers: list[str] | None = None,
) -> tuple[ort.InferenceSession, str]:
    """Create an ONNX InferenceSession, trying providers in order.

    For each provider, the corresponding options from
    :func:`get_provider_options` are applied.  If a provider fails to
    initialise, a warning is logged and the next provider is tried.

    Args:
        model_path: Path to the ``.onnx`` model file.
        providers: Ordered list of providers to try.  Defaults to
            :func:`select_providers`.

    Returns:
        Tuple of ``(session, active_provider_name)``.

    Raises:
        RuntimeError: If no provider could create a session (should never
            happen since CPUExecutionProvider is always available).
    """
    if providers is None:
        providers = select_providers()

    last_error: Exception | None = None

    for provider in providers:
        try:
            options = get_provider_options(provider)
            provider_with_options = (provider, options) if options else provider
            session = ort.InferenceSession(
                model_path,
                providers=[provider_with_options],
            )
            active = get_active_provider(session)
            logger.info("ONNX session created with provider: %s", active)
            return session, active
        except Exception as exc:
            logger.warning(
                "Provider %s failed, trying next: %s", provider, exc
            )
            last_error = exc

    raise RuntimeError(
        f"All ONNX providers failed. Last error: {last_error}"
    )


def get_active_provider(session: ort.InferenceSession) -> str:
    """Return the name of the provider actually in use by *session*.

    Args:
        session: An initialised ONNX InferenceSession.

    Returns:
        Provider name string (e.g. ``"CPUExecutionProvider"``).
    """
    active_providers = session.get_providers()
    return active_providers[0] if active_providers else "unknown"
