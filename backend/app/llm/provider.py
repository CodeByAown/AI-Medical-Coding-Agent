"""
LLM provider abstraction — supports Ollama (local), Anthropic Claude, and OpenAI.
Ollama is the default for HIPAA-friendly local deployment.
"""
import json
import logging
import re
from typing import Any, Dict, Optional

from app.config import get_settings
from app.utils.async_utils import run_sync

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMProvider:
    """Unified LLM interface supporting multiple backends."""

    def __init__(self):
        self._ollama_client = None
        self._anthropic_client = None
        self._openai_client = None

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """Send a completion request to the configured LLM provider."""
        provider = settings.llm_provider.lower()

        if provider == "ollama":
            return await self._ollama_complete(system_prompt, user_message, temperature, max_tokens)
        elif provider == "anthropic":
            return await self._anthropic_complete(system_prompt, user_message, temperature, max_tokens)
        elif provider == "openai":
            return await self._openai_complete(system_prompt, user_message, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    async def _ollama_complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        try:
            import ollama as ollama_lib

            def _call():
                return ollama_lib.chat(
                    model=settings.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                )

            response = await run_sync(_call)
            return response["message"]["content"]
        except ImportError:
            raise RuntimeError("ollama package not installed. Run: pip install ollama")
        except Exception as e:
            logger.error(f"Ollama completion failed: {e}")
            raise

    async def _anthropic_complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        try:
            from anthropic import AsyncAnthropic
            if self._anthropic_client is None:
                self._anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            message = await self._anthropic_client.messages.create(
                model=settings.anthropic_model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                temperature=temperature,
            )
            return message.content[0].text
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
        except Exception as e:
            logger.error(f"Anthropic completion failed: {e}")
            raise

    async def _openai_complete(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        try:
            from openai import AsyncOpenAI
            if self._openai_client is None:
                self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await self._openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        except Exception as e:
            logger.error(f"OpenAI completion failed: {e}")
            raise

    async def check_availability(self) -> Dict[str, Any]:
        """Check if the configured LLM is reachable."""
        provider = settings.llm_provider.lower()
        try:
            if provider == "ollama":
                import httpx
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                    models = resp.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    return {
                        "available": True,
                        "provider": "ollama",
                        "model": settings.llm_model,
                        "model_available": any(
                            settings.llm_model in name for name in model_names
                        ),
                        "available_models": model_names,
                    }
            elif provider == "anthropic":
                return {
                    "available": bool(settings.anthropic_api_key),
                    "provider": "anthropic",
                    "model": settings.anthropic_model,
                }
            elif provider == "openai":
                return {
                    "available": bool(settings.openai_api_key),
                    "provider": "openai",
                    "model": settings.openai_model,
                }
        except Exception as e:
            return {"available": False, "provider": provider, "error": str(e)}
        return {"available": False, "provider": provider}


def parse_llm_json_response(response_text: str) -> Dict:
    """Extract and parse JSON from LLM response, handling markdown code blocks."""
    # Try direct JSON parse first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Extract from markdown code block
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```",
        r"\{[\s\S]*\}",
    ]
    for pattern in patterns:
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            candidate = match.group(1) if "```" in pattern else match.group(0)
            try:
                return json.loads(candidate.strip())
            except json.JSONDecodeError:
                continue

    logger.warning(f"Could not parse JSON from LLM response: {response_text[:200]}")
    return {}


# Module-level singleton
_llm_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = LLMProvider()
    return _llm_provider
