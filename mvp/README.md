# MVP 1c-vibe: «Jira → код → MR → комментарий»

Каркас первого MVP: агент берёт задачу из Jira, правит код демо-репозитория
GitLab, открывает Merge Request и оставляет комментарий в задаче.
План и архитектура — в `docs/mvp-plan.md`.

## Структура

```
mvp/
  envconfig.py            — загрузчик .env (без зависимостей)
  jira_client.py          — Jira REST: get / comment
  gitlab_client.py        — GitLab REST: whoami / project / create-mr
  publish.py              — ветка → commit → push → MR → комментарий в Jira
  skills/1c-vibe-demo/    — скилл агента (инструкция для харнеса)
  demo-project/           — содержимое демо-репозитория (контент для GitLab)
  .env.example            — шаблон настроек (реальный .env в git не попадает)
```

## Быстрый старт

1. **Настрой окружение:**
   ```
   cp .env.example .env   # и заполни JIRA_URL/JIRA_TOKEN, GITLAB_URL/GITLAB_TOKEN
   ```
   Токены: Jira — Personal Access Token в профиле; GitLab — Access Token со scope `api`.

2. **Проверь доступы:**
   ```
   python3 gitlab_client.py whoami
   python3 jira_client.py get INTAIDEV-101
   ```

   Для Jira Cloud текущий MVP нужно переключить с Bearer/API v2 на
   Basic + API v3/ADF; сначала уточни тип Jira. Из коробки реализован Server/DC.

3. **Создай демо-репозиторий** в GitLab (пустой, без README) и запушь туда
   содержимое `demo-project/`:
   ```
   git init /tmp/1c-vibe-demo && cd /tmp/1c-vibe-demo
   cp -R <путь>/mvp/demo-project/. .
   git add -A && git commit -m "chore: demo project"
   git remote add origin <url>
   git push -u origin master   # или main
   ```

4. **Заведи демо-задачи в Jira** — тексты в `demo-project/tasks/demo-tasks.md`.

5. **Подключи скилл** `skills/1c-vibe-demo/SKILL.md` к своему харнесу
   (opencode/DeepSeek Harness/Claude Code — это обычная инструкция) и попроси:
   «выполни задачу INTAIDEV-101 по скиллу 1c-vibe-demo».

## Ручная проверка workflow (без агента)

```
cd /tmp/1c-vibe-demo
python3 <путь>/mvp/publish.py INTAIDEV-101 --repo . --prepare
echo "// тест" >> Catalogs/Товары/Ext/ManagerModule.bsl
python3 <путь>/mvp/publish.py INTAIDEV-101 "проверка публикации" --repo .
```

Первая команда создаст чистую ветку `agent/INTAIDEV-101`; вторая — коммит,
MR и комментарий в Jira. Разделение защищает незакоммиченные правки от
случайного сброса при переключении ветки.

## Локальные тесты каркаса

```
python3 -m unittest discover -s tests -v
```

## Заметки

- Python 3.10+ (в аннотациях используется синтаксис `X | None`), внешних пакетов нет.
- `publish.py` для HTTPS использует временный askpass: токен не попадает в URL,
  аргументы процесса или git-конфиг. Для SSH используется обычный `origin`.
- Перед HTTPS push хост `origin` сверяется с `GITLAB_URL`.
- Если Jira оказалась Cloud, а не Server — см. комментарий в `jira_client.py`.
