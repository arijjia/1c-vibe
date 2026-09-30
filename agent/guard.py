# -*- coding: utf-8 -*-
"""Опциональный предохранитель от промпт-инъекций: qwen3guard перед goal.

Включается в .env:  LLM_GUARD=1  (+ опц. LLM_GUARD_MODEL=qwen3guard).
Проверяется текст цели агента; verdict "Safe" → пропускаем, иначе стоп.
Провайдер guard-а — основной в цепочке (litellm). Файл не зависит от loop.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

from llm import log


def check_goal(goal: str) -> tuple[bool, str]:
    """(безопасно, пояснение). Ошибка сервиса трактуется как безопасно (fail-open),
    т.к. guard — дополнительный слой, а не критический путь петли."""
    if os.environ.get("LLM_GUARD", "").strip() != "1":
        return True, "guard выключен"
    model = os.environ.get("LLM_GUARD_MODEL", "qwen3guard")
    base = os.environ.get("LLM_BASE_URL", "")
    key = os.environ.get("LLM_API_KEY", "")
    if not (base and key):
        return True, "guard включён, но нет LLM_BASE_URL/LLM_API_KEY — пропуск"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": goal}],
        "max_tokens": 100,
    }).encode("utf-8")
    request = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        verdict = (data["choices"][0]["message"].get("content") or "").strip()
    except Exception as error:  # noqa: BLE001 — fail-open, см. докстринг
        return True, f"guard недоступен ({error}) — пропускаю"
    safe = verdict.lower().startswith("safe")
    return safe, verdict
