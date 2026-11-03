"""Provider registry — maps provider names to their integration classes."""

from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .anthropic_provider import AnthropicProvider
from .ollama_provider import OllamaProvider
from .custom_provider import CustomProvider

PROVIDERS = {
    'openai': OpenAIProvider,
    'gemini': GeminiProvider,
    'anthropic': AnthropicProvider,
    'ollama': OllamaProvider,
    'custom': CustomProvider,
}

def get_provider(provider_name, api_key='', base_url='', model_id='', timeout=120):
    cls = PROVIDERS.get(provider_name)
    if not cls:
        raise ValueError(f"Unknown provider: {provider_name}")
    return cls(api_key=api_key, base_url=base_url, model_id=model_id, timeout=timeout)
