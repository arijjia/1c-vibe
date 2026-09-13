# MVP 1c-vibe: «Jira → код → MR → комментарий»

Каркас первого MVP: агент берёт задачу из Jira, правит код демо-репозитория
GitLab, открывает Merge Request и оставляет комментарий в задаче.
План и архитектура — в `docs/mvp-plan.md`.

## Структура

```
mvp/
  envconfig.py            — загрузчик .env (без зависимостей)
  jira_client.py          — Jira REST: whoami / get / comment (+ create для seed)
  gitlab_client.py        — GitLab REST: whoami / project / create-mr
  publish.py              — ветка → commit → push → MR → комментарий в Jira
  seed_demo.py            — создание трёх демо-задач в Jira
  skills/1c-vibe-demo/    — скилл агента (инструкция для харнеса)
  demo-project/           — содержимое демо-репозитория (контент для GitLab)
  .env.example            — шаблон настроек (реальный .env в git не попадает)
```

## Быстрый старт

1. **Настрой окружение:**
   ```
   cp .env.example .env   # и заполни доступы (Jira, GitLab, модель)
   chmod 600 .env
   ```
   Токены: Jira — PAT в профиле (или логин+пароль Basic), GitLab — Access Token scope `api`.

2. **Проверь доступы:**
   ```
   python3 gitlab_client.py whoami
   python3 jira_client.py whoami
   python3 seed_demo.py INTAIDEV --dry
   ```

3. **Создай демо-репозиторий** в GitLab (пустой, без README) и запушь туда
   содержимое `demo-project/`:
   ```
   git init /tmp/1c-vibe-demo && cd /tmp/1c-vibe-demo
   cp -R <путь>/mvp/demo-project/. .
   git add -A && git commit -m "chore: demo project"
   git remote add origin <url>
   git push -u origin master   # или main
   ```

4. **Создай демо-задачи:** `python3 seed_demo.py INTAIDEV`
   (тексты — в `demo-project/tasks/demo-tasks.md`).

5. **Подключи скилл** `skills/1c-vibe-demo/SKILL.md` к своему харнесу
   (opencode/DeepSeek Harness/Claude Code — это обычная инструкция) и попроси:
   «выполни задачу INTAIDEV-101 по скиллу 1c-vibe-demo».

## Ручная проверка publish (без агента)

```
cd /tmp/1c-vibe-demo
echo "// тест" >> Catalogs/Товары/Ext/ManagerModule.bsl
python3 <путь>/mvp/publish.py INTAIDEV-101 "проверка публикации" --repo .
```

Скрипт создаст ветку `agent/INTAIDEV-101`, MR и комментарий в Jira.

## Заметки

- Python 3.10+ (в аннотациях используется синтаксис `X | None`), внешних пакетов нет.
- `publish.py` пушит токеном в URL одного push-а, токен в конфиг git не пишется.
- Авторизация Jira: PAT (Bearer) либо логин+пароль (Basic) — см. `.env.example`.
