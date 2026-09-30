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


def run(pool: LlmPool, toolbox: Toolbox, goal: str) -> str:
    messages: list[dict] = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": goal},
    ]
    for turn in range(1, MAX_TURNS + 1):
        choice, provider = pool.chat(messages, tools=TOOLS_SCHEMA)
        messages.append(choice)
        tool_calls = choice.get("tool_calls") or []
        content = (choice.get("content") or "").strip()
        if not tool_calls:
            log(f"петля завершена на ходе {turn} (провайдер {provider})")
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
