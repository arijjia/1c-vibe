#!/usr/bin/env bash
# Чистая комната DSH: инстанс харнеса «как у коллеги с чистым компом».
#
# Что делает:
#   - создаёт СВЕЖИЙ DSH_HOME (по умолчанию ~/.dsh-cleanroom), не трогая ~/.dsh;
#   - прописывает туда только необходимое: провайдер utmn, ключ, скилл 1c-vibe-demo;
#   - запускает `dsh web` на отдельном порту (по умолчанию 3098).
#
# Использование:
#   scripts/cleanroom-dsh.sh            # создать (если нет) и запустить на :3098
#   scripts/cleanroom-dsh.sh 3100       # другой порт
#   scripts/cleanroom-dsh.sh --reset    # снести чистую комнату и пересоздать
#
# Боевой инстанс (:3080, ~/.dsh) не затрагивается никогда.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
CLEANROOM="${DSH_CLEANROOM:-$HOME/.dsh-cleanroom}"
case "$CLEANROOM" in /*) ;; *) CLEANROOM="$PWD/$CLEANROOM" ;; esac
PORT="3098"

for arg in "$@"; do
  case "$arg" in
    --reset) RESET=1 ;;
    [0-9]*) PORT="$arg" ;;
    *) echo "неизвестный аргумент: $arg" >&2; exit 2 ;;
  esac
done

if [[ -n "${RESET:-}" ]]; then
  if [[ "$CLEANROOM" == "$REPO/dsh-home" ]]; then
    echo "отказ: --reset не удаляет репозиторный dsh-home (там есть tracked cordis.patch.yml)" >&2
    exit 2
  fi
  echo ">> сношу $CLEANROOM"
  rm -rf "$CLEANROOM"
fi

# dsh после импорта может переименовать settings.yaml в settings.yaml.imported.
if [[ -f "$CLEANROOM/settings.yaml" || -f "$CLEANROOM/settings.yaml.imported" ]]; then
  echo ">> чистая комната уже настроена: $CLEANROOM"
else
  echo ">> создаю чистую комнату: $CLEANROOM"
  mkdir -p "$CLEANROOM/skills" "$CLEANROOM/profiles"

  # settings.yaml — минимум, как получилось бы у нового пользователя
  cat > "$CLEANROOM/settings.yaml" <<'YAML'
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
agent-default-model:
  provider: utmn
  model: qwen-3.8-deep
YAML

  # ключ: из окружения или спросить (в файл не логируется)
  if [[ -z "${LITELLM_API_KEY:-}" ]]; then
    read -r -s -p "Ключ LiteLLM (sk-...): " LITELLM_API_KEY; echo
  fi
  cat > "$CLEANROOM/.credentials.yaml" <<YAML
version: 1
refs:
  LITELLM_API_KEY: "${LITELLM_API_KEY}"
YAML
  chmod 600 "$CLEANROOM/.credentials.yaml"

  # скилл из репы — единственная «инструкция», которую видит агент
  cp -R "$REPO/mvp/skills/1c-vibe-demo" "$CLEANROOM/skills/"
  echo ">> скилл 1c-vibe-demo установлен"

  # реестр воркспейсов: сессии открываются в корне этой репы, а не в
  # дефолтной папке dsh (иначе агент не видит AGENTS.md и скилл репы;
  # формат — workspace domain v2)
  NOW="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
  mkdir -p "$CLEANROOM/storages"
  cat > "$CLEANROOM/storages/workspace.json" <<JSON
{
  "unit": {"name": "workspace", "version": 2},
  "global": {
    "initialized": true,
    "defaultWorkspaceId": "ws-1c-vibe",
    "workspaceIds": ["ws-1c-vibe"],
    "archivedSessionIds": [],
    "pinnedSessionIds": []
  },
  "tables": {"workspaces": {"ws-1c-vibe": {
    "path": "$REPO",
    "title": "1c-vibe",
    "sessionIds": [],
    "createdAt": "$NOW",
    "updatedAt": "$NOW"}}}
}
JSON
  echo ">> рабочая папка сессий: $REPO"
fi

echo ">> запускаю dsh web: http://127.0.0.1:${PORT}  (DSH_HOME=$CLEANROOM)"
echo "   рабочая папка для сессии: $REPO"
cd "$REPO"

# Лаунчер `dsh` не пробрасывает node --expose-internals, который нужен
# HMR-сервису web-профиля — запускаем entrypoint напрямую (приём из
# kb/dsh: bin/dsh-web-live).
dsh_bin="$(command -v dsh)"
entry_js="$(dirname "$(dirname "$(readlink -f "$dsh_bin")")")/lib/bin.js"
DSH_HOME="$CLEANROOM" exec node --expose-internals "$entry_js" web \
  --host 127.0.0.1 --port "$PORT" --no-open
