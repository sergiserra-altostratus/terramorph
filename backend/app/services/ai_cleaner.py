"""AI-powered HCL code cleaning service.

Supports multiple providers: OpenAI, Anthropic, Google AI, AWS Bedrock,
Azure OpenAI, Ollama, Groq, Mistral.
"""

import httpx
import json
from enum import Enum

from app.core.logging import get_logger

logger = get_logger("ai.cleaner")


class AIProvider(str, Enum):
    """Supported AI providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE_AI = "google_ai"
    AWS_BEDROCK = "aws_bedrock"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    GROQ = "groq"
    MISTRAL = "mistral"


# Default models per provider
DEFAULT_MODELS = {
    AIProvider.OPENAI: "gpt-4.1",
    AIProvider.ANTHROPIC: "claude-sonnet-4-20250514",
    AIProvider.GOOGLE_AI: "gemini-2.5-pro",
    AIProvider.AWS_BEDROCK: "anthropic.claude-sonnet-4-20250514-v1:0",
    AIProvider.AZURE_OPENAI: "gpt-4.1",
    AIProvider.OLLAMA: "llama3.1",
    AIProvider.GROQ: "llama-3.3-70b-versatile",
    AIProvider.MISTRAL: "mistral-large-latest",
}

# Available models per provider (updated July 2026)
AVAILABLE_MODELS = {
    AIProvider.OPENAI: [
        "gpt-5",
        "gpt-5-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "gpt-4o",
        "gpt-4o-mini",
        "o3",
        "o3-pro",
        "o3-mini",
        "o4-mini",
    ],
    AIProvider.ANTHROPIC: [
        "claude-sonnet-5-20260617",
        "claude-opus-4-7-20260301",
        "claude-sonnet-4-6-20260215",
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ],
    AIProvider.GOOGLE_AI: [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ],
    AIProvider.AWS_BEDROCK: [
        "anthropic.claude-sonnet-4-6-20260215-v1:0",
        "anthropic.claude-sonnet-4-20250514-v1:0",
        "anthropic.claude-opus-4-20250514-v1:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-5-haiku-20241022-v1:0",
        "amazon.nova-pro-v1:0",
        "amazon.nova-lite-v1:0",
        "meta.llama4-scout-17b-16e-instruct-v1:0",
    ],
    AIProvider.AZURE_OPENAI: [
        "gpt-5",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4o",
        "gpt-4o-mini",
        "o3-mini",
    ],
    AIProvider.OLLAMA: [
        "llama3.1",
        "llama3.1:70b",
        "llama3.3",
        "llama4-scout",
        "codellama",
        "deepseek-coder-v2",
        "qwen2.5-coder",
        "qwen3",
        "mistral",
        "mixtral",
        "gemma2",
        "phi-4",
    ],
    AIProvider.GROQ: [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama4-scout-17b-16e-instruct",
        "deepseek-r1-distill-llama-70b",
        "qwen-qwq-32b",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ],
    AIProvider.MISTRAL: [
        "mistral-large-latest",
        "mistral-medium-3.5",
        "mistral-small-latest",
        "codestral-latest",
        "magistral-medium-latest",
        "magistral-small-latest",
        "open-mistral-nemo",
        "devstral-latest",
    ],
}

# Provider setup instructions
PROVIDER_INSTRUCTIONS = {
    AIProvider.OPENAI: {
        "name": "OpenAI",
        "url": "https://platform.openai.com/api-keys",
        "instructions": [
            "Go to https://platform.openai.com/api-keys",
            "Click 'Create new secret key'",
            "Give it a name and copy the key (starts with 'sk-')",
            "Paste the key in the API Key field below",
        ],
        "placeholder": "sk-...",
    },
    AIProvider.ANTHROPIC: {
        "name": "Anthropic",
        "url": "https://console.anthropic.com/settings/keys",
        "instructions": [
            "Go to https://console.anthropic.com/settings/keys",
            "Click 'Create Key'",
            "Name it and copy the key (starts with 'sk-ant-')",
            "Paste the key in the API Key field below",
        ],
        "placeholder": "sk-ant-...",
    },
    AIProvider.GOOGLE_AI: {
        "name": "Google AI (Gemini)",
        "url": "https://aistudio.google.com/apikey",
        "instructions": [
            "Go to https://aistudio.google.com/apikey",
            "Click 'Create API Key'",
            "Select your GCP project",
            "Copy the generated key and paste it below",
        ],
        "placeholder": "AIza...",
    },
    AIProvider.AWS_BEDROCK: {
        "name": "AWS Bedrock",
        "url": "https://console.aws.amazon.com/bedrock",
        "instructions": [
            "Configure AWS credentials with Bedrock access",
            "Ensure the model is enabled in your AWS region",
            "Provide your AWS Access Key ID as the API Key",
            "Set the endpoint URL to your Bedrock region endpoint",
        ],
        "placeholder": "AKIA...",
    },
    AIProvider.AZURE_OPENAI: {
        "name": "Azure OpenAI",
        "url": "https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub",
        "instructions": [
            "Go to Azure Portal → Azure OpenAI resource",
            "Navigate to 'Keys and Endpoint'",
            "Copy Key 1 or Key 2",
            "Set the endpoint URL to your Azure OpenAI endpoint",
        ],
        "placeholder": "your-azure-key",
    },
    AIProvider.OLLAMA: {
        "name": "Ollama (Local)",
        "url": "https://ollama.com/download",
        "instructions": [
            "Install Ollama from https://ollama.com/download",
            "Run 'ollama pull llama3.1' to download a model",
            "Ensure Ollama is running (default: http://localhost:11434)",
            "No API key needed — set endpoint URL to http://localhost:11434",
        ],
        "placeholder": "(not required)",
    },
    AIProvider.GROQ: {
        "name": "Groq",
        "url": "https://console.groq.com/keys",
        "instructions": [
            "Go to https://console.groq.com/keys",
            "Click 'Create API Key'",
            "Copy the key (starts with 'gsk_')",
            "Paste it in the API Key field below",
        ],
        "placeholder": "gsk_...",
    },
    AIProvider.MISTRAL: {
        "name": "Mistral AI",
        "url": "https://console.mistral.ai/api-keys",
        "instructions": [
            "Go to https://console.mistral.ai/api-keys",
            "Click 'Create new key'",
            "Copy the generated key",
            "Paste it in the API Key field below",
        ],
        "placeholder": "your-mistral-key",
    },
}

# Clean prompt template
CLEAN_PROMPT = """Clean up the following Terraform HCL resource block by removing default values and unnecessary attributes that don't affect the infrastructure.

