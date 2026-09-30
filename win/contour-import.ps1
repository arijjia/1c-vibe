# contour-import.ps1 — загрузка XML-дерева конфигурации из git-ветки в тестовую ИБ.
# Запуск после contour-restore.ps1. $RepoDump — выгрузка конфигурации в репе
# (ветка agent/INTAIDEV-N, каталог с Configuration.xml).
# Fail-closed: импорт с ошибками = стоп конвейера.

$ErrorActionPreference = "Stop"

# ── CONFIG ───────────────────────────────────────────────────────────────────
$Ibcmd  = "C:\Program Files\1cv8\8.3.23.xxx\bin\ibcmd.exe"
$DbPath = "C:\1c-vibe\ib"
$RepoDump = "C:\1c-vibe\repo"   # клон репы; XML-выгрузка в корне или подкаталоге
# ─────────────────────────────────────────────────────────────────────────────

if (-not (Test-Path "$RepoDump\Configuration.xml")) {
    throw "Configuration.xml не найден в $RepoDump — не похоже на выгрузку 1С"
}

Write-Host "==> импорт конфигурации из $RepoDump"
& $Ibcmd infobase config import `
    --db-path="$DbPath" `
    --config-files="$RepoDump"
if ($LASTEXITCODE -ne 0) { throw "config import: код $LASTEXITCODE — конвейер остановлен" }

Write-Host "==> OK: конфигурация применена"
exit 0
