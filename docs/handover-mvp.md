# Хэндовер: MVP 1c-vibe через agctl — что сделано, как устроено, что делать руками

Дата: 2026-10-07. Для кого: владелец проекта. Цель документа: за 10 минут понять
всю картину и начать ручной прогон «как разработчик 1С» — сначала на этой
машине, потом на Windows-VM. Сценарий видео — в [video-guide.md](video-guide.md).

---

## 1. Два репозитория и что где лежит

| | `agctl` (платформа) | `1c-vibe` (домен 1С) |
|---|---|---|
| Что это | Go-бинарь: ЛК, provision рабочих мест, Docker-контейнеры, git-память, секреты, аудит, бэклоги | Домен: тулкит Jira/GitLab, скилл агента, демо-проект 1С, доки, бэклог проекта |
| Ключевое | `cmd/agctl`, `internal/{provision,runtime/dockerrt,server,store,secrets,auth,assets}`, `internal/assets/templates/1c-vibe` (снапшот шаблона) | `mvp/` (jira/gitlab/publish/lint/envconfig), `mvp/skills/1c-vibe-demo/SKILL.md`, `mvp/demo-project/`, `docs/`, `backlog/` |
| Чего тут нет | Ничего про 1С | Ничего про изоляцию/provision |

Связка: шаблон 1c-vibe **вшит в бинарь** (`go:embed` из `internal/assets/templates/1c-vibe`).
При создании рабочего места agctl копирует шаблон в репку воркспейса. Обновили
1c-vibe → нужно перекопировать в шаблон и пересобрать бинарь; сверка —
`make -C agctl tpl_check_sync` (ловит дрейф; правила: `*.py`/tests/demo
байт-в-байт, `SKILL.md` — с точностью до `mvp/`→`scripts/`). В будущем (T4)
provision будет тянуть шаблоны из git-URL — тогда снапшот исчезнет.

`agctl-hq` (приватное) — исследования, e2e-гайд, презентации; кода нет.

## 2. Как это работает под капотом (коротко)

1. `agctl serve` → ЛК на `127.0.0.1:8929` (SQLite в `$AGCTL_HOME`, первый
   зарегистрированный = admin).
2. «Создать рабочее место» (или CLI `agctl workspace create`) → agctl создаёт:
   **bare-repo** («эмуляция GitLab», хранит git-историю) + **рабочий клон**
   (его видит агент) + **DSH_HOME** (дом харнеса: настройки, сессии) + контейнер.
3. В контейнер монтируются ровно две вещи: клон → `/workspace`,
   DSH_HOME → `/home/dsh`. Контейнер расходный: данные живут на диске хоста,
   поэтому stop/start/удаление контейнера работу не теряют. Autosave: commit+push
   в bare каждые 2 минуты.
4. Порт dsh web наружу торчит только на `127.0.0.1:<порт>`; ссылка «Открыть»
   содержит одноразовый boot-токен (голый URL = 401).
5. Секреты: LLM-токен шифруется в БД (AES-256-GCM, ключ в
   `$AGCTL_HOME/secrets.key`), в контейнер едет через env
   `AGCTL_LLM_API_KEY`. Известная недоделка: agctl ещё пишет открытую копию в
   `dsh-home/.credentials.yaml` (0600) — перед продом убрать.
6. DSH, Node, python3+pytest — внутри образа `agctl-dsh`; на хосте нужны только
   Go/make/Docker (для сборки) — dsh отдельно ставить НЕ надо.
7. Решение «1c-vibe — только через agctl»: [agctl-only.md](agctl-only.md).
   Старые пути B1 (dsh на хосте), B2 (dsh-home в репе), B3 (петля `agent/`) —
   **legacy**, не поддерживаются, код помечен и лежит до аудита удаления.

## 3. Что я сделала в этой сессии (коммиты, без пушей)

**1c-vibe:**
- `51d82e5` решение «только agctl» + legacy-карта B1–B3 (docs/agctl-only.md);
- `f0fae37` план карточек + черновик video-guide; `ddd7875` актуализация доки;
- `ce7036a` чистка B3-хвостов (LLM_* из .env.example и AGENTS.md);
- `1c96e1b` **`search_issues(JQL)`** в jira_client (+CLI `search`, живой прогон
  по VPN; тесты 14 passed).
- Карточки: 8 задач плана, из них done: template-sync, b3-cleanup,
  template-drift-guard, workspace-cli, jira-trigger-spike, jira-run-poller.

**agctl:**
- `70486cc` синк шаблона 1c-vibe (env.example, demo .gitignore, python-гигиена);
- `a157b0e` **`make tpl_check_sync`** — анти-дрейф сверка репо↔шаблон (PASS/FAIL проверены);
- `704a03a` **`agctl workspace create`** — создание места из CLI без ЛК;
- `8f615c4` фикс порта в комментарии demo.mk (:8929);
- `52c7763` **поллер agent-run**: миграция `004_jira_runs.sql`, store-методы
  (+тест), `internal/server/jirapoll.go` — тикер раз в минуту (env
  `AGCTL_JIRA_URL/TOKEN/JQL/WORKSPACE`), новые задачи с меткой → очередь +
  аудит. Доставка «Jira → agctl» работает; **инжект промпта в dsh-сессию —
  следующий шаг** (проба endpoints на живом контейнере; запасной план —
  `Runtime.Exec` + `dsh headless`).