Rules:
- Remove attributes set to their default values (e.g., timeouts, empty strings, false booleans that are defaults)
- Remove computed/read-only attributes that Terraform manages automatically
- Remove redundant nested blocks that are empty or contain only defaults
- Keep all attributes that define the actual infrastructure state
- Preserve the resource type, name, and essential configuration
- Do NOT add lifecycle blocks or ignore_changes
- Do NOT add comments
- Preserve proper HCL formatting and indentation

Input HCL:
```hcl
{hcl_code}
```

Return ONLY the cleaned HCL code, nothing else. No markdown, no backticks, no explanations."""


async def clean_hcl(hcl_code: str, provider: AIProvider, api_key: str, model: str | None = None, endpoint_url: str | None = None) -> str:
    """Clean HCL code using the configured AI provider.

    Args:
        hcl_code: Raw HCL content to clean.
        provider: AI provider to use.
        api_key: API key for the provider.
        model: Optional model override.
        endpoint_url: Optional endpoint URL override.

    Returns:
        Cleaned HCL code.
    """
    if not model:
        model = DEFAULT_MODELS.get(provider, "")

    prompt = CLEAN_PROMPT.format(hcl_code=hcl_code)

    try:
        if provider == AIProvider.OPENAI:
            return await _call_openai(prompt, api_key, model)
        elif provider == AIProvider.ANTHROPIC:
            return await _call_anthropic(prompt, api_key, model)
        elif provider == AIProvider.GOOGLE_AI:
            return await _call_google_ai(prompt, api_key, model)
        elif provider == AIProvider.OLLAMA:
            return await _call_ollama(prompt, model, endpoint_url or "http://localhost:11434")
        elif provider == AIProvider.GROQ:
            return await _call_groq(prompt, api_key, model)
        elif provider == AIProvider.MISTRAL:
            return await _call_mistral(prompt, api_key, model)
        elif provider == AIProvider.AZURE_OPENAI:
            return await _call_azure_openai(prompt, api_key, model, endpoint_url or "")
        elif provider == AIProvider.AWS_BEDROCK:
            return await _call_openai(prompt, api_key, model)  # Bedrock uses OpenAI-compatible API
        else:
            logger.warning(f"Unsupported provider: {provider}")
            return hcl_code
    except Exception as e:
        logger.error(f"AI cleaning failed ({provider}): {e}")
        raise


async def _call_openai(prompt: str, api_key: str, model: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


async def _call_anthropic(prompt: str, api_key: str, model: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "Content-Type": "application/json", "anthropic-version": "2023-06-01"},
            json={"model": model, "max_tokens": 4096, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"].strip()


async def _call_google_ai(prompt: str, api_key: str, model: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}},
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _call_ollama(prompt: str, model: str, endpoint: str) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{endpoint}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.1}},
        )
        response.raise_for_status()
        return response.json()["response"].strip()


async def _call_groq(prompt: str, api_key: str, model: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


async def _call_mistral(prompt: str, api_key: str, model: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


async def _call_azure_openai(prompt: str, api_key: str, model: str, endpoint: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{endpoint}/openai/deployments/{model}/chat/completions?api-version=2024-02-01",
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json={"messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
