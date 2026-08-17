# ejecutar_revision.ps1
# Asistente interactivo: pregunta las variables y ejecuta revision_pc.py con ellas.
#
# Uso:
#   .\ejecutar_revision.ps1
#
# Si Windows bloquea la ejecucion de scripts .ps1, corre esto una sola vez
# en una terminal de PowerShell (como tu usuario, no admin):
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

Write-Host "=== Revision de PC - Configuracion ===" -ForegroundColor Cyan
Write-Host "Deja en blanco y da Enter para usar el valor por default.`n" -ForegroundColor DarkGray

$diasInput = Read-Host "Cuantos dias hacia atras revisar? (default: 7)"
$dias = 7
if (-not [string]::IsNullOrWhiteSpace($diasInput)) {
    $valorValido = 0
    if ([int]::TryParse($diasInput, [ref]$valorValido)) {
        $dias = $valorValido
    } else {
        Write-Host "Valor invalido, usando 7." -ForegroundColor DarkYellow
    }
}

$logsInput = Read-Host "Logs a revisar, separados por coma (default: System,Application)"
$logs = "System,Application"
if (-not [string]::IsNullOrWhiteSpace($logsInput)) {
    $logs = $logsInput
}

$advertenciasInput = Read-Host "Incluir advertencias, no solo errores/criticos? (s/N)"
$incluirAdvertencias = $advertenciasInput -match '^[sSyY]'

$sinApagadosInput = Read-Host "Omitir la seccion de apagados inesperados? (s/N)"
$sinApagados = $sinApagadosInput -match '^[sSyY]'

$topInput = Read-Host "Cuantos eventos recientes mostrar con detalle? (default: 10)"
$top = 10
if (-not [string]::IsNullOrWhiteSpace($topInput)) {
    $valorValido = 0
    if ([int]::TryParse($topInput, [ref]$valorValido)) {
        $top = $valorValido
    } else {
        Write-Host "Valor invalido, usando 10." -ForegroundColor DarkYellow
    }
}

$salida = Read-Host "Ruta de CSV para guardar el reporte (Enter = no guardar)"

$argumentos = @("revision_pc.py", "--dias", $dias, "--logs", $logs, "--top", $top)
if ($incluirAdvertencias) { $argumentos += "--incluir-advertencias" }
if ($sinApagados) { $argumentos += "--sin-apagados" }
if (-not [string]::IsNullOrWhiteSpace($salida)) { $argumentos += @("--salida", $salida) }

Write-Host "`nEjecutando: python $($argumentos -join ' ')" -ForegroundColor Yellow
Write-Host ""

python @argumentos
