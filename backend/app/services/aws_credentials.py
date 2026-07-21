"""AWS credentials management service.

Stores AWS access credentials for resource discovery.
Best practice: IAM user with ReadOnlyAccess policy.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.persistence import load, save
from app.core.encryption import encrypt, decrypt

logger = get_logger("aws.credentials")

AWS_SETTINGS_FILE = "aws_settings.json"

AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-north-1", "eu-south-1",
    "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
    "ap-southeast-1", "ap-southeast-2",
    "ap-south-1", "ap-east-1",
    "sa-east-1",
    "ca-central-1",
    "me-south-1", "af-south-1",
]


class AWSCredentials(BaseModel):
    """AWS credential configuration."""

    access_key_id: str = ""
    secret_access_key: str = ""
    session_token: str = ""
    region: str = "us-east-1"
    configured: bool = False


def _load_aws_settings() -> AWSCredentials:
    """Load AWS settings from disk and decrypt secrets."""
    data = load(AWS_SETTINGS_FILE)
    if data:
        try:
            if data.get("secret_access_key"):
                data["secret_access_key"] = decrypt(data["secret_access_key"])
            if data.get("session_token"):
                data["session_token"] = decrypt(data["session_token"])
            return AWSCredentials(**data)
        except Exception:
            return AWSCredentials()
    return AWSCredentials()


def _save_aws_settings(settings: AWSCredentials) -> None:
    """Save AWS settings to disk with encrypted secrets."""
    data = settings.model_dump()
    if data.get("secret_access_key"):
        data["secret_access_key"] = encrypt(data["secret_access_key"])
    if data.get("session_token"):
        data["session_token"] = encrypt(data["session_token"])
    save(AWS_SETTINGS_FILE, data)


# Load on module init
_aws_settings = _load_aws_settings()


def get_aws_credentials() -> AWSCredentials:
    """Get current AWS credentials."""
    return _aws_settings


def is_aws_configured() -> bool:
    """Check if AWS credentials are configured."""
    return _aws_settings.configured and bool(_aws_settings.access_key_id)


def set_aws_credentials(
    access_key_id: str,
    secret_access_key: str,
    region: str = "us-east-1",
    session_token: str = "",
) -> None:
    """Configure AWS credentials and persist."""
    _aws_settings.access_key_id = access_key_id
    _aws_settings.secret_access_key = secret_access_key
    _aws_settings.region = region
    _aws_settings.session_token = session_token
    _aws_settings.configured = True
    _save_aws_settings(_aws_settings)


def remove_aws_credentials() -> None:
    """Remove AWS credentials."""
    _aws_settings.access_key_id = ""
    _aws_settings.secret_access_key = ""
    _aws_settings.session_token = ""
    _aws_settings.configured = False
    _save_aws_settings(_aws_settings)


def get_boto3_session() -> boto3.Session:
    """Create a boto3 session from configured credentials.

    Returns:
        Authenticated boto3 session.

    Raises:
        ValueError: If credentials are not configured.
    """
    if not is_aws_configured():
        raise ValueError("AWS credentials not configured. Go to Settings to configure them.")

    kwargs = {
        "aws_access_key_id": _aws_settings.access_key_id,
        "aws_secret_access_key": _aws_settings.secret_access_key,
        "region_name": _aws_settings.region,
    }
    if _aws_settings.session_token:
        kwargs["aws_session_token"] = _aws_settings.session_token

    return boto3.Session(**kwargs)


def check_aws_auth() -> dict:
    """Verify AWS authentication is valid.

    Returns:
        Dict with status details.
    """
    if not is_aws_configured():
        return {"authenticated": False, "account": None, "error": "Not configured"}

    try:
        session = get_boto3_session()
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        return {
            "authenticated": True,
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
            "user_id": identity.get("UserId"),
        }
    except (ClientError, NoCredentialsError) as e:
        return {"authenticated": False, "account": None, "error": str(e)}


def get_aws_settings_for_frontend() -> dict:
    """Get AWS settings formatted for frontend (secret masked)."""
    return {
        "configured": _aws_settings.configured,
        "access_key_id_masked": _mask_key(_aws_settings.access_key_id),
        "region": _aws_settings.region,
        "has_session_token": bool(_aws_settings.session_token),
        "regions": AWS_REGIONS,
    }


def _mask_key(key: str) -> str:
    """Mask a key for display."""
    if not key:
        return ""
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"
