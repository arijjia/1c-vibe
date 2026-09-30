# bootstrap.ps1 — подготовка Windows-машины контура 1c-vibe (ЦИТ ТюмГУ).
# Запускать в PowerShell от пользователя:
#   Set-ExecutionPolicy -Scope Process Bypass -Force; .\bootstrap.ps1
# Два режима получения кода:
#   .\bootstrap.ps1                 — клон с GitHub (если репо доступна)
#   .\bootstrap.ps1 -Bundle b64.txt — из base64-бандла (receive_bundle.py)
# Что делает: проверяет git/python, получает код, создаёт .env, проверяет LLM.

param([string]$Bundle = "")
$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/arijjia/1c-vibe.git"
$Root    = "$HOME\1c-vibe"

function Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

Step "1/5 Проверка winget и пакетов (git, Python 3.12)"
$need = @()
foreach ($pkg in @("Git.Git", "Python.Python.3.12")) {
    winget list --id $pkg -e *> $null
    if ($LASTEXITCODE -ne 0) { $need += $pkg }
}
if ($need.Count -gt 0) {
    Step "устанавливаю: $($need -join ', ')"
    foreach ($pkg in $need) { winget install -e --id $pkg --accept-source-agreements --accept-package-agreements }
    # обновить PATH в текущей сессии
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
} else { Write-Host "git и python уже установлены" }

Step "2/5 Получение кода"
if ($Bundle -ne "") {
    if (-not (Test-Path $Bundle)) { throw "бандл не найден: $Bundle" }
    $b64 = (Get-Content $Bundle -Raw).Trim()
    $zipPath = "$env:TEMP\1cvibe.zip"
    [IO.File]::WriteAllBytes($zipPath, [Convert]::FromBase64String($b64))
    New-Item -ItemType Directory -Force -Path $Root | Out-Null
    Expand-Archive -Path $zipPath -DestinationPath $Root -Force
    Write-Host "распаковано в $Root"
} elseif (Test-Path $Root) {
    Write-Host "каталог уже есть: $Root"
} else {
    git clone $RepoUrl $Root
}

Step "3/5 Файл настроек mvp/.env"
$envFile = "$Root\mvp\.env"
if (Test-Path $envFile) { Write-Host ".env уже существует — не трогаю" }
else {
    Copy-Item "$Root\mvp\.env.example" $envFile
    Write-Host "Создан $envFile — заполни JIRA_*, GITLAB_*, LLM_API_KEY и открой заново." -ForegroundColor Yellow
}

Step "4/5 Проверка LLM (LLM_BASE_URL из .env)"
$envLines = Get-Content $envFile | Where-Object { $_ -match "^[A-Z_]+=" }
foreach ($line in $envLines) { $k, $v = $line -split "=", 2; Set-Item -Path "env:$k" -Value $v }
if ($env:LLM_BASE_URL -and $env:LLM_API_KEY) {
    python "$Root\agent\llmcheck.py"
} else {
    Write-Host "LLM_BASE_URL/LLM_API_KEY не заполнены — пропуск проверки." -ForegroundColor Yellow
}

Step "5/5 Готово. Дальше:"
Write-Host @"
  cd $Root
  python agent\loop.py --task INTAIDEV-101 --workspace mvp\dump
(перед этим заполни mvp\.env: JIRA_URL/TOKEN, GITLAB_URL/TOKEN, LLM_API_KEY)
"@
