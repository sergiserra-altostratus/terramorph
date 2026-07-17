"""AI settings management service.

Persists provider configuration to disk (JSON file) so settings
survive container restarts.
"""

from pydantic import BaseModel, Field
from app.services.ai_cleaner import AIProvider, DEFAULT_MODELS, PROVIDER_INSTRUCTIONS, AVAILABLE_MODELS
from app.services.persistence import load, save

SETTINGS_FILE = "ai_settings.json"


class AIProviderConfig(BaseModel):
    """Configuration for a single AI provider."""

    provider: AIProvider
    api_key: str = ""
    model: str = ""
    endpoint_url: str = ""
    enabled: bool = False


class AISettings(BaseModel):
    """Global AI settings."""

    active_provider: AIProvider | None = None
    providers: dict[str, AIProviderConfig] = Field(default_factory=dict)


def _load_settings() -> AISettings:
    """Load settings from disk."""
    data = load(SETTINGS_FILE)
    if data:
        try:
            return AISettings(**data)
        except Exception:
            return AISettings()
    return AISettings()


def _save_settings(settings: AISettings) -> None:
    """Save settings to disk."""
    save(SETTINGS_FILE, settings.model_dump(mode="json"))


# Load on module init
_settings = _load_settings()


def get_settings() -> AISettings:
    """Get current AI settings."""
    return _settings


def get_active_config() -> AIProviderConfig | None:
    """Get the active provider configuration (if any is configured)."""
    if not _settings.active_provider:
        return None
    config = _settings.providers.get(_settings.active_provider.value)
    if config and config.enabled and config.api_key:
        return config
    return None


def is_ai_configured() -> bool:
    """Check if any AI provider is configured and active."""
    return get_active_config() is not None


def set_provider_config(
    provider: AIProvider,
    api_key: str,
    model: str = "",
    endpoint_url: str = "",
) -> None:
    """Configure a provider and persist to disk."""
    config = AIProviderConfig(
        provider=provider,
        api_key=api_key,
        model=model or DEFAULT_MODELS.get(provider, ""),
        endpoint_url=endpoint_url,
        enabled=True,
    )
    _settings.providers[provider.value] = config

    # Auto-set as active if it's the first configured provider
    if not _settings.active_provider:
        _settings.active_provider = provider

    _save_settings(_settings)


def set_active_provider(provider: AIProvider) -> bool:
    """Set the active AI provider and persist."""
    config = _settings.providers.get(provider.value)
    if config and config.enabled:
        _settings.active_provider = provider
        _save_settings(_settings)
        return True
    return False


def remove_provider_config(provider: AIProvider) -> None:
    """Remove a provider configuration and persist."""
    _settings.providers.pop(provider.value, None)
    if _settings.active_provider == provider:
        _settings.active_provider = None
        for p, config in _settings.providers.items():
            if config.enabled:
                _settings.active_provider = AIProvider(p)
                break

    _save_settings(_settings)


def mask_api_key(key: str) -> str:
    """Mask an API key for safe display."""
    if not key:
        return ""
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def get_settings_for_frontend() -> dict:
    """Get settings formatted for frontend display (keys masked)."""
    providers_info = []
    for provider in AIProvider:
        config = _settings.providers.get(provider.value)
        instructions = PROVIDER_INSTRUCTIONS.get(provider, {})
        providers_info.append({
            "provider": provider.value,
            "name": instructions.get("name", provider.value),
            "url": instructions.get("url", ""),
            "instructions": instructions.get("instructions", []),
            "placeholder": instructions.get("placeholder", ""),
            "configured": bool(config and config.api_key),
            "enabled": bool(config and config.enabled),
            "model": config.model if config else DEFAULT_MODELS.get(provider, ""),
            "endpoint_url": config.endpoint_url if config else "",
            "api_key_masked": mask_api_key(config.api_key) if config else "",
            "default_model": DEFAULT_MODELS.get(provider, ""),
            "available_models": AVAILABLE_MODELS.get(provider, []),
        })

    return {
        "active_provider": _settings.active_provider.value if _settings.active_provider else None,
        "is_configured": is_ai_configured(),
        "providers": providers_info,
    }
