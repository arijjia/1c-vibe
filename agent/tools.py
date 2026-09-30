# -*- coding: utf-8 -*-
"""Тулзы агентской петли 1c-vibe: то, что агент может делать на машине.

Философия (из роадмапа): агент не шире рабочего каталога и разрешённых
команд. Всё выполняется внутри workspace; опасные пути и команды отсечены.
Каждый вызов пишется в журнал прогона (audit.log рядом с workspace).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Команды, которые агенту нельзя запускать даже изнутри разрешённой.
FORBIDDEN_SUBSTRINGS = (
    "rm -rf /", "rd /s", "del /f /s /q c:\\", "format ", "shutdown",
    "cipher /w", "diskpart",
)

MAX_TOOL_OUTPUT = 20_000  # символов — чтобы не разрывать контекст модели


def _clip(text: str) -> str:
    if len(text) > MAX_TOOL_OUTPUT:
        return text[:MAX_TOOL_OUTPUT] + f"\n… (обрезано, всего {len(text)} символов)"
    return text


class Toolbox:
    """Набор инструментов агента; workspace — единственная рабочая область.

    mvp_root — абсолютный путь к каталогу mvp/ проекта: CLI-скрипты запускаются
    оттуда, но с cwd=workspace, чтобы относительные пути (--repo dump/...) были
    внутри рабочей области.
    """

    def __init__(self, workspace: Path, mvp_root: Path | None = None,
                 extra_cli: list[str] | None = None):
        self.workspace = workspace.resolve()
        self.mvp_root = (mvp_root or Path(__file__).resolve().parent.parent / "mvp").resolve()
        self.extra_cli = extra_cli or ["jira_client.py", "gitlab_client.py",
                                       "publish.py", "seed_demo.py", "lint.py"]
        self.audit_path = self.workspace / "audit.log"
        self._audit("session", f"старт тулбокса, workspace={self.workspace}, mvp={self.mvp_root}")

    # ── служебное ────────────────────────────────────────────────────────────

    def _audit(self, tool: str, detail: str) -> None:
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{tool}\t{detail}"
        try:
            with open(self.audit_path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass

    def _safe_path(self, raw: str) -> Path:
        """Путь только внутри workspace (защита от ../ и абсолютных путей наружу)."""
        candidate = (self.workspace / raw).resolve()
        if self.workspace not in candidate.parents and candidate != self.workspace:
            raise ValueError(f"путь вне workspace запрещён: {raw}")
        return candidate

    # ── инструменты ──────────────────────────────────────────────────────────

    def run_cmd(self, command: str, timeout_s: int = 600) -> str:
        """Запустить shell-команду в workspace; stdout+stderr, код возврата."""
        lowered = command.lower()
        for bad in FORBIDDEN_SUBSTRINGS:
            if bad in lowered:
                self._audit("run_cmd", "ЗАПРЕЩЕНО: " + command)
                return "ЗАПРЕЩЕНО: команда отклонена политикой безопасности"
        self._audit("run_cmd", command)
        try:
            completed = subprocess.run(
                command, shell=True, cwd=str(self.workspace), timeout=timeout_s,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            output = f"exit={completed.returncode}\n"
            if completed.stdout:
                output += "--stdout--\n" + completed.stdout
            if completed.stderr:
                output += "--stderr--\n" + completed.stderr
            return _clip(output)
        except subprocess.TimeoutExpired:
            return f"ТАЙМАУТ через {timeout_s}с: {command}"
        except OSError as error:
            return f"ОШИБКА ЗАПУСКА: {error}"

    def run_cli(self, args: str) -> str:
        """Запустить CLI-скрипты проекта (jira/gitlab/publish) из mvp/ проекта."""
        first = args.split()[0] if args.split() else ""
        if first in self.extra_cli:
            script = self.mvp_root / first
            return self.run_cmd(f'"{sys.executable}" "{script}" {args[len(first):].strip()}')
        return (f"неизвестный CLI: {args}. Разрешены: " + ", ".join(self.extra_cli))

    def read_file(self, path: str, max_bytes: int = 60_000) -> str:
        """Прочитать текстовый файл из workspace (XML/BSL/MD и т.п.)."""
        try:
            target = self._safe_path(path)
            data = target.read_bytes()[:max_bytes]
            self._audit("read_file", path)
            return _clip(data.decode("utf-8", errors="replace"))
        except (OSError, ValueError) as error:
            return f"ОШИБКА ЧТЕНИЯ {path}: {error}"

    def write_file(self, path: str, content: str) -> str:
        """Записать файл в workspace (создать/перезаписать)."""
        try:
            target = self._safe_path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            self._audit("write_file", f"{path} ({len(content)} символов)")
            return f"OK: записано {path} ({len(content)} символов)"
        except (OSError, ValueError) as error:
            return f"ОШИБКА ЗАПИСИ {path}: {error}"

    def list_dir(self, path: str = ".") -> str:
        """Список файлов/каталогов (имя, тип, размер)."""
        try:
            target = self._safe_path(path)
            if not target.is_dir():
                return f"не каталог: {path}"
            rows = []
            for entry in sorted(target.iterdir()):
                kind = "DIR " if entry.is_dir() else "FILE"
                size = entry.stat().st_size if entry.is_file() else ""
                rows.append(f"{kind}\t{size}\t{entry.name}")
            self._audit("list_dir", path)
            return _clip("\n".join(rows) or "(пусто)")
        except (OSError, ValueError) as error:
            return f"ОШИБКА СПИСКА {path}: {error}"


# Схемы для OpenAI tools API (vLLM/LiteLLM + qwen поддерживают).
TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "run_cmd",
        "description": "Выполнить shell-команду в рабочем каталоге (git, python, линтер и т.д.).",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"},
            "timeout_s": {"type": "integer", "default": 600},
        }, "required": ["command"]},
    }},
    {"type": "function", "function": {
        "name": "run_cli",
        "description": "Запустить CLI проекта: jira_client.py / gitlab_client.py / publish.py / seed_demo.py (аргументы без имени файла).",
        "parameters": {"type": "object", "properties": {
            "args": {"type": "string"},
        }, "required": ["args"]},
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Прочитать текстовый файл из рабочего каталога.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
        }, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Создать/перезаписать файл в рабочем каталоге.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        }, "required": ["path", "content"]},
    }},
    {"type": "function", "function": {
        "name": "list_dir",
        "description": "Список файлов каталога рабочего пространства.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "default": "."},
        }},
    }},
]


def dispatch(toolbox: Toolbox, name: str, arguments: str) -> str:
    """Выполнить вызов инструмента по имени из ответа модели."""
    try:
        kwargs = json.loads(arguments) if arguments.strip() else {}
    except json.JSONDecodeError as error:
        return f"ОШИБКА АРГУМЕНТОВ {name}: {error}"
    handlers = {
        "run_cmd": lambda: toolbox.run_cmd(kwargs.get("command", "")),
        "run_cli": lambda: toolbox.run_cli(kwargs.get("args", "")),
        "read_file": lambda: toolbox.read_file(kwargs.get("path", "")),
        "write_file": lambda: toolbox.write_file(kwargs.get("path", ""), kwargs.get("content", "")),
        "list_dir": lambda: toolbox.list_dir(kwargs.get("path", ".")),
    }
    handler = handlers.get(name)
    if handler is None:
        return f"НЕИЗВЕСТНЫЙ ИНСТРУМЕНТ: {name}"
    return handler()
