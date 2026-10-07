---
schema: 1.0.0
id: live-jira-mr
title: "Живой цикл Jira→MR агентом в agctl-воркспейсе"
status: open
priority: P1
size: M
area: 1c-vibe
repo: 1c-vibe
created: 2026-10-07
updated: 2026-10-07
tags: ["plan", "e2e"]
depends: ["clean-machine-run"]
---

## Описание

Нужны VPN + токены Jira/GitLab. Агент целиком: INTAIDEV-N → ветка → правка → линт → MR → комментарий в Jira. Критерий: ссылки на MR и задачу, проверки зелёные.

## Критерии готовности

- (сформулировать)

## Журнал

- 2026-10-07: создано (`backlog new`).
- 2026-10-07: Пробы из домашней сети (без VPN): jira.utmn.ru отвечает 302, gitlab и litellm — 000 (недоступны); Jira API даёт 403 (похоже на WAF без VPN). Вывод: живой цикл только с VPN — чистая машина должна быть в контуре.
