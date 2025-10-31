# Bootstrap script: creates required folders and ensures base files exist
param(
    [switch]$Force
)

Write-Host "=== TELEGRAM BOT BOOTSTRAP ===" -ForegroundColor Cyan

# Create required directories
$dirs = @("data","logs","certs","alembic\versions")
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        Write-Host "Created dir: $d" -ForegroundColor Green
    } elseif ($Force) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        Write-Host "Ensured dir: $d" -ForegroundColor Yellow
    }
}

# Ensure alembic.ini exists
if (-not (Test-Path "alembic.ini")) {
    @"
[alembic]
script_location = alembic
prepend_sys_path = .
timezone = UTC

sqlalchemy.url = sqlite+aiosqlite:///./data/bot.db
"@ | Out-File -FilePath "alembic.ini" -Encoding UTF8 -Force
    Write-Host "Created alembic.ini (minimal)" -ForegroundColor Green
}

# Ensure .env template exists
if (-not (Test-Path ".env") -and (Test-Path "config\config.example.env")) {
    Copy-Item "config\config.example.env" ".env"
    Write-Host "Copied config.example.env to .env" -ForegroundColor Yellow
}

Write-Host "Bootstrap finished." -ForegroundColor Cyan
