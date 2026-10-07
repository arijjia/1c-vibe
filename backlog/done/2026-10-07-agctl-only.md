---
schema: 1.0.0
id: agctl-only
title: "1c-vibe только через agctl: закрепить решение и legacy-карту B1–B3"
status: done
priority: P1
size: M
area: meta
repo: 1c-vibe
created: 2026-10-07
updated: 2026-10-07
tags: ["agctl", "docs"]
depends: []
---

## Описание

Решение: единственный целевой путь — agctl (сначала CLI-first без веб-панели ЛК, затем сервер). B1/B2/B3 — legacy, не поддерживаются. Нужно закрепить в доках + разметить какой код legacy.

## План

- Создать `docs/agctl-only.md`: решение + legacy-карта B1–B3 + ACTIVE-список + фиксация про секреты.
- README: структура + целевой запуск через agctl, B3 помечен legacy.
- `docs/onboarding.md`, `AGENTS.md`: legacy-баннеры; `agent/` помечен LEGACY B3.
- Код legacy не удалять (отдельный аудит).

## Критерии готовности

- `docs/agctl-only.md` существует и перечисляет каждый legacy-путь B1–B3 и ACTIVE-пути.
- README/AGENTS.md/onboarding.md ссылаются на решение, противоречий «agent/ — целевая петля» не осталось.
- `backlog check` зелёный.

## Не делать

- Не удалять код `agent/`, `dsh-home/`, `scripts/cleanroom-dsh.sh` (только маркировка).
- Не менять процедуру `mvp/` и контурные скрипты.

## Журнал

- 2026-10-07: создано (`backlog new`).
- 2026-10-07: **in-progress** — взято в работу
- 2026-10-07: доки закреплены (agctl-only.md + баннеры); проверка `backlog check` перед закрытием
- 2026-10-07: **done** — Решение закреплено: docs/agctl-only.md + баннеры в README/AGENTS.md/onboarding.md; legacy-код не удалён
