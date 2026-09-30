# contour-restore.ps1 — восстановление тестовой базы 1С из ночного .dt через ibcmd.
# ЗНАЧЕНИЯ В БЛОКЕ CONFIG заполняются по итогам первого прогона на машине
# (см. contour-plan.md, раздел «Что нужно замерить»).
# Принцип fail-closed: любая ошибка останавливает конвейер.

$ErrorActionPreference = "Stop"

# ── CONFIG (замерить на машине) ──────────────────────────────────────────────
$Ibcmd    = "C:\Program Files\1cv8\8.3.23.xxx\bin\ibcmd.exe"  # путь к ibcmd
$Backup   = "C:\backups\night.dt"                             # свежий ночной бэкап
$DbPath   = "C:\1c-vibe\ib"                                   # каталог тестовой ИБ
# ─────────────────────────────────────────────────────────────────────────────

if (-not (Test-Path $Ibcmd))  { throw "ibcmd не найден: $Ibcmd" }
if (-not (Test-Path $Backup)) { throw "бэкап не найден: $Backup" }

Write-Host "==> восстановление $Backup -> $DbPath"
New-Item -ItemType Directory -Force -Path $DbPath | Out-Null

& $Ibcmd infobase restore `
    --db-path="$DbPath" `
    --restore-file="$Backup" `
    --force
if ($LASTEXITCODE -ne 0) { throw "restore завершился с кодом $LASTEXITCODE — конвейер остановлен" }

Write-Host "==> OK: база восстановлена ($DbPath)"
exit 0
