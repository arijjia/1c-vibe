#!/usr/bin/env python3
"""Публикация правок агента: ветка → commit → push → Merge Request → комментарий в Jira.

Использование:
  python publish.py ISSUE-KEY "резюме одним предложением" --repo /путь/к/клону [опции]

Опции:
  --repo PATH     путь к локальному клону демо-репозитория (по умолчанию ../1c-vibe-demo)
  --base BRANCH   базовая ветка (по умолчанию — ветка по умолчанию из GitLab)

Что делает:
  1. git fetch + ветка agent/ISSUE-KEY от базовой ветки;
  2. git add -A и коммит с сообщением "feat(ISSUE-KEY): резюме";
  3. push по HTTPS с токеном (токен не сохраняется в конфиге git);
  4. Merge Request через GitLab API;
  5. комментарий в Jira: резюме + ссылка на MR.

Все шаги печатаются — это же лог прогона для человека.
"""

import argparse
import os
import re
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from envconfig import load_env
from gitlab_client import api as gitlab_api, encoded_path
from jira_client import api as jira_api

load_env()


def git(repo: str, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True
    )
    if result.returncode != 0:
        sys.exit(f"git {' '.join(args)} завершился с ошибкой:\n{result.stderr.strip()}")
    return result.stdout.strip()


def remote_https(repo: str) -> tuple[str, str]:
    """Возвращает (хост, path) origin, приводя ssh-адрес к https-виду."""
    origin = git(repo, "remote", "get-url", "origin")
    if origin.startswith("git@"):
        host, path = origin[4:].split(":", 1)
    else:
        m = re.match(r"https?://([^/]+)/(.+)", origin)
        if not m:
            sys.exit(f"Не поняла формат origin: {origin}")
        host, path = m.group(1), m.group(2)
    return host, path.removesuffix(".git")


def push_url(host: str, path: str, token: str) -> str:
    return f"https://oauth2:{urllib.parse.quote(token)}@{host}/{path}.git"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("issue", help="ключ задачи, например INTAIDEV-101")
    parser.add_argument("summary", help="резюме правки одним предложением")
    parser.add_argument("--repo", default=os.path.join(os.getcwd(), "..", "1c-vibe-demo"))
    parser.add_argument("--base", default=None, help="базовая ветка (по умолчанию из GitLab)")
    args = parser.parse_args()

    gitlab_url = os.environ.get("GITLAB_URL", "").rstrip("/")
    gitlab_token = os.environ.get("GITLAB_TOKEN", "")
    jira_url = os.environ.get("JIRA_URL", "").rstrip("/")
    if not (gitlab_url and gitlab_token and jira_url):
        sys.exit("GITLAB_URL/GITLAB_TOKEN/JIRA_URL не заданы: заполни mvp/.env")

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        sys.exit(f"{repo} — не git-репозиторий; укажи путь к клону через --repo")

    host, project_path = remote_https(repo)
    branch = f"agent/{args.issue}"

    # 1. свежая база и ветка
    git(repo, "fetch", "origin")
    project = gitlab_api("GET", f"/projects/{encoded_path(project_path)}")
    base = args.base or project.get("default_branch", "main")
    print(f"[1/5] базовая ветка: {base}, рабочая ветка: {branch}")
    git(repo, "checkout", "-B", branch, f"origin/{base}")

    # 2. коммит
    git(repo, "add", "-A")
    if git(repo, "status", "--porcelain"):
        git(repo, "commit", "-m", f"feat({args.issue}): {args.summary}")
        print("[2/5] коммит создан")
    else:
        print("[2/5] изменений нет — проверь, что агент реально правил файлы")
        sys.exit(1)

    # 3. push (токен только в URL этого push, не в конфиге)
    git(repo, "push", push_url(host, project_path, gitlab_token), f"{branch}:{branch}")
    print(f"[3/5] ветка запушена: {branch}")

    # 4. Merge Request
    mr = gitlab_api(
        "POST",
        f"/projects/{project['id']}/merge_requests",
        {
            "source_branch": branch,
            "target_branch": base,
            "title": f"{args.issue}: {args.summary}",
            "description": (
                f"{args.summary}\n\nЗадача: {jira_url}/browse/{args.issue}\n\n"
                "Изменения подготовлены ИИ-агентом 1c-vibe и требуют ревью человека."
            ),
            "remove_source_branch": True,
        },
    )
    print(f"[4/5] MR создан: {mr['web_url']}")

    # 5. комментарий в Jira
    jira_api(
        "POST",
        f"/rest/api/2/issue/{args.issue}/comment",
        {
            "body": (
                f"Агент 1c-vibe подготовил решение.\n\n"
                f"Что сделано: {args.summary}\n"
                f"Merge Request: {mr['web_url']}\n\n"
                "После ревью и вливания MR задачу можно закрыть."
            )
        },
    )
    print(f"[5/5] комментарий добавлен в {args.issue}")
    print(f"\nГотово. MR: {mr['web_url']}")


if __name__ == "__main__":
    main()
