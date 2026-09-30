# -*- coding: utf-8 -*-
"""Оффлайн-тест петли: мок-провайдер со сценарием ходов, без сети."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mvp"))

from loop import run  # noqa: E402
from tools import Toolbox  # noqa: E402


class FakeProvider:
    """Провайдер со сценарием: выдаёт заготовленные ходы по очереди."""

    def __init__(self, script: list[dict]):
        self.script = list(script)
        self.name = "fake"

    def chat(self, messages, tools=None, max_tokens=8192):
        if not self.script:
            return {"role": "assistant", "content": "сценарий исчерпан"}
        step = self.script.pop(0)
        if "content" in step and "tool_calls" not in step:
            return {"role": "assistant", "content": step["content"]}
        return {
            "role": "assistant",
            "content": step.get("content", ""),
            "tool_calls": [{
                "id": f"call_{len(self.script)}",
                "type": "function",
                "function": {"name": step["tool"], "arguments": json.dumps(step["args"])},
            }],
        }


class FakePool:
    def __init__(self, provider: FakeProvider):
        self.providers = [provider]


class LoopOfflineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.toolbox = Toolbox(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_full_cycle_with_tools(self) -> None:
        provider = FakeProvider([
            {"tool": "write_file", "args": {"path": "task-note.md", "content": "INTAIDEV-101: сделано"}},
            {"tool": "run_cmd", "args": {"command": "echo done"}},
            {"content": "Цикл выполнен: файл записан, команда отработала, MR открыт (демо)."},
        ])
        report = run(FakePool(provider), self.toolbox, "демо-цель")
        self.assertIn("Цикл выполнен", report)
        self.assertTrue((Path(self.tmp.name) / "task-note.md").exists())
        self.assertIn("INTAIDEV-101", (Path(self.tmp.name) / "task-note.md").read_text(encoding="utf-8"))

    def test_limit_stops_runaway(self) -> None:
        # бесконечный инструментальный ход → лимит ходов должен остановить
        endless = FakeProvider([{"tool": "list_dir", "args": {"path": "."}}] * 1000)
        report = run(FakePool(endless), self.toolbox, "демо-цель")
        self.assertIn("ЛИМИТ ХОДОВ", report)

    def test_forbidden_command_reported_to_model(self) -> None:
        provider = FakeProvider([
            {"tool": "run_cmd", "args": {"command": "shutdown /s"}},
            {"content": "стоп"},
        ])
        run(FakePool(provider), self.toolbox, "демо-цель")
        audit = (Path(self.tmp.name) / "audit.log").read_text(encoding="utf-8")
        self.assertIn("ЗАПРЕЩЕНО", audit)


class GuardTest(unittest.TestCase):
    def test_guard_disabled_by_default(self) -> None:
        import os
        saved = os.environ.pop("LLM_GUARD", None)
        try:
            from guard import check_goal
            safe, verdict = check_goal("любая цель")
            self.assertTrue(safe)
        finally:
            if saved is not None:
                os.environ["LLM_GUARD"] = saved


if __name__ == "__main__":
    unittest.main()


class GitExcludeTest(unittest.TestCase):
    def test_exclude_seeded_in_git_repo(self) -> None:
        import subprocess
        repo = Path(tempfile.mkdtemp())
        try:
            subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
            toolbox = Toolbox(repo)
            exclude = repo / ".git" / "info" / "exclude"
            text = exclude.read_text(encoding="utf-8")
            self.assertIn("audit.log", text)
            self.assertIn(".bsl-ls/", text)
        finally:
            import shutil
            shutil.rmtree(repo, ignore_errors=True)
