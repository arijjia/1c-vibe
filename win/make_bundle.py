# -*- coding: utf-8 -*-
"""make_bundle.py — сборка base64-бандла кода для передачи на Windows-машину.

На маке:   python3 win/make_bundle.py [выходной файл]
На машине: python receive_bundle.py <файл>   (распакует в .\\1c-vibe)

Состав: agent/*.py, mvp/*.py, mvp/.env.example, mvp/skills/**, win/*.
Исключены секреты (.env), кэши и тяжёлые файлы (uv.lock, demo-project —
демо-дерево едет через git clone/GitLab).
"""

from __future__ import annotations

import base64
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def collect() -> list[Path]:
    picks: list[Path] = []
    picks += sorted((ROOT / "agent").glob("*.py"))
    picks += sorted((ROOT / "mvp").glob("*.py"))
    example = ROOT / "mvp" / ".env.example"
    if example.exists():
        picks.append(example)
    picks += sorted(p for p in (ROOT / "mvp" / "skills").rglob("*") if p.is_file())
    picks += sorted((ROOT / "win").glob("*"))
    out: list[Path] = []
    for path in picks:
        if path.is_file() and "__pycache__" not in str(path) and path.name != ".env":
            out.append(path)
    return out


def main() -> int:
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/1cvibe-mini.b64.txt")
    buffer = io.BytesIO()
    files = collect()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT))
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(encoded, encoding="ascii")
    print(f"бандл: {len(files)} файлов, zip {len(buffer.getvalue())} байт, "
          f"b64 {len(encoded)} символов -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
