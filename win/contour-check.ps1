# contour-check.ps1 — проверка конфигурации (/CheckConfig-аналог через ibcmd)
# с сохранением лога. Fail-closed: пустой/ошибочный лог = ненулевой код выхода.
# Запуск после contour-import.ps1.

$ErrorActionPreference = "Stop"

# ── CONFIG ───────────────────────────────────────────────────────────────────
$Ibcmd  = "C:\Program Files\1cv8\8.3.23.xxx\bin\ibcmd.exe"
$DbPath = "C:\1c-vibe\ib"
$LogDir = "C:\1c-vibe\proofs"
# ─────────────────────────────────────────────────────────────────────────────

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$stamp  = Get-Date -Format "yyyyMMdd-HHmmss"
$checkLog = Join-Path $LogDir "check-$stamp.log"

Write-Host "==> проверка конфигурации, лог: $checkLog"
& $Ibcmd infobase config check `
    --db-path="$DbPath" `
    --check-logical=true *>&1 | Tee-Object -FilePath $checkLog

# fail-closed: отчёт обязан существовать и не быть пустым
if (-not (Test-Path $checkLog) -or (Get-Item $checkLog).Length -eq 0) {
    throw "лог проверки пуст — конвейер остановлен (это ошибка, а не 'всё чисто')"
}
if ($LASTEXITCODE -ne 0) { throw "config check: код $LASTEXITCODE — есть проблемы, смотри лог" }

Write-Host "==> OK: проверка завершена, пруф: $checkLog"
exit 0
