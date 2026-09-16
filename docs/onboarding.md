# Онбординг с чистого компьютера: от клона репы до «задача из Jira → MR»

Для кого: человек с доступами к Jira и GitLab (UTMN), пустой компьютер
(macOS / Windows / Linux). Итог: агент в DeepSeek Harness берёт задачу
`INTAIDEV-N`, правит демо-репо и открывает Merge Request.

## 0. Что понадобится

- Терминал; доступ в сеть `utmn.ru` (при необходимости — VPN).
- Node.js 20+ (для харнеса) — ставим ниже.
- Логин/токены:
  - Jira Personal Access Token: профиль пользователя → «Персональные токены».
  - GitLab Personal Access Token со scope `api`: GitLab → Preferences → Access Tokens.
  - Ключ LiteLLM (`sk-...`) — выдаёт администратор `litellm-dev.utmn.ru`.

## 1. Инструменты

**Git** — официальный установщик с git-scm.com, либо пакетный менеджер:

```
macOS:  brew install git          # или xcode-select --install
Windows: winget install --id Git.Git
Linux:  sudo apt install git      # или dnf/pacman
```

Настрой под себя, иначе будут проблемы с commit/push:

```
git config --global user.name "Имя Фамилия"
git config --global user.email "you@utmn.ru"
```

**uv** (управляет питоном сам, системный Python не нужен):

```
macOS / Linux:   curl -LsSf https://astral.sh/uv/install.sh | sh
Windows (PowerShell): powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Node.js 20+** (нужен для DeepSeek Harness):

```
macOS:   brew install node@22     # или установщик с nodejs.org
Windows: winget install OpenJS.NodeJS.LTS
Linux:   см. nodejs.org — пакетный менеджер твоего дистрибутива
```

Проверка: `git --version && uv --version && node --version`.

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

## 4. DeepSeek Harness (dsh): установка, настройка, запуск

dsh — это npm-пакет `@deepseek-ai/dsh`, консольная программа поверх Node.js.
Работает на macOS, Windows и Linux.

### 4.1 Установка

```
npm install -g @deepseek-ai/dsh
dsh --version        # проверка: должно напечатать версию, например 0.1.5-rc.1
```

Если `npm: command not found` — не установлен Node.js, вернись к шагу 1.

### 4.2 Запуск

```
dsh web
```

Поднимает веб-интерфейс агента на `http://127.0.0.1:3080` — открой его в
браузере. Терминал при этом держи открытым (там живёт сервер; Ctrl+C — стоп).

Домашний каталог харнеса — `~/.dsh` (Windows: `%USERPROFILE%\.dsh`). Там лежат
настройки, скиллы, сессии и креды. Каталог создаётся при первом запуске.

### 4.3 Модель: провайдер utmn (LiteLLM)

Нужны два файла в `~/.dsh`. Создай/дополни их любым редактором.

**`~/.dsh/settings.yaml`** — внутри секции `llm-pi-ai.providers` описать
провайдера (OpenAI-совместимый LiteLLM):

```yaml
llm-pi-ai:
  providers:
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

**`~/.dsh/.credentials.yaml`** — сюда и только сюда ключ (секция `refs`;
файл в git не попадает, ключ не вставляй в код и чаты):

```yaml
version: 1
refs:
  LITELLM_API_KEY: "sk-..."
```

**Модель по умолчанию.** В веб-морде (`Settings → Models`) выбери
`utmn / qwen-3.8-deep` для агента — этого достаточно. Либо пропиши
принудительно файлом `~/.dsh/utmn-model.patch.yml`:

```yaml
- id: agent-default-model
  config:
    provider: utmn
    model: qwen-3.8-deep
```

После правки конфигов перезапусти `dsh web` (Ctrl+C и снова).

### 4.4 Проверка модели

В веб-морде создай сессию, убедись, что в селекторе моделей выбрана
qwen-модель, и спроси что-нибудь. Если пришёл ответ — модель живая.

## 5. Скилл агента

Скилл `mvp/skills/1c-vibe-demo/SKILL.md` — пошаговая инструкция агента:
прочитать задачу → подготовить ветку `agent/INTAIDEV-N` → править XML/BSL →
`publish.py` (commit → push → MR → комментарий в Jira). Положи его в каталог
скиллов харнеса (или укажи путь в prompt'е) — дальше агенту достаточно сказать:
«выполни задачу INTAIDEV-2 по скиллу 1c-vibe-demo».

## 6. Демо-репозиторий и типовой цикл

Демо-репо клонируется в `mvp/dump/` (каталог в git не попадает — это рабочая
песочница агента):

```
cd mvp/dump
git clone https://gitlab.utmn.ru/rd/1c-ai/1c-vibe-demo.git
```

Дальше работа одной фразой в харнесе:

1. Открыл `dsh web`, написал: «пофикси INTAIDEV-2 и сделай MR».
2. Агент сам: читает задачу, готовит ветку `agent/INTAIDEV-2`, правит код,
   публикует MR, комментирует задачу. Тебе остаются ссылки на MR и задачу.
3. Ревьюишь MR в GitLab, мёржишь.

## Частые проблемы

| Симптом | Причина / решение |
|---|---|
| `nodename nor servname` | в `.env` осталась заглушка `example.local` или нет VPN |
| `CERTIFICATE_VERIFY_FAILED` | укажи `HTTPS_CA_BUNDLE` с корпоративным CA |
| Jira 404 «запрос не существует» | такого номера задачи нет — проверь ключ |
| `push` отклонён | нет прав на демо-репо или не создан fork-доступ |
