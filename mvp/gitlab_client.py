#!/usr/bin/env python3
"""Мини-клиент GitLab для MVP 1c-vibe.

Умеет:
  whoami                                     — проверить токен;
  project  group/subgroup/project            — найти проект (id, web_url);
  create-mr group/subgroup/project SOURCE TITLE [DESCRIPTION]
          — создать merge request из ветки SOURCE в основную ветку.

Аутентификация (в mvp/.env):
  GITLAB_URL   — например https://gitlab.example.local
  GITLAB_TOKEN — Personal Access Token (scope api) ИЛИ OAuth-токен.
  GITLAB_AUTH  — необязательно: header|bearer (по умолчанию определяется
                 автоматически: glpat-* → PRIVATE-TOKEN, остальное → Bearer).

Git-операции (push) с PAT: https://<user>:<token>@host/...
с OAuth-токеном:            https://oauth2:<token>@host/...
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from envconfig import load_env

load_env()

API = "/api/v4"


def _base() -> str:
    url = os.environ.get("GITLAB_URL")
    if not url:
        sys.exit("GITLAB_URL не задан: заполни mvp/.env (см. .env.example)")
    return url.rstrip("/")


def _token() -> str:
    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        sys.exit("GITLAB_TOKEN не задан: заполни mvp/.env (см. .env.example)")
    return token


def _headers() -> dict:
    token = _token()
    mode = os.environ.get("GITLAB_AUTH")
    if not mode:
        mode = "header" if token.startswith("glpat-") else "bearer"
    headers = {"Content-Type": "application/json"}
    if mode == "header":
        headers["PRIVATE-TOKEN"] = token
    else:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def api(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(_base() + API + path, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        if e.code in (401, 403):
            sys.exit(f"GitLab ответил {e.code} (не прошла авторизация): {detail}\n"
                     "Подсказка: проверь GITLAB_TOKEN и GITLAB_AUTH (header|bearer).")
        sys.exit(f"GitLab ответил {e.code}: {detail}")
    except urllib.error.URLError as e:
        sys.exit(f"Не удалось соединиться с {_base()}: {e.reason} (проверь VPN)")


def encoded_path(project: str) -> str:
    return urllib.parse.quote(project, safe="")


def whoami() -> None:
    user = api("GET", "/user")
    print(f"{user.get('username')} <{user.get('email', '?')}> — токен работает")


def get_project(project: str) -> None:
    info = api("GET", f"/projects/{encoded_path(project)}")
    print(f"id={info['id']}  {info['path_with_namespace']}  {info['web_url']}")
    print(f"ветка по умолчанию: {info.get('default_branch')}")


def create_mr(project: str, source: str, title: str, description: str) -> dict:
    info = api("GET", f"/projects/{encoded_path(project)}")
    target = info.get("default_branch", "main")
    mr = api(
        "POST",
        f"/projects/{info['id']}/merge_requests",
        {
            "source_branch": source,
            "target_branch": target,
            "title": title,
            "description": description,
            "remove_source_branch": True,
        },
    )
    return mr


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        sys.exit(2)
    if argv[0] == "whoami":
        whoami()
    elif argv[0] == "project" and len(argv) >= 2:
        get_project(argv[1])
    elif argv[0] == "create-mr" and len(argv) >= 4:
        project, source, title = argv[1], argv[2], argv[3]
        description = argv[4] if len(argv) >= 5 else ""
        mr = create_mr(project, source, title, description)
        print(f"MR !{mr['iid']}: {mr['web_url']}")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
