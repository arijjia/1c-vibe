---
schema: 1.0.0
id: jira-trigger-spike
title: "Спайк: Jira-триггер фонового запуска агента"
status: done
priority: P2
size: M
area: meta
repo: 1c-vibe
created: 2026-10-07
updated: 2026-10-07
tags: ["plan", "research"]
depends: []
---

## Описание

4 вопроса: webhook vs поллер (JQL labels=agent-run); чем инжектить задачу в dsh (session.prompt/headless/exec); связка задача↔workspace/session; кто вправе вешать метку. Сервисный аккаунт 1c-agent + метка agent-run.

## Критерии готовности

- (сформулировать)

## Журнал

- 2026-10-07: создано (`backlog new`).
- 2026-10-07: **in-progress** — взято в работу
- 2026-10-07: Ответы (все сверены с кодом). 1) Доставка: поллер для MVP — webhook требует админа Jira и inbound-доступность agctl (ноутбук за NAT отпадает); поллер = новый search_issues(JQL) в jira_client.py (сейчас есть только get/comment/create) + цикл рядом с autosave, JQL labels=agent-run. 2) Инжект: agctl уже держит bearer-токен dsh web (wsToken из логов) и ходит на 127.0.0.1:порт с хоста — первый кандидат HTTP-инжект в сессию (какие endpoints принимают промпт в dsh 0.1.7-rc.2 — проба на машине D); запасной — новый Runtime.Exec в dockerrt (сейчас Exec нет) + dsh headless внутри контейнера. 3) Маппинг: новая миграция SQL (store.go: user_version-миграции из файлов) — таблица jira_key↔workspace/session/статус; воркспейс один на проект, сессия на задачу. 4) Права: сервисный аккаунт Jira (browse+comment+edit labels), GitLab PAT api (уже требуется); метку вправе вешать любой с edit issues; агент трогает только помеченные. Предусловие: контейнер должен видеть контур (VPN) —inherit от хоста.
- 2026-10-07: **done** — Спайк закрыт: 4 ответа в журнале, реализация — отдельными задачами
