# -*- coding: utf-8 -*-
"""Тесты агентской петли 1c-vibe: изоляция workspace, запрет-лист, JSON-режим."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from tools import Toolbox, dispatch  # noqa: E402
from loop import _json_mode_message  # noqa: E402


class ToolboxSafetyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.toolbox = Toolbox(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_write_read_roundtrip(self) -> None:
        self.assertTrue(self.toolbox.write_file("a/b.txt", "привет").startswith("OK"))
        self.assertEqual(self.toolbox.read_file("a/b.txt"), "привет")

    def test_path_traversal_blocked(self) -> None:
        result = self.toolbox.read_file("../outside.txt")
        self.assertIn("запрещён", result)
        result = self.toolbox.write_file("../../etc/passwd", "x")
        self.assertIn("запрещён", result)

    def test_forbidden_command(self) -> None:
        result = self.toolbox.run_cmd("rm -rf /")
        self.assertIn("ЗАПРЕЩЕНО", result)
        result = self.toolbox.run_cmd("format c:")
        self.assertIn("ЗАПРЕЩЕНО", result)

    def test_allowed_command_runs(self) -> None:
        result = self.toolbox.run_cmd("echo ok")
        self.assertIn("exit=0", result)
        self.assertIn("ok", result)

    def test_unknown_cli(self) -> None:
        self.assertIn("неизвестный CLI", self.toolbox.run_cli("evil.py --boom"))

    def test_dispatch_unknown_tool(self) -> None:
        self.assertIn("НЕИЗВЕСТНЫЙ ИНСТРУМЕНТ",
                      dispatch(self.toolbox, "nuke", "{}"))


class JsonModeTest(unittest.TestCase):
    def test_tool_call_parsed(self) -> None:
        choice = {"content": '{"tool": "list_dir", "arguments": {"path": "."}}'}
        result = _json_mode_message(choice)
        self.assertEqual(result["tool_calls"][0]["function"]["name"], "list_dir")

    def test_final_parsed(self) -> None:
        choice = {"content": '{"final": "готово"}'}
        result = _json_mode_message(choice)
        self.assertEqual(result["content"], "готово")
        self.assertNotIn("tool_calls", result)

    def test_markdown_fence_stripped(self) -> None:
        choice = {"content": "```json\n{\"tool\": \"run_cmd\", \"arguments\": {\"command\": \"git status\"}}\n```"}
        result = _json_mode_message(choice)
        self.assertEqual(json.loads(result["tool_calls"][0]["function"]["arguments"])["command"],
                         "git status")

    def test_plain_text_passthrough(self) -> None:
        choice = {"content": "просто текст не по протоколу"}
        self.assertEqual(_json_mode_message(choice), choice)

    def test_empty_content(self) -> None:
        self.assertIsNone(_json_mode_message({"content": ""}))


if __name__ == "__main__":
    unittest.main()
