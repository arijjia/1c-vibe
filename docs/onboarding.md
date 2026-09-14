# Онбординг с чистого компьютера: от клона репы до «задача из Jira → MR»

Для кого: человек с доступами к Jira и GitLab (UTMN), пустой macOS.
Итог: агент в DeepSeek Harness берёт задачу `INTAIDEV-N`, правит демо-репо
и открывает Merge Request.

## 0. Что понадобится

- macOS с терминалом; доступ в сеть `utmn.ru` (при необходимости — VPN).
- Логин/токены:
  - Jira Personal Access Token: профиль пользователя → «Персональные токены».
  - GitLab Personal Access Token со scope `api`: GitLab → Preferences → Access Tokens.
  - Ключ LiteLLM (`sk-...`) — выдаёт администратор `litellm-dev.utmn.ru`.

## 1. Инструменты

```
# uv (управляет питоном сам, системный Python не нужен)
brew install uv git
# git настрой под себя, иначе будут проблемы с commit/push
git config --global user.name "Имя Фамилия"
git config --global user.email "you@utmn.ru"
```

## 2. Репозиторий MVP

```
git clone git@gitlab.utmn.ru:<namespace>/1c-vibe.git
cd 1c-vibe/mvp
uv sync                      # создаст .venv по uv.lock
```

Проверка, что клиенты вообще живы:

```
uv run python3 gitlab_client.py whoami
```

Ожидаемо: `GITLAB_URL — заглушка...` — переходим к настройкам.

## 3. Доступы к Jira и GitLab (mvp/.env)

```
cp .env.example .env
```

Заполни в `mvp/.env`:

```
JIRA_URL=https://jira.utmn.ru            # реальный адрес вашей Jira
JIRA_TOKEN=<Personal Access Token>
GITLAB_URL=https://gitlab.utmn.ru
GITLAB_TOKEN=<token со scope api>
DEMO_PROJECT=rd/1c-ai/1c-vibe-demo
```

`.env` в git не попадает (проверь `git check-ignore .env` — должно молчать).
Никогда не вставляй токены в код и коммиты.

Проверка:

```
uv run python3 gitlab_client.py whoami
uv run python3 gitlab_client.py project rd/1c-ai/1c-vibe-demo
uv run python3 jira_client.py get INTAIDEV-1
```

Если `CERTIFICATE_VERIFY_FAILED` — ничего отключать не надо: клиенты уже
используют certifi; для корпоративного CA укажи `HTTPS_CA_BUNDLE=/путь/ca.pem`.

## 4. DeepSeek Harness (dsh) и модель

Харнес ставится отдельно от этой репы (инструкция — у владельца установки:
`/opt/homebrew/lib`, веб-морда `http://127.0.0.1:3080`). Первый запуск:

```
dsh
```

Дальше — конфигурация модели. Нужны два файла в `~/.dsh`:

**`~/.dsh/settings.yaml`** — описать провайдера `utmn` (OpenAI-совместимый
LiteLLM) внутри `llm-pi-ai.providers`:

```yaml
    utmn:
      apiKeyEnv: LITELLM_API_KEY
      api: openai-completions
      baseURL: https://litellm-dev.utmn.ru/v1
      models:
        - id: qwen-3.8-deep
          name: Qwen 3.8 Deep
          contextWindow: 262144
          maxTokens: 65536
        - id: qwen-3.8-fast
          name: Qwen 3.8 Fast
          contextWindow: 262144
          maxTokens: 65536
```

**`~/.dsh/.credentials.yaml`** — сюда и только сюда ключ (секция `refs`):

```yaml
refs:
  LITELLM_API_KEY: "sk-..."
```

Выбор модели по умолчанию — переопределение `agent-default-model`
(в этой установке это `~/.dsh/utmn-model.patch.yml`):

```yaml
- id: agent-default-model
  config:
    provider: utmn
    model: qwen-3.8-deep
```

После правки конфигов перезапусти харнес. В списке моделей появятся
qwen-модели; выбери `qwen-3.8-deep` как рабочую.

## 5. Скилл агента

Скилл `mvp/skills/1c-vibe-demo/SKILL.md` — пошаговая инструкция агента:
прочитать задачу → подготовить ветку `agent/INTAIDEV-N` → править XML/BSL →
`publish.py` (commit → push → MR → комментарий в Jira). Положи его в каталог
скиллов харнеса (или укажи путь в prompt'е) — дальше агенту достаточно сказать:
«выполни задачу INTAIDEV-2 по скиллу 1c-vibe-demo».

## 6. Типовой цикл работы

1. Открыл харнес, написал: «пофикси INTAIDEV-2 и сделай MR».
2. Агент сам: читает задачу, готовит ветку, правит код, публикует MR,
   комментирует задачу. Тебе остаются ссылки на MR и задачу.
3. Ревьюишь MR в GitLab, мёржишь.

## Частые проблемы

| Симптом | Причина / решение |
|---|---|
| `nodename nor servname` | в `.env` осталась заглушка `example.local` или нет VPN |
| `CERTIFICATE_VERIFY_FAILED` | укажи `HTTPS_CA_BUNDLE` с корпоративным CA |
| Jira 404 «запрос не существует» | такого номера задачи нет — проверь ключ |
| `push` отклонён | нет прав на демо-репо или не создан fork-доступ |
