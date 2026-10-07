---
schema: 1.0.0
id: template-sync
title: "Синхронизировать шаблон 1c-vibe в agctl с репозиторием 1c-vibe"
status: done
priority: P1
size: M
area: agctl
repo: 1c-vibe
created: 2026-10-07
updated: 2026-10-07
tags: ["plan", "sync"]
depends: []
---

## Описание

Работа в ../agctl. Перекопировать mvp/тулкит, скилл и демо-проект в internal/assets/templates/1c-vibe (раскладка scripts/ вместо mvp/), вручную свести 6 мест дрейфа SKILL.md и .env.example. Проверить: go test ./... в agctl + pytest tests/ шаблона.

## Критерии готовности

- (сформулировать)

## Журнал

- 2026-10-07: создано (`backlog new`).
- 2026-10-07: **in-progress** — взято в работу
- 2026-10-07: Проверено: .py/tests в шаблоне байт-в-байт равны репо; SKILL.md расходится только путями mvp→scripts и python3 вместо run_cli (корректная адаптация). Исправлено: удалён __pycache__ из шаблона (попадал бы в go:embed), добавлен demo-project/.gitignore, .env.example досинхронизирован, .gitignore agctl покрывает __pycache__/*.pyc/.venv. Тесты шаблона: 13 passed.
- 2026-10-07: **done** — Шаблон сверен с репо, мусор убран, тесты шаблона 13 passed, go test зелёный
