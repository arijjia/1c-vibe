# Онбординг с чистого компьютера: от клона репы до «задача из Jira → MR»

> **Основной и поддерживаемый режим отдела 1С** (решение владельца
> 2026-10-14): локальная установка из клона репозитория — git + Node.js +
> dsh на компьютере разработчика, без Docker. Историческое решение
> «только через agctl» (2026-10-07) отменено решением владельца.

Для кого: человек с доступами к Jira и GitLab (UTMN), пустой компьютер
(macOS / Windows / Linux). Итог: агент в DeepSeek Harness берёт задачу
`INTAIDEV-N`, правит демо-репо и открывает Merge Request.

Время на всё: **один вечер** (установка ~20 минут, остальное — проверки).

## 0. Что понадобится

- Терминал; доступ в сеть `utmn.ru` (**корпоративный VPN** — включи его
  на время работы: Jira/GitLab/модель доступны только через него).
- Node.js 20+ (для харнеса) — ставим ниже.
- Java 11+ (для BSL-линтера; сам jar линтера скачается при первом
  запуске `lint.py`).
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

**Java 11+** (нужна линтеру BSL):

```
macOS:   brew install openjdk@17
Windows: winget install Microsoft.OpenJDK.17
Linux:   sudo apt install default-jdk
```

Проверка инструментов: `git --version && uv --version && node --version && java -version`.

## 2. Репозиторий MVP

```
git clone https://github.com/arijjia/1c-vibe.git
cd 1c-vibe/mvp
uv sync                      # создаст .venv; нужный Python uv поставит сам
```

(вариант по SSH: `git clone git@github.com:arijjia/1c-vibe.git`)

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
dsh --version        # проверка: должно напечатать версию, например 0.2.0-rc.2
```

Если `npm: command not found` — не установлен Node.js, вернись к шагу 1.

### 4.2 Запуск: изолированный дом 1c-vibe (важно!)

Бинарь `dsh` на машине один (глобальный npm-пакет), а «личность» ему
задаёт домашний каталог (`DSH_HOME`). Голый `dsh web` возьмёт стандартный
`~/.dsh` и порт 3080: если там уже работает твой личный харнес — получишь
`EADDRINUSE`, а главное — смешаешь личные настройки с 1С. Для 1c-vibe
запускай в изоляции:

**Вариант А — постоянный дом проекта `dsh-home/` (повседневная работа):**

```bash
# из любого каталога репы — git сам найдёт корень
DSH_HOME="$(git rev-parse --show-toplevel)/dsh-home" dsh web --port 3099 --no-open
# Windows PowerShell: cd в корень репы, затем
#   $env:DSH_HOME="$PWD\dsh-home"; dsh web --port 3099 --no-open
```

Открой напечатанную ссылку — в ней одноразовый токен входа. Сессии, креды
и настройки живут в `dsh-home/` (в git попадает только `cordis.patch.yml`,
остальное в `.gitignore`); личный `~/.dsh` и порт 3080 не затрагиваются.

**Вариант Б — «чистая комната» (проверка глазами нового пользователя):**

```bash
scripts/cleanroom-dsh.sh            # свежий дом ~/.dsh-cleanroom, порт :3098
scripts/cleanroom-dsh.sh --reset    # снести и пересоздать с нуля
```

Скрипт сам пропишет провайдера utmn, спросит ключ LiteLLM (или возьмёт
из env `LITELLM_API_KEY`) и установит скилл `1c-vibe-demo`.

### 4.3 Модель: провайдер utmn (LiteLLM)

Нужны два файла в доме харнеса (вариант А — `dsh-home/`, чистая установка —
`~/.dsh`; чистая комната вариант Б прописывает их сама). Создай/дополни
их любым редактором.

**`<дом>/settings.yaml`** (вариант А — `dsh-home/settings.yaml`) — внутри секции `llm-pi-ai.providers` описать
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

**`<дом>/.credentials.yaml`** — сюда и только сюда ключ (секция `refs`;
файл в git не попадает, ключ не вставляй в код и чаты):

```yaml
version: 1
refs:
  LITELLM_API_KEY: "sk-..."
