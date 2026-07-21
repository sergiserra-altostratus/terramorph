"""AI settings API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ai_cleaner import AIProvider
from app.services.ai_settings import (
    get_settings_for_frontend,
    set_provider_config,
    set_active_provider,
    remove_provider_config,
    is_ai_configured,
)
from app.services.aws_credentials import (
    get_aws_settings_for_frontend,
    set_aws_credentials,
    remove_aws_credentials,
    check_aws_auth,
    is_aws_configured,
    AWS_REGIONS,
)

router = APIRouter()


class ConfigureProviderRequest(BaseModel):
    """Request to configure an AI provider."""

    provider: AIProvider
    api_key: str = ""
    model: str = ""
    endpoint_url: str = ""


class SetActiveProviderRequest(BaseModel):
    """Request to set the active provider."""

    provider: AIProvider


@router.get("/settings/ai")
async def get_ai_settings() -> dict:
    """Get AI provider settings (API keys masked)."""
    return get_settings_for_frontend()


@router.post("/settings/ai/configure")
async def configure_provider(request: ConfigureProviderRequest) -> dict:
    """Configure an AI provider with API key and optional settings."""
    # Ollama doesn't require API key
    if request.provider != AIProvider.OLLAMA and not request.api_key:
        raise HTTPException(status_code=400, detail="API key is required for this provider")

    set_provider_config(
        provider=request.provider,
        api_key=request.api_key,
        model=request.model,
        endpoint_url=request.endpoint_url,
    )

    return {"status": "configured", "provider": request.provider.value}


@router.post("/settings/ai/activate")
async def activate_provider(request: SetActiveProviderRequest) -> dict:
    """Set the active AI provider."""
    success = set_active_provider(request.provider)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{request.provider.value}' is not configured. Configure it first.",
        )
    return {"status": "activated", "provider": request.provider.value}


@router.delete("/settings/ai/{provider}")
async def delete_provider(provider: AIProvider) -> dict:
    """Remove a provider configuration."""
    remove_provider_config(provider)
    return {"status": "removed", "provider": provider.value}


@router.get("/settings/ai/status")
async def ai_status() -> dict:
    """Quick check if AI is configured and ready."""
    return {"configured": is_ai_configured()}


# === AWS Credentials ===


class AWSConfigureRequest(BaseModel):
    """Request to configure AWS credentials."""

    access_key_id: str
    secret_access_key: str
    region: str = "us-east-1"
    session_token: str = ""


@router.get("/settings/aws")
async def get_aws_settings() -> dict:
    """Get AWS credential settings (secrets masked)."""
    return get_aws_settings_for_frontend()


@router.post("/settings/aws/configure")
async def configure_aws(request: AWSConfigureRequest) -> dict:
    """Configure AWS credentials."""
    if not request.access_key_id or not request.secret_access_key:
        raise HTTPException(status_code=400, detail="Access Key ID and Secret Access Key are required.")

    set_aws_credentials(
        access_key_id=request.access_key_id,
        secret_access_key=request.secret_access_key,
        region=request.region,
        session_token=request.session_token,
    )
    return {"status": "configured"}


@router.delete("/settings/aws")
async def delete_aws() -> dict:
    """Remove AWS credentials."""
    remove_aws_credentials()
    return {"status": "removed"}


@router.get("/settings/aws/verify")
async def verify_aws() -> dict:
    """Verify AWS credentials are valid by calling STS."""
    return check_aws_auth()


@router.get("/settings/aws/status")
async def aws_status() -> dict:
    """Quick check if AWS is configured."""
    return {"configured": is_aws_configured()}
