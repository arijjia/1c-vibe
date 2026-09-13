#!/usr/bin/env python3
"""Мини-клиент Jira для MVP 1c-vibe.

Умеет:
  get    ISSUE-KEY          — показать постановку задачи;
  comment ISSUE-KEY "текст" — добавить комментарий.

Аутентификация — любой из вариантов (проверяются в этом порядке):
  1. JIRA_TOKEN                 — Personal Access Token (Jira Server/DC), Bearer;
  2. JIRA_USER + JIRA_PASSWORD  — Basic-авторизация (логин/пароль корпоративной
                                   учётки; для Jira Cloud вместо пароля — API-токен).

Настройки (в mvp/.env, см. .env.example):
  JIRA_URL — например https://jira.example.local
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from envconfig import load_env

load_env()

API = "/rest/api/2"


def _base() -> str:
    url = os.environ.get("JIRA_URL")
    if not url:
        sys.exit("JIRA_URL не задан: заполни mvp/.env (см. .env.example)")
    return url.rstrip("/")


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("JIRA_TOKEN")
    user = os.environ.get("JIRA_USER")
    password = os.environ.get("JIRA_PASSWORD")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif user and password:
        cred = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {cred}"
    else:
        sys.exit("Не задана авторизация: в mvp/.env укажи JIRA_TOKEN "
                 "или пару JIRA_USER + JIRA_PASSWORD (см. .env.example)")
    return headers


def api(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(_base() + path, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        if e.code in (401, 403):
            sys.exit(f"Jira ответила {e.code} (не прошла авторизация): {detail}\n"
                     "Подсказка: для Server/DC имя пользователя может отличаться "
                     "от email — попробуй короткий логин в JIRA_USER.")
        sys.exit(f"Jira ответила {e.code}: {detail}")
    except urllib.error.URLError as e:
        sys.exit(f"Не удалось соединиться с {_base()}: {e.reason} (проверь VPN)")


def get_issue(key: str) -> None:
    issue = api("GET", f"{API}/issue/{key}")
    fields = issue.get("fields", {})
    print(f"{issue.get('key')}: {fields.get('summary', '')}")
    print("-" * 60)
    print(fields.get("description") or "(описания нет)")


def whoami() -> None:
    me = api("GET", f"{API}/myself")
    print(f"{me.get('name')} ({me.get('displayName')}) — авторизация работает")


def add_comment(key: str, text: str) -> None:
    api("POST", f"{API}/issue/{key}/comment", {"body": text})
    print(f"Комментарий добавлен к {key}.")


def create_issue(project: str, summary: str, description: str, issuetype: str = "Task") -> str:
    issue = api(
        "POST",
        f"{API}/issue",
        {
            "fields": {
                "project": {"key": project},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issuetype},
            }
        },
    )
    return issue["key"]


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        sys.exit(2)
    if argv[0] == "whoami":
        whoami()
    elif argv[0] == "get" and len(argv) >= 2:
        get_issue(argv[1])
    elif argv[0] == "comment" and len(argv) >= 3:
        add_comment(argv[1], argv[2])
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
