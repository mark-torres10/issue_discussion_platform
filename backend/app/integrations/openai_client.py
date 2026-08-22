import os
from collections.abc import Callable
from typing import Any, Protocol

from openai import OpenAI


class ChatCompletionsClient(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class OpenAIClient(Protocol):
    chat: Any


_client_factory: Callable[[], OpenAI] | None = None


def set_openai_client_factory(factory: Callable[[], OpenAI] | None) -> None:
    global _client_factory
    _client_factory = factory


def get_openai_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return api_key


def get_configured_text_model() -> str:
    return os.environ.get("OPENAI_TEXT_MODEL", "gpt-4.1-mini")


def get_openai_client() -> OpenAI:
    if _client_factory is not None:
        return _client_factory()
    return OpenAI(api_key=get_openai_api_key())


def generate_chat_completion(
    *,
    client: OpenAI,
    model: str,
    messages: list[dict[str, str]],
) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned empty completion content")
    return content
