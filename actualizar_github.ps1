# actualizar_github.ps1
# Automatiza: git add . / git commit -m "..." / git push
#
# Uso:
#   .\actualizar_github.ps1
#   .\actualizar_github.ps1 -Mensaje "Descripcion del cambio"
#
# Si Windows bloquea la ejecucion de scripts .ps1, corre esto una sola vez
# en una terminal de PowerShell (como tu usuario, no admin):
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

param(
    [string]$Mensaje
)

Write-Host "=== Actualizar repositorio en GitHub ===" -ForegroundColor Cyan

git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: esta carpeta no es un repositorio de Git." -ForegroundColor Red
    exit 1
}

Write-Host "`nEstado actual:" -ForegroundColor Yellow
git status --short

$cambios = git status --porcelain
if ([string]::IsNullOrWhiteSpace($cambios)) {
    Write-Host "`nNo hay cambios pendientes. Todo esta al dia con GitHub." -ForegroundColor Green
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Mensaje)) {
    $Mensaje = Read-Host "`nMensaje del commit"
    if ([string]::IsNullOrWhiteSpace($Mensaje)) {
        Write-Host "ERROR: el mensaje de commit no puede estar vacio." -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n[1/3] git add ." -ForegroundColor Yellow
git add .

Write-Host "`n[2/3] git commit -m `"$Mensaje`"" -ForegroundColor Yellow
git commit -m "$Mensaje"
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: el commit fallo. Revisa el mensaje de arriba." -ForegroundColor Red
    exit 1
}

Write-Host "`n[3/3] git push" -ForegroundColor Yellow
git push
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: el push fallo." -ForegroundColor Red
    Write-Host "Si es porque el remoto tiene cambios que no tienes localmente, intenta:" -ForegroundColor DarkYellow
    Write-Host "  git pull --rebase" -ForegroundColor DarkYellow
    Write-Host "  git push" -ForegroundColor DarkYellow
    exit 1
}

Write-Host "`nListo. Cambios publicados en GitHub." -ForegroundColor Green
