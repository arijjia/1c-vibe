# -*- coding: utf-8 -*-
"""Приёмник бандла 1c-vibe на Windows: b64 -> zip -> распаковка -> проверка.

На машине (PowerShell):
  $b64 = Get-Content b64.txt -Raw       # содержимое 1cvibe-bundle.b64.txt
  python receive_bundle.py b64.txt      # либо передать путь аргументом

Скрипт: декодирует base64, распаковывает в .\1c-vibe, печатает состав.
"""

from __future__ import annotations

import base64
import io
import sys
import zipfile
from pathlib import Path


def main() -> None:
    raw_path = Path(sys.argv[1] if len(sys.argv) > 1 else "b64.txt")
    data = base64.b64decode(raw_path.read_text(encoding="utf-8").strip())
    target = Path("1c-vibe").resolve()
    target.mkdir(exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        archive.extractall(target)
    count = sum(1 for _ in target.rglob("*") if _.is_file())
    print(f"OK: {target} — файлов: {count}")


if __name__ == "__main__":
    main()
