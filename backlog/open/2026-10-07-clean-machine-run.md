---
schema: 1.0.0
id: clean-machine-run
title: "Прогон agctl+1c-vibe на чистой машине по e2e-гайду"
status: open
priority: P1
size: M
area: 1c-vibe
repo: 1c-vibe
created: 2026-10-07
updated: 2026-10-07
tags: ["plan", "e2e"]
depends: []
---

## Описание

Сборка, serve, регистрация, создание 1c-vibe-места, scripts/.env, pytest внутри, демо-задача до MR. Все затыки — в чеклист. База: agctl-hq/docs/agctl-mvp-e2e-test-guide.md, изолированный TEST_HOME.

## Критерии готовности

- (сформулировать)

## Журнал

- 2026-10-07: создано (`backlog new`).
- 2026-10-07: Готов хэндовер: docs/handover-mvp.md — сводка сессии, декомпозиция, часть 1 (эта машина, INTAIDEV-3 — единственная демо-задача без MR), часть 2 (Windows-VM: WSL2 надёжно / нативно эксперимент), ответы на вопросы. Сценарий съёмки — video-guide v2 (10 сцен).
