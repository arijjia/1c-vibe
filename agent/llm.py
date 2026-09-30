# -*- coding: utf-8 -*-
"""LLM-клиент 1c-vibe: OpenAI-совместимый API, только stdlib.

Цепочка отказоустойчивости моделей (первая доступная побеждает):
  1. основной провайдер из .env (LLM_BASE_URL + LLM_MODEL, по умолчанию
     корпоративный LiteLLM ЦИТ ТюмГУ с qwen-моделями);
  2. резервный провайдер из .env (LLM_FALLBACK_URL / LLM_FALLBACK_MODEL /
     LLM_FALLBACK_KEY, например z.ai coding API), если основной недоступен.

Все запросы логируются в stderr (модель, время, токены) — для журнала прогона.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

RETRY_COUNT = 2
RETRY_DELAY_S = 3.0
REQUEST_TIMEOUT_S = 180


@dataclass
class Provider:
    """Один LLM-провайдер (OpenAI-совместимый /chat/completions)."""

    name: str
    base_url: str
    api_key: str
    model: str

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             max_tokens: int = 8192) -> dict:
        """Один вызов /chat/completions; возвращает message-объект ассистента."""
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
        body = json.dumps(payload).encode("utf-8")
        url = self.base_url.rstrip("/") + "/chat/completions"
        last_error: Exception | None = None
        for attempt in range(1, RETRY_COUNT + 1):
            started = time.monotonic()
            request = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
                    data = json.loads(response.read().decode("utf-8"))
                choice = data["choices"][0]["message"]
                usage = data.get("usage", {})
                elapsed = time.monotonic() - started
                log(f"{self.name}/{self.model}: ok за {elapsed:.1f}с, "
                    f"токены: {usage.get('prompt_tokens', '?')}+{usage.get('completion_tokens', '?')}")
                return choice
            except (urllib.error.URLError, urllib.error.HTTPError, KeyError,
                    json.JSONDecodeError, TimeoutError, OSError) as error:
                last_error = error
                log(f"{self.name}/{self.model}: попытка {attempt}/{RETRY_COUNT} "
                    f"неудачна: {error}")
                if attempt < RETRY_COUNT:
                    time.sleep(RETRY_DELAY_S)
        raise ConnectionError(f"провайдер {self.name} недоступен: {last_error}")


@dataclass
class LlmPool:
    """Цепочка провайдеров; chat() идёт по цепочке до первого успеха."""

    providers: list[Provider] = field(default_factory=list)

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> tuple[dict, str]:
        """Возвращает (message, provider_name); падает только если все недоступны."""
        errors: list[str] = []
        for provider in self.providers:
            try:
                return provider.chat(messages, tools), provider.name
            except ConnectionError as error:
                errors.append(str(error))
        raise ConnectionError("все LLM-провайдеры недоступны:\n" + "\n".join(errors))


def log(message: str) -> None:
    """Журнал в stderr: время + текст (stdout оставлен ответам и артефактам)."""
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] {message}", file=sys.stderr, flush=True)


def pool_from_env() -> LlmPool:
    """Собрать пул провайдеров из переменных окружения / .env."""
    from envconfig import load_env  # локальный импорт: mvp-каркас

    load_env()
    providers: list[Provider] = []
    if os.environ.get("LLM_BASE_URL") and os.environ.get("LLM_API_KEY"):
        providers.append(Provider(
            name="main",
            base_url=os.environ["LLM_BASE_URL"],
            api_key=os.environ["LLM_API_KEY"],
            model=os.environ.get("LLM_MODEL", "qwen-3.8-deep"),
        ))
    if os.environ.get("LLM_FALLBACK_URL") and os.environ.get("LLM_FALLBACK_KEY"):
        providers.append(Provider(
            name="fallback",
            base_url=os.environ["LLM_FALLBACK_URL"],
            api_key=os.environ["LLM_FALLBACK_KEY"],
            model=os.environ.get("LLM_FALLBACK_MODEL", "glm-4.6"),
        ))
    if not providers:
        raise SystemExit("не задан ни один провайдер: заполни LLM_BASE_URL/LLM_API_KEY в .env")
    return LlmPool(providers)