```

**Модель по умолчанию.** В веб-морде (`Settings → Models`) выбери
`utmn / qwen-3.8-deep` для агента — этого достаточно. Либо пропиши
принудительно файлом `<дом>/utmn-model.patch.yml`:

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
Если ответа нет — проверь **корпоративный VPN**: модель обращается к сети
в момент запроса, без VPN до `litellm-dev.utmn.ru` не достучаться.

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

## 7. Чистая комната (для владельца репы)

Чтобы увидеть харнес глазами коллеги с чистым компом — не трогая свой боевой
инстанс (`~/.dsh`, порт 3080):

```
scripts/cleanroom-dsh.sh            # создаст ~/.dsh-cleanroom и поднимет :3098
scripts/cleanroom-dsh.sh 3100       # на другом порту
scripts/cleanroom-dsh.sh --reset    # снести и пересоздать с нуля
```

Скрипт кладёт в отдельный DSH_HOME только необходимое: провайдер utmn,
ключ (из env `LITELLM_API_KEY` или спросит), скилл 1c-vibe-demo. Запустит
`dsh web --no-open` — открой напечатанную ссылку (в ней одноразовый токен
доверия; голый URL без токена даст 401).

Заметки:
- два инстанса не конфликтуют: у каждого свой порт и свой DSH_HOME;
- рабочая папка сессии — корень этой репы: клонируй демо-репо в `mvp/dump/`,
  как в §6, и попроси чистый агент выполнить задачу целиком;
- `--reset` стирает сессии и правки чистой комнаты — это ожидаемо.

## 8. Чек-лист: проверка, что всё работает

Пять уровней, идём сверху вниз; следующий уровень — только если
предыдущий зелёный. Все команды — из `mvp/`, через `uv run python3 …`.
Проверяться только на **демо-проекте** и тестовых задачах.

### Уровень 1 — окружение живо (~2 минуты)

| # | Команда | Зелёный результат |
|---|---|---|
| 1 | `uv run python3 gitlab_client.py whoami` | отвечает твоё имя → GitLab-токен жив |
| 2 | `uv run python3 gitlab_client.py project rd/1c-ai/1c-vibe-demo` | видит демо-проект |
| 3 | `uv run python3 jira_client.py get INTAIDEV-1` | видит задачу → Jira-токен жив |
| 4 | `uv run python3 -m pytest tests/ -q` | **14 passed** — тулкит цел |
| 5 | `uv run python3 lint.py --src demo-project` | линтер отработал без падения (Java + jar ок) |

### Уровень 2 — ручной цикл без агента (проверяем тулкит)

На тестовой задаче демо-проекта:

```
uv run python3 publish.py <KEY> --repo dump/1c-vibe-demo --prepare
# → появилась ветка agent/<KEY>; внеси маленькую правку в XML/BSL
uv run python3 publish.py <KEY> "проверка публикации" --repo dump/1c-vibe-demo
```

Зелёный результат: в GitLab появился **MR**, в Jira — **комментарий**
со ссылкой.

### Уровень 3 — цикл с агентом (проверяем агента)

`dsh web` запущен, скилл подключён (§5), VPN включён. Фраза:
**«пофикси `<KEY>` и сделай MR»**. Зелёный результат:

- работа шла в ветке `agent/<KEY>` — основная ветка не тронута;
- правки в стиле окружения (русский синтаксис, табы);
- `lint.py` без ошибок уровня Error;
- MR создан, в Jira прилетел комментарий со ссылкой;
- **ты ревьюишь и мержишь** — агент в основную ветку не пишет никогда.

### Уровень 4 — новый человек / новый компьютер

`scripts/cleanroom-dsh.sh` — «чистая комната» (§7): свежий харнес с
чистым домом, скилл и провайдер ставятся автоматически. Критерий —
коллега с нуля проходит путь «клон → задача → MR» за один вечер.

### Уровень 5 — регресс после любых изменений

Повторить уровни 1 и 2 на тестовой задаче; при сомнениях — уровень 4.
