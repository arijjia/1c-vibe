#!/usr/bin/env python3
"""Валит CI, если в отчёте BSL Language Server есть диагностики уровня Error.

Формат отчёта менялся между версиями BSL LS, поэтому парсер терпимый:
рекурсивно ищет по JSON любые поля "severity" со значением error
(регистр не важен). Если структура отчёта не распознана — предупреждаем,
но не валим пайплайн (чтобы не блокировать демо обновлением формата).

Использование: python ci/check_lint.py bsl-lint.json
"""

import json
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


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "bsl-lint.json"
    with open(path, encoding="utf-8") as f:
        report = json.load(f)

    severities = list(iter_severities(report))
    if not severities:
        print("ВНИМАНИЕ: поля severity не найдены — проверьте формат отчёта BSL LS.")
        print("Пайплайн не упал, но убедитесь, что анализ реально выполнился.")
        return

    errors = [s for s in severities if str(s).lower() in ERROR_VALUES]
    total = len(severities)
    print(f"Диагностик: {total}, из них уровня Error: {len(errors)}")
    if errors:
        print("Есть ошибки — смотрите артефакт bsl-lint.json.")
        sys.exit(1)
    print("Ошибок уровня Error нет.")


if __name__ == "__main__":
    main()