**Живые пробы по VPN:** GitLab whoami ок; Jira читается; цикл INTAIDEV-1
подтверждён артефактами прошлых прогонов (открытый MR !2 + комментарий агента).
На все демо-задачи 1/2/4/101 MR уже открыты → для чистого прогона берём
**INTAIDEV-3** (единственная без MR).

## 4. Часть 1 — твой ручной прогон на ЭТОЙ машине

Предусловия: Docker Desktop запущен, VPN включён. Терминал 1 — `make demo`
держит сервер; браузер и терминал 2 — твоя работа.

1. **Запуск платформы** (терминал 1):
   `cd cit/agctl && make demo`
   Первый раз собирает web+бинарь+образ (несколько минут), потом печатает
   `serve: addr=http://127.0.0.1:8929`.
2. **Регистрация:** открой `http://127.0.0.1:8929`, зарегистрируйся
   (первый пользователь = admin).
3. **Рабочее место:** «Создать рабочее место» → имя `1c-demo`, шаблон
   **1c-vibe**, Base URL `https://litellm-dev.utmn.ru/v1`, модели
   `qwen-3.8-deep` и `qwen-3.8-fast`, токен LiteLLM (sk-…). Жди статус
   `running` → кнопка «Открыть» → dsh web (ссылка с токеном).
4. **Контур внутри воркспейса** (терминал dsh web):
   `cd scripts && cp .env.example .env` → впиши `JIRA_URL/JIRA_TOKEN`
   (или `JIRA_USER/JIRA_PASSWORD`) и `GITLAB_URL/GITLAB_TOKEN` →
   `python3 -m pytest tests/ -q` (ожидаешь 14 passed).
5. **Задача агенту:** прочитай постановку — `python3 jira_client.py get INTAIDEV-3`
   (функция `ЦенаСНДС(Сумма, СтавкаНДС)` в модуле менеджера). В чате dsh web:
   «выполни INTAIDEV-3 по скиллу 1c-vibe-demo». Смотри: ветка → правка BSL →
   линт → публикация.
6. **Пруфы:** MR в GitLab (дифф+CI) и комментарий агента в INTAIDEV-3.
   Ревьюишь и мёржишь — ты контролёр.
7. **Живучесть:** в ЛК Stop → Start у воркспейса → файлы и сессии на месте.
8. *(опционально)* **Триггер:** в Jira повесь метку `agent-run` на задачу и
   запусти serve с env:
   `AGCTL_JIRA_URL=https://jira.utmn.ru AGCTL_JIRA_TOKEN=<PAT сервис-аккаунта>`
   `AGCTL_JIRA_WORKSPACE=<id воркспейса w-…> make demo`
   → в логе появится `jira-poll: … → очередь` (инжект агента пока ручной).

Критерий успеха Части 1: INTAIDEV-3 дошла до MR без ручных правок кода,
Stop/Start ничего не потерял.

## 5. Часть 2 — Windows-VM

- **Надёжный путь: WSL2.** `wsl --install -d Ubuntu` → в Ubuntu
  `sudo apt install git make` + Go (go.dev/dl) + Docker Desktop с WSL-интеграцией
  → `git clone …/agctl && make demo`. Дальше всё то же самое; браузер — внутри VM.
  VPN на VM включить: из неё должны быть видны jira/gitlab/litellm utmn.ru.
- **Нативная Windows — эксперимент:** winget git+Go+Docker Desktop →
  `go build -o agctl.exe .\cmd\agctl` → `.\agctl.exe serve`. Риски: сборка образа
  через named pipe никем не обкатана (CI гоняет только `go test`). Затыки
  записывай в карточку `clean-machine-run`.

## 6. Ответы на твои вопросы (коротко)

- **Зачем Docker** — изоляция/воспроизводимость/лимиты; переживает ли контейнер
  смерть — да, данные вне его (маунты). **Зачем bare+клон** — git-память и
  страховка autosave. **Что такое DSH_HOME** — дом харнеса (настройки/сессии),
  не «где живёт dsh-бинарь» — тот внутри образа. **Сессии** — JSONL-журналы
  (zstd), формат версионный. **Секреты** — см. п.2.5. Всё развёрнуто в чате
  2026-10-07 и docs/agctl-only.md.
- **B1–B3** — legacy, карта пофайлово в docs/agctl-only.md.
- **Плагины kb/dsh в agctl-контейнере не видны** — каталог не смонтирован;
  в воркспейсе свои скиллы из шаблона.

## 7. Недоделки (честно)

- Инжект промпта в dsh — скелет поллера без него (проба endpoints на живом
  контейнере).
- Открытый токен в `dsh-home/.credentials.yaml` (0600) — убрать до прода.
- Легаси-код B1–B3 в репо — удалить отдельным аудитом.
- Пуши не делались ни в один репо — 9 коммитов в 1c-vibe и 6 в agctl ждут тебя.
