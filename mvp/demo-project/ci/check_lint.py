#!/usr/bin/env python3
"""Валит CI, если в отчёте BSL Language Server есть диагностики уровня Error.

Использование: python ci/check_lint.py bsl-report

Аргумент — файл отчёта или каталог с отчётами (json). Формат отчёта менялся
между версиями BSL LS, поэтому парсер терпимый: рекурсивно ищет по JSON любые
поля "severity" со значением error (регистр не важен).
Если отчётов нет — ошибка (анализ должен выполняться всегда).
Если поля severity не найдены — предупреждение без падения.
"""

import glob
import json
import os
import sys

ERROR_VALUES = {"error", "1"}  # числовые severity: 1 = Error в LSP


def iter_severities(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key.lower() == "severity":
                yield value
            else:
                yield from iter_severities(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_severities(item)


def collect(path):
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "**", "*.json"), recursive=True))
    else:
        files = [path]
    severities = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                severities.extend(iter_severities(json.load(fh)))
        except (OSError, json.JSONDecodeError) as e:
            print(f"ВНИМАНИЕ: не удалось разобрать {f}: {e}")
    return severities


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "bsl-report"
    if not os.path.exists(path):
        print(f"ОШИБКА: отчёт не найден: {path} — анализ не выполнился?")
        sys.exit(1)

    severities = collect(path)
    if not severities:
        print("ВНИМАНИЕ: поля severity не найдены — проверьте формат отчёта BSL LS.")
        print("Пайплайн не упал, но убедитесь, что анализ реально выполнился.")
        return

    errors = [s for s in severities if str(s).lower() in ERROR_VALUES]
    print(f"Диагностик: {len(severities)}, из них уровня Error: {len(errors)}")
    if errors:
        print("Есть ошибки — смотрите артефакт отчёта.")
        sys.exit(1)
    print("Ошибок уровня Error нет.")


if __name__ == "__main__":
    main()
