# Revision_PC

Herramientas en Python/PowerShell para revisar los logs de Windows (Visor de Eventos) y detectar qué está fallando en el equipo: errores críticos, drivers, servicios, hardware, apagados inesperados, etc.

No requiere librerías externas — usa `wevtutil`, que ya viene incluido en Windows.

## Archivos

- **`revision_pc.py`** — script principal, analiza los logs.
- **`ejecutar_revision.ps1`** — asistente interactivo que pregunta los parámetros y ejecuta el script por ti.
- **`ejecutar_revision.bat`** — doble clic para correr el asistente sin preocuparte por políticas de ejecución de PowerShell.
- **`actualizar_github.ps1`** — automatiza `git add` / `commit` / `push`.
- **`actualizar_github.bat`** — doble clic para correr la publicación a GitHub sin preocuparte por políticas de ejecución.

## Si descargaste este repo como ZIP (no con `git clone`)

Windows marca los archivos extraídos de un ZIP descargado por navegador como "de Internet" (Mark of the Web), lo que bloquea los `.ps1` con el error *"cannot be loaded... is not digitally signed"*, sin importar tu política de ejecución. Dos formas de evitarlo:

- Usa los archivos **`.bat`** en vez de los `.ps1` directamente (les hacen doble clic normal, no requieren desbloquear nada).
- O desbloquea el ZIP antes de extraerlo: clic derecho → Propiedades → casilla "Unblock" → Aceptar.
- O, si ya lo extrajiste, corre `Unblock-File .\ejecutar_revision.ps1` (y lo mismo para `actualizar_github.ps1`).

Si en cambio clonas con `git clone`, este problema no ocurre — Git no marca los archivos.

## Uso rápido (recomendado)

```powershell
.\ejecutar_revision.ps1
```

Te va preguntando días a revisar, qué logs, si incluir advertencias, si mostrar apagados inesperados, cuántos eventos recientes mostrar, y si quieres guardar un CSV. Arma el comando y lo corre.

Si Windows bloquea el script la primera vez, corre una sola vez (no requiere admin):
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Uso directo por línea de comandos

```bash
# Últimos 7 días (default), logs System + Application
python revision_pc.py

# Últimos 30 días, mostrando los 15 eventos más recientes con detalle
python revision_pc.py --dias 30 --top 15

# Incluir advertencias, no solo errores/críticos
python revision_pc.py --dias 14 --incluir-advertencias

# Omitir la sección de apagados inesperados
python revision_pc.py --sin-apagados

# Revisar también el log de Setup
python revision_pc.py --logs System,Application,Setup

# Exportar el reporte completo a CSV
python revision_pc.py --dias 30 --salida reporte.csv
```

### Parámetros de `revision_pc.py`

| Flag | Default | Descripción |
|---|---|---|
| `--dias` | 7 | Días hacia atrás a revisar |
| `--logs` | System,Application | Logs a consultar, separados por coma. Escribe `todos` para revisar TODOS los logs del sistema (cientos de ellos, más lento). Otras opciones comunes: `System` (drivers/hardware), `Application` (programas), `Setup` (instalación/actualizaciones), `Security` (requiere PowerShell como Administrador). |
| `--incluir-advertencias` | desactivado | Incluye nivel Advertencia, no solo Crítico/Error |
| `--sin-apagados` | desactivado | Omite la detección de apagados inesperados |
| `--top` | 10 | Cuántos eventos recientes mostrar con detalle completo |
| `--salida` | (ninguno) | Ruta **completa** del archivo CSV a generar, incluyendo el nombre (ej: `D:\Revision_PC\reporte.csv`). No es solo una carpeta. |

## Qué hace

1. Consulta los logs indicados filtrando por nivel (Crítico=1, Error=2, Advertencia=3).
2. Agrupa los eventos por origen (proveedor) e ID de evento, para mostrarte los problemas que más se repiten.
3. Muestra los últimos N eventos con **detalle completo**: log, nivel, origen, ID, tarea/categoría y la descripción ya explicada por Windows (la misma que ves en el Visor de Eventos), sin necesidad de conexión a internet.
4. Incluye un link de búsqueda listo para abrir por cada evento, para profundizar si el mensaje local no basta.
5. Detecta específicamente **apagados/reinicios inesperados**:
   - `Kernel-Power` ID 41 — reinicio sin apagado limpio (corte de energía, sobrecalentamiento, hardware).
   - `EventLog` ID 6008 — apagado anterior no controlado.
   - `WER-SystemErrorReporting` ID 1001 — BSOD, con el código de bug check y una pista de la causa habitual.
   - `User32` ID 1074 — apagados/reinicios planeados (solo como contexto).
6. Opcionalmente guarda todo en un CSV para analizarlo después (Excel, etc.).

## Siguientes pasos sugeridos

- Si ves un código BSOD repetido, revisa la tabla de causas en `revision_pc.py` (`BUGCHECK_HINTS`) o el link de búsqueda que te da cada evento.
- Si ves muchos eventos del proveedor `disk`, `ntfs` o `Ntfs`, revisar salud del disco (`chkdsk`, S.M.A.R.T.).
- Si se repiten apagados sin código BSOD asociado, revisa temperaturas (HWMonitor/HWiNFO) y la fuente de poder.
