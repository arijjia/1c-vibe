# -*- coding: utf-8 -*-
"""Агентская петля 1c-vibe: задача → работа инструментами → отчёт.

Запуск (на машине с доступом к LLM и Jira/GitLab):
    python agent/loop.py --task INTAIDEV-101 --workspace mvp/dump
    python agent/loop.py --goal "разбери задачу INTAIDEV-102 и предложи правки"

Петля: системный промпт (скилл) + цель → модель → tool-calls → результаты
→ модель → … до финального ответа. Лимит итераций защищает от вечного цикла.
Порядок работы строго по скиллу mvp/skills/1c-vibe-demo/SKILL.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mvp"))

from llm import LlmPool, log, pool_from_env  # noqa: E402
from tools import TOOLS_SCHEMA, Toolbox, dispatch  # noqa: E402

MAX_TURNS = 40
SKILL_PATH = Path(__file__).resolve().parent.parent / "mvp" / "skills" / "1c-vibe-demo" / "SKILL.md"

SYSTEM_TEMPLATE = """Ты — 1С-разработчик-агент проекта 1c-vibe (ЦИТ ТюмГУ).

Ты работаешь на машине, где есть: python, git, доступ к Jira/GitLab организации,
рабочий каталог (workspace) с клоном репозитория и CLI-скриптами проекта.

Строго следуй процедуре скилла:
---
{skill}
---

Правила петли:
- Действуй инструментами (run_cmd/run_cli/read_file/write_file/list_dir), а не фантазией.
- Правки — только в ветке agent/<TASK>, созданной publish.py --prepare.
- Перед публикацией перечитай git diff и прогони доступные проверки.
- Завершай, когда цикл по скиллу выполнен (MR + комментарий в Jira) либо когда
  нужен человек: тогда финальный ответ — явный вопрос и что ты уже сделал.
- Финальный ответ пиши по-русски, кратко: что сделано, пруфы, что дальше.
"""


def build_system_prompt() -> str:
    try:
        skill = SKILL_PATH.read_text(encoding="utf-8")
    except OSError:
        skill = "(скилл не найден — работай по общей процедуре Jira→ветка→правка→MR)"
    return SYSTEM_TEMPLATE.format(skill=skill)


JSON_MODE_SUFFIX = """

РЕЖИМ JSON: отвечай СТРОГО одним JSON-объектом без markdown и пояснений:
  {"tool": "<имя инструмента>", "arguments": {…аргументы…}}
или, когда всё сделано и готов финальный ответ:
  {"final": "<текст отчёта по-русски>"}
"""

JSON_SCHEMA_HINT = """Доступные инструменты (имя → аргументы):
- run_cmd {command: str, timeout_s?: int} — shell-команда в workspace;
- run_cli {args: str} — CLI проекта: jira_client.py / gitlab_client.py / publish.py / seed_demo.py;
- read_file {path: str}; write_file {path: str, content: str}; list_dir {path?: str}.
"""


def _json_mode_message(choice: dict) -> dict | None:
    """Разобрать ответ JSON-режима: синтезировать tool_calls или вернуть final."""
    content = (choice.get("content") or "").strip()
    if not content:
        return None
    text = content
    if text.startswith("```"):  # снять markdown-забор, если модель его добавила
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # модель ответила текстом не по протоколу — считаем это финалом
        return choice
    if isinstance(parsed, dict) and parsed.get("tool"):
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": f"json_{int(time.time())}",
                "type": "function",
                "function": {
                    "name": parsed["tool"],
                    "arguments": json.dumps(parsed.get("arguments", {}), ensure_ascii=False),
                },
            }],
        }
    if isinstance(parsed, dict) and "final" in parsed:
        return {"role": "assistant", "content": str(parsed["final"])}
    return choice  # непонятный JSON — показываем как есть


def _chat_turn(pool: LlmPool, messages: list[dict],
               tools_broken: set[str]) -> tuple[dict, object, bool]:
    """Один ход к модели: (choice, provider, json_mode).

    Идём по провайдерам. Если провайдер отвечает, но не принял tools API —
    один раз пробуем тот же провайдер в JSON-режиме (суффикс к последнему
    сообщению, история не засоряется) и помечаем его в tools_broken.
    """
    last_error: Exception | None = None
    for provider in pool.providers:
        json_mode = provider.name in tools_broken
        msgs = messages
        if json_mode:
            msgs = messages + [{"role": "system",
                                "content": JSON_SCHEMA_HINT + JSON_MODE_SUFFIX}]
        try:
            return provider.chat(msgs, tools=None if json_mode else TOOLS_SCHEMA), provider, json_mode
        except ConnectionError as error:
            last_error = error
            if not json_mode:
                try:
                    choice = provider.chat(
                        messages + [{"role": "system",
                                     "content": JSON_SCHEMA_HINT + JSON_MODE_SUFFIX}],
                        tools=None)
                    tools_broken.add(provider.name)
                    log(f"{provider.name}: tools API не принят ({error}); "
                        "работаю в JSON-режиме")
                    return choice, provider, True
                except ConnectionError as second_error:
                    last_error = second_error
    raise ConnectionError(f"ни один провайдер не ответил: {last_error}")


def run(pool: LlmPool, toolbox: Toolbox, goal: str) -> str:
    messages: list[dict] = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": goal},
    ]
    tools_broken: set[str] = set()
    for turn in range(1, MAX_TURNS + 1):
        choice, provider, json_mode = _chat_turn(pool, messages, tools_broken)
        if json_mode:
            choice = _json_mode_message(choice)
            if choice is None:
                return "модель вернула пустой ответ в JSON-режиме — стоп"
        messages.append(choice)
        tool_calls = choice.get("tool_calls") or []
        content = (choice.get("content") or "").strip()
        if not tool_calls:
            log(f"петля завершена на ходе {turn} (провайдер {provider.name})")
            return content or "(пустой ответ модели)"
        log(f"ход {turn}: {len(tool_calls)} вызов(ов) инструментов")
        for call in tool_calls:
            function = call.get("function", {})
            name = function.get("name", "?")
            arguments = function.get("arguments", "{}")
            log(f"  → {name} {arguments[:160]}")
            result = dispatch(toolbox, name, arguments)
            log(f"  ← {result[:160]}")
            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "content": result,
            })
    return ("ЛИМИТ ХОДОВ ИСЧЕРПАН (" + str(MAX_TURNS) +
            "). Прервано; смотри audit.log и журнал stderr для состояния.")


def main() -> None:
    parser = argparse.ArgumentParser(description="1c-vibe agent loop")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", help="ключ задачи Jira, например INTAIDEV-101")
    group.add_argument("--goal", help="свободная цель для агента")
    parser.add_argument("--workspace", default="dump",
                        help="рабочий каталог (создаётся при отсутствии)")
    args = parser.parse_args()

    goal = (f"Выполни задачу {args.task} по процедуре скилла: прочитай задачу "
            f"(jira_client.py get {args.task}), подготовь ветку, внеси правки, "
            "проверь себя, опубликуй MR и прокомментируй задачу."
            if args.task else args.goal)

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    toolbox = Toolbox(workspace)
    pool = pool_from_env()
    report = run(pool, toolbox, goal)
    print("\n=== ОТЧЁТ АГЕНТА ===")
    print(report)


if __name__ == "__main__":
    main()
