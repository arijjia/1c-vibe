---
schema: 1.0.0
id: workspace-cli
title: "CLI-команда agctl: создать/запустить рабочее место"
status: done
priority: P2
size: M
area: agctl
repo: 1c-vibe
created: 2026-10-07
updated: 2026-10-07
tags: ["plan", "cli"]
depends: []
---

## Описание

Работа в ../agctl. Команда поверх тех же Provision+Start (сейчас только serve/migrate/backlog/version): создать место из шаблона 1c-vibe, напечатать ссылку dsh web. Для видео не блокирует.

## Критерии готовности

- (сформулировать)

## Журнал

- 2026-10-07: создано (`backlog new`).
- 2026-10-07: **in-progress** — взято в работу
- 2026-10-07: Реализовано: agctl workspace create (cmd/agctl/workspace.go) — синхронный аналог provisionJob: Provision+Start, секрет в SQLite, квота, ожидание boot-токена, печать ссылки. Проверено: сборка, gofmt чист, error-пути (шаблон/юзер). Живой create с docker — в clean-machine-run.
- 2026-10-07: **done** — Реализовано и проверено (сборка+валидации+go test); живой прогон — в clean-machine-run
