# Revision_PC

Script en Python para revisar los logs de Windows (Visor de Eventos) y detectar qué está fallando en el equipo: errores críticos, drivers, servicios, hardware, etc.

No requiere librerías externas — usa `wevtutil`, que ya viene incluido en Windows.

## Uso

```bash
# Últimos 7 días (default), logs System + Application
python revision_pc.py

# Últimos 30 días
python revision_pc.py --dias 30

# Incluir advertencias, no solo errores/críticos
python revision_pc.py --dias 14 --incluir-advertencias

# Revisar también el log de Setup
python revision_pc.py --logs System,Application,Setup

# Exportar el reporte a CSV
python revision_pc.py --dias 30 --salida reporte.csv
```

## Qué hace

1. Consulta los logs indicados (`System` y `Application` por defecto) filtrando por nivel (Crítico=1, Error=2, Advertencia=3).
2. Agrupa los eventos por origen (proveedor) e ID de evento, para mostrarte los problemas que más se repiten.
3. Muestra los 10 eventos más recientes con su mensaje.
4. Opcionalmente guarda todo en un CSV para analizarlo después (Excel, etc.).

## Siguientes pasos sugeridos

- Buscar el `event_id` + `proveedor` que más se repita en Google/Microsoft Docs para identificar la causa raíz.
- Si ves muchos eventos del proveedor `disk`, `ntfs` o `Ntfs`, revisar salud del disco (`chkdsk`, S.M.A.R.T.).
- Si ves eventos de `Kernel-Power` con ID 41, normalmente indica apagados inesperados (posible problema de energía/hardware).
