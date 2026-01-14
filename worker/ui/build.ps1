# ui/build.ps1
# Script para build do Tauri App

Write-Host "🔨 Building RPA Worker UI..." -ForegroundColor Cyan

# Verifica se Rust está instalado
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Rust não encontrado. Instale em: https://rustup.rs/" -ForegroundColor Red
    exit 1
}

# Verifica se Tauri CLI está instalado
if (-not (Get-Command cargo-tauri -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Instalando Tauri CLI..." -ForegroundColor Yellow
    cargo install tauri-cli
}

# Build
Write-Host "⚙️ Compilando aplicação..." -ForegroundColor Yellow
cd src-tauri
cargo tauri build

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Build concluído com sucesso!" -ForegroundColor Green
    Write-Host "📦 Binário gerado em: src-tauri\target\release\rpa-worker-ui.exe" -ForegroundColor Cyan
} else {
    Write-Host "`n❌ Erro no build" -ForegroundColor Red
    exit 1
}