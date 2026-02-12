"""Centralized LLM client with multi-provider support.

All three providers (NVIDIA NIM, Ollama, vLLM) expose an OpenAI-compatible
``/v1/chat/completions`` endpoint, so the core HTTP logic is identical —
only the base URL, model name, and auth header differ.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, enum.Enum):
    nvidia_nim = "nvidia_nim"
    ollama = "ollama"
    vllm = "vllm"


@dataclass
class LLMProviderConfig:
    provider: LLMProvider
    base_url: str
    model: str
    api_key: str = ""


PROVIDER_DEFAULTS: dict[LLMProvider, LLMProviderConfig] = {
    LLMProvider.nvidia_nim: LLMProviderConfig(
        provider=LLMProvider.nvidia_nim,
        base_url="https://integrate.api.nvidia.com/v1",
        model="nvidia/nemotron-3-nano-30b-a3b",
        api_key="",
    ),
    LLMProvider.ollama: LLMProviderConfig(
        provider=LLMProvider.ollama,
        base_url="http://localhost:11434/v1",
        model="llama3.2",
        api_key="",
    ),
    LLMProvider.vllm: LLMProviderConfig(
        provider=LLMProvider.vllm,
        base_url="http://localhost:8080/v1",
        model="meta-llama/Llama-3.1-8B-Instruct",
        api_key="",
    ),
}


def get_system_default_config() -> LLMProviderConfig:
    """Build config from environment/config.py settings (system-level defaults)."""
    provider_str = settings.llm_provider
    try:
        provider = LLMProvider(provider_str)
    except ValueError:
        provider = LLMProvider.nvidia_nim

    if provider == LLMProvider.nvidia_nim:
        return LLMProviderConfig(
            provider=provider,
            base_url=settings.nvidia_nim_llm_url,
            model=settings.nvidia_nim_llm_model,
            api_key=settings.nvidia_nim_api_key,
        )
    elif provider == LLMProvider.ollama:
        return LLMProviderConfig(
            provider=provider,
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            api_key="",
        )
    elif provider == LLMProvider.vllm:
        return LLMProviderConfig(
            provider=provider,
            base_url=settings.vllm_base_url,
            model=settings.vllm_model,
            api_key=settings.vllm_api_key,
        )

    return PROVIDER_DEFAULTS[LLMProvider.nvidia_nim]


async def get_user_llm_config(user_id: str, db: AsyncSession) -> LLMProviderConfig:
    """Resolve the LLM config for a specific user.

    Priority: user DB settings > system config > provider defaults.
    """
    from app.db.repositories.settings_repo import get_settings_by_user_id
    from app.utils.encryption import decrypt_api_key

    user_settings = await get_settings_by_user_id(db, user_id)

    if user_settings is None or user_settings.llm_provider is None:
        return get_system_default_config()

    try:
        provider = LLMProvider(user_settings.llm_provider)
    except ValueError:
        return get_system_default_config()

    defaults = PROVIDER_DEFAULTS[provider]
    system = get_system_default_config()

    base_url = user_settings.llm_base_url or (
        system.base_url if system.provider == provider else defaults.base_url
    )
    model = user_settings.llm_model or (
        system.model if system.provider == provider else defaults.model
    )

    api_key = ""
    if user_settings.llm_api_key_encrypted:
        api_key = decrypt_api_key(user_settings.llm_api_key_encrypted)
    elif provider == LLMProvider.nvidia_nim:
        api_key = settings.nvidia_nim_api_key
    elif provider == LLMProvider.vllm:
        api_key = settings.vllm_api_key

    return LLMProviderConfig(
        provider=provider,
        base_url=base_url,
        model=model,
        api_key=api_key,
    )
