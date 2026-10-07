---
schema: 1.0.0
id: jira-run-poller
title: "Поллер agent-run: search_issues + очередь jira_runs в agctl"
status: done
priority: P2
size: M
area: agctl
repo: 1c-vibe
created: 2026-10-07
updated: 2026-10-07
tags: ["jira-trigger"]
depends: []
---

## Описание

search_issues(JQL) в jira_client + миграция 004 jira_runs + тикер в agctl (AGCTL_JIRA_* env). Инжект в dsh — следующий шаг (проба endpoints на живом контейнере).

## Критерии готовности

- (сформулировать)

## Журнал

- 2026-10-07: создано (`backlog new`).
- 2026-10-07: Сделано: jira_client.search_issues (+CLI search, живой прогон по VPN: 4 задачи проекта, по метке пусто), тест 14 passed; agctl: 004_jira_runs.sql, JiraRunInsert/Update/List (+тест, идемпотентность), server/jirapoll.go (тикер 60с, env AGCTL_JIRA_URL/TOKEN/JQL/WORKSPACE, Bearer, audit jira.run.queued), StartBackground подключён. go build/test/vet зелёные, tpl_check_sync PASS.
- 2026-10-07: **done** — Доставка до agctl работает; инжект промпта в dsh — следующая карточка после пробы endpoints
