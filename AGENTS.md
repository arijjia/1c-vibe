# AGENTS.md — окружение агента 1c-vibe (ЦИТ ТюмГУ)

> Целевой путь — только через agctl (`docs/agctl-only.md`). Процедура ниже —
> legacy B2 («изолированный dsh-агент»): действует переходно, пока нет agctl
> CLI, затем заменяется agctl-онбордингом. Режимы B1/B3 не использовать.

Ты — агент 1c-vibe, работаешь в репозитории проекта 1c-vibe.
Ниже — всё, что нужно для работы. НЕ ищи инструменты по файловой системе —
они уже здесь.

## Кто ты и где ты

- Корень репозитория = текущий рабочий каталог запуска.
- `mvp/` — CLI-скрипты проекта (jira_client, gitlab_client, publish, lint).
- `agent/` — LEGACY B3 (самописная петля, не использовать; агент работает в dsh web).
- `mvp/dump/` — рабочие клоны для правок кода.

## Доступы (не искать — уже настроены)

- Jira: https://jira.utmn.ru, проект INTAIDEV (Basic-авторизация).
- GitLab: https://gitlab.utmn.ru, проект rd/1c-ai/1c-vibe-demo.
- Учётные данные: в `mvp/.env` (JIRA_URL/JIRA_USER/JIRA_PASSWORD,
  GITLAB_URL/GITLAB_TOKEN). Скрипты читают его сами через
  `mvp/envconfig.py`. Содержимое .env НИКОГДА не печатай в ответах.

## Задачи Jira

Ключи задач: `INTAIDEV-<номер>` (например INTAIDEV-4; не «intadev»).
Прочитать задачу:

```
python3 mvp/jira_client.py get INTAIDEV-4
```

## Процедура выполнения задачи (см. mvp/skills/1c-vibe-demo/SKILL.md)

1. `python3 mvp/jira_client.py get <KEY>` — прочитай постановку.
2. Склонируй при необходимости демо-репо в `mvp/dump/1c-vibe-demo`
   (origin: https://gitlab.utmn.ru/rd/1c-ai/1c-vibe-demo.git) и подготовь
   ветку: `python3 mvp/publish.py <KEY> --repo mvp/dump/1c-vibe-demo --prepare`
   (для prepare нужен только GitLab, токен в .env).
3. Внеси правки в XML/BSL по постановке, стиль — как в окружающем коде.
4. Проверь себя: `python3 mvp/lint.py --src <путь к выгрузке>` (BSL LS,
   fail-closed). Исправь ошибки уровня Error.
5. Опубликуй: `python3 mvp/publish.py <KEY> "резюме" --repo mvp/dump/1c-vibe-demo`
   — коммит, push, MR, комментарий в Jira.
6. Доложи пользователю: ссылка на MR, что проверено.

## Правила

- При неоднозначной постановке — спроси, не выдумывай.
- MR — единственный путь публикации; основную ветку не трогать.
- Токены и пароли не выводить в чат и не коммитить.
- Модели: провайдер agctl (qwen-*), настроен в этом окружении по умолчанию.
