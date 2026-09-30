# -*- coding: utf-8 -*-
"""Проверка связи с LLM: /models + короткий chat-запрос по цепочке провайдеров.

Запуск: python agent/llmcheck.py   (читает mvp/.env)
Код возврата 0 — хотя бы один провайдер отвечает.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mvp"))

from llm import log, pool_from_env  # noqa: E402


def main() -> int:
    pool = pool_from_env()
    ok = False
    for provider in pool.providers:
        url = provider.base_url.rstrip("/") + "/models"
        request = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {provider.api_key}",
        })
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
            models = [m.get("id") for m in data.get("data", [])]
            log(f"{provider.name}: /models OK, моделей: {len(models)}")
            probe, used = pool.chat(
                [{"role": "user", "content": "Ответь одним словом: работает?"}],
            )
            text = (probe.get("content") or "").strip()
            log(f"{provider.name}: chat OK ({used}), ответ: {text[:80]!r}")
            ok = True
        except Exception as error:  # noqa: BLE001 — диагностика, любой сбой не фатален
            log(f"{provider.name}: НЕДОСТУПЕН: {error}")
    print("LLM: OK" if ok else "LLM: все провайдеры недоступны")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
