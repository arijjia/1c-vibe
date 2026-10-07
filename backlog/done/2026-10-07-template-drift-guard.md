---
schema: 1.0.0
id: template-drift-guard
title: "Процедура anti-drift: сверка репо 1c-vibe и шаблона agctl"
status: done
priority: P2
size: M
area: agctl
repo: 1c-vibe
created: 2026-10-07
updated: 2026-10-07
tags: ["plan", "process"]
depends: []
---

## Описание

Скрипт или чеклист сверки 1c-vibe/mvp против agctl internal/assets/templates/1c-vibe (образец: diff -rq), запускать перед каждым релизом бинаря. Живёт до T4 (шаблоны из git-URL).

## Критерии готовности

- (сформулировать)

## Журнал

- 2026-10-07: создано (`backlog new`).
- 2026-10-07: **in-progress** — взято в работу
- 2026-10-07: Готово: bin/check-1c-vibe-sync.sh + make tpl_check_sync. Проверен PASS на текущем состоянии и FAIL на намеренном дрейфе (откачено). По пути пойман и удалён реальный __pycache__ от прогонов pytest.
- 2026-10-07: **done** — Anti-drift работает: PASS+FAIL проверены
