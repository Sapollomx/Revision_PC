#!/usr/bin/env python3
"""
revision_pc.py - Analiza los registros de eventos de Windows para identificar
errores y advertencias que puedan indicar fallas en el equipo, con deteccion
especifica de apagados/reinicios inesperados (cortes de energia, BSOD, etc)
y mensajes de detalle completos (los mismos que muestra el Visor de Eventos).

Requiere: Windows (usa wevtutil, incluido de forma nativa. No necesitas instalar nada).

Uso:
    python revision_pc.py
    python revision_pc.py --dias 30
    python revision_pc.py --dias 14 --incluir-advertencias --top 15
    python revision_pc.py --salida reporte.csv
"""

import argparse
import csv
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

NS = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}

NIVEL_TEXTO = {"1": "Critico", "2": "Error", "3": "Advertencia", "4": "Informacion"}

FIRMAS_APAGADO_INESPERADO = [
    ("Microsoft-Windows-Kernel-Power", "41",
     "Reinicio sin apagado limpio: posible corte de energia, sobrecalentamiento o falla de hardware"),
    ("EventLog", "6008",
     "El sistema reporta que el apagado anterior no fue controlado"),
]

FIRMA_BUGCHECK = ("Microsoft-Windows-WER-SystemErrorReporting", "1001",
                   "Pantalla azul (BSOD) registrada, con codigo de error (bug check)")

FIRMA_APAGADO_PLANEADO = ("User32", "1074",
                           "Apagado/reinicio iniciado de forma normal (contexto, no es una falla)")

BUGCHECK_HINTS = {
    "0x0000000a": "IRQL_NOT_LESS_OR_EQUAL - normalmente un driver defectuoso",
    "0x0000001e": "KMODE_EXCEPTION_NOT_HANDLED - error del kernel o de un driver",
    "0x00000024": "NTFS_FILE_SYSTEM - posible falla del disco",
    "0x0000003b": "SYSTEM_SERVICE_EXCEPTION - driver o software de seguridad",
    "0x00000050": "PAGE_FAULT_IN_NONPAGED_AREA - RAM defectuosa o driver",
    "0x0000007e": "SYSTEM_THREAD_EXCEPTION_NOT_HANDLED - driver",
    "0x0000009f": "DRIVER_POWER_STATE_FAILURE - driver con mal manejo de energia",
    "0x000000d1": "DRIVER_IRQL_NOT_LESS_OR_EQUAL - driver",
    "0x00000116": "VIDEO_TDR_ERROR - driver de tarjeta grafica",
    "0x00000124": "WHEA_UNCORRECTABLE_ERROR - hardware: CPU, RAM o fuente de poder",
    "0x0000012b": "FAULTY_HARDWARE_CORRUPTED_PAGE - hardware defectuoso (RAM/CPU)",
}


def obtener_todos_los_logs():
    """Enumera TODOS los logs de eventos disponibles en el sistema (wevtutil el)."""
    try:
        salida = subprocess.run(
            ["wevtutil", "el"], capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=30
        )
    except FileNotFoundError:
        print("ERROR: 'wevtutil' no se encontro. Este script solo funciona en Windows.")
        sys.exit(1)
    if salida.returncode != 0:
        return []
    return [linea.strip() for linea in salida.stdout.splitlines() if linea.strip()]


def construir_query(nivel_max, dias):
    fecha_limite = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    niveles = " or ".join(f"Level={n}" for n in range(1, nivel_max + 1))
    return f"*[System[({niveles}) and TimeCreated[@SystemTime>='{fecha_limite}']]]"


def construir_query_especifico(provider, event_id, dias):
    fecha_limite = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    return (
        f"*[System[(Provider[@Name='{provider}'] and EventID={event_id}) "
        f"and TimeCreated[@SystemTime>='{fecha_limite}']]]"
    )


def generar_url_busqueda(proveedor, event_id):
    """Link listo para abrir en el navegador y profundizar (no lo abre el script)."""
    consulta = quote(f"Windows Event ID {event_id} {proveedor}")
    return f"https://www.bing.com/search?q={consulta}"


def consultar_log(nombre_log, query, categoria="general", max_eventos=500):
    """
    Usa /f:renderedxml para que Windows incluya el mensaje ya traducido/explicado
    (el mismo texto que ves en Visor de Eventos > pestana General), en vez de
    solo los valores crudos de EventData. Todo esto es local, sin internet.
    """
    cmd = [
        "wevtutil", "qe", nombre_log,
        f"/q:{query}",
        "/f:renderedxml",
        f"/c:{max_eventos}",
        "/rd:true",
    ]
    try:
        salida = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="ignore", timeout=60
        )
    except FileNotFoundError:
        print("ERROR: 'wevtutil' no se encontro. Este script solo funciona en Windows.")
        sys.exit(1)

    if salida.returncode != 0 and not salida.stdout.strip():
        return []

    xml_texto = salida.stdout.strip()
    if not xml_texto:
        return []

    envoltura = f"<Root>{xml_texto}</Root>"
    try:
        raiz = ET.fromstring(envoltura)
    except ET.ParseError:
        return []

    eventos = []
    for evento in raiz.findall("e:Event", NS):
        sistema = evento.find("e:System", NS)
        if sistema is None:
            continue
        proveedor_el = sistema.find("e:Provider", NS)
        proveedor = proveedor_el.get("Name") if proveedor_el is not None else "Desconocido"
        event_id_el = sistema.find("e:EventID", NS)
        event_id = event_id_el.text if event_id_el is not None else "?"
        nivel_el = sistema.find("e:Level", NS)
        nivel = nivel_el.text if nivel_el is not None else "?"
        tiempo_el = sistema.find("e:TimeCreated", NS)
        tiempo = tiempo_el.get("SystemTime") if tiempo_el is not None else "?"

        # Mensaje explicado (rendering info), tarea y palabras clave si Windows los tiene localmente
        mensaje_completo = ""
        tarea = ""
        render_info = evento.find("e:RenderingInfo", NS)
        if render_info is not None:
            msg_el = render_info.find("e:Message", NS)
            if msg_el is not None and msg_el.text:
                mensaje_completo = msg_el.text.strip()
            tarea_el = render_info.find("e:Task", NS)
            if tarea_el is not None and tarea_el.text:
                tarea = tarea_el.text.strip()

        # Si el proveedor no tiene tabla de mensajes local (comun en apps de terceros),
        # caemos de regreso a los datos crudos.
        if not mensaje_completo:
            datos = []
            eventdata = evento.find("e:EventData", NS)
            if eventdata is not None:
                for d in eventdata.findall("e:Data", NS):
                    if d.text:
                        datos.append(d.text)
            mensaje_completo = " | ".join(datos)

        eventos.append({
            "log": nombre_log,
            "tiempo": tiempo,
            "nivel": nivel,
            "proveedor": proveedor,
            "event_id": event_id,
            "tarea": tarea,
            "mensaje": mensaje_completo,
            "categoria": categoria,
            "url_busqueda": generar_url_busqueda(proveedor, event_id),
        })
    return eventos


def imprimir_resumen(eventos, top=10):
    if not eventos:
        print("No se encontraron eventos de error/critico en el rango solicitado. Buena senal.")
        return

    print(f"\nTotal de eventos encontrados: {len(eventos)}\n")

    contador = Counter((e["proveedor"], e["event_id"]) for e in eventos)
    print("Top 10 problemas mas frecuentes (origen, ID de evento -> repeticiones):")
    for (proveedor, event_id), veces in contador.most_common(10):
        print(f"  - {proveedor} (ID {event_id}): {veces} veces")

    print(f"\nUltimos {top} eventos (mas recientes primero, con detalle completo):")
    print("-" * 70)
    for i, e in enumerate(eventos[:top], start=1):
        nivel_txt = NIVEL_TEXTO.get(e["nivel"], e["nivel"])
        print(f"\n[{i}] {e['tiempo']}  |  {nivel_txt}  |  Log: {e['log']}")
        print(f"    Origen: {e['proveedor']}   ID de evento: {e['event_id']}")
        if e["tarea"] and e["tarea"] not in ("", "None"):
            print(f"    Categoria/Tarea: {e['tarea']}")
        if e["mensaje"]:
            print(f"    Descripcion: {e['mensaje']}")
        else:
            print("    Descripcion: (Windows no tiene una plantilla de mensaje local para este proveedor)")
        print(f"    Mas info: {e['url_busqueda']}")


def detectar_apagados_inesperados(dias):
    inesperados = []
    for provider, event_id, _desc in FIRMAS_APAGADO_INESPERADO:
        query = construir_query_especifico(provider, event_id, dias)
        inesperados.extend(consultar_log("System", query, categoria="apagado_inesperado"))

    query_bc = construir_query_especifico(FIRMA_BUGCHECK[0], FIRMA_BUGCHECK[1], dias)
    bugcheck = consultar_log("System", query_bc, categoria="bugcheck_bsod")

    query_pl = construir_query_especifico(FIRMA_APAGADO_PLANEADO[0], FIRMA_APAGADO_PLANEADO[1], dias)
    planeados = consultar_log("System", query_pl, categoria="apagado_planeado")

    inesperados.sort(key=lambda e: e["tiempo"], reverse=True)
    bugcheck.sort(key=lambda e: e["tiempo"], reverse=True)
    planeados.sort(key=lambda e: e["tiempo"], reverse=True)

    return {"inesperados": inesperados, "bugcheck": bugcheck, "planeados": planeados}


def imprimir_apagados_inesperados(resultado):
    inesperados = resultado["inesperados"]
    bugcheck = resultado["bugcheck"]
    planeados = resultado["planeados"]

    print("\n" + "=" * 60)
    print("APAGADOS INESPERADOS")
    print("=" * 60)

    if not inesperados and not bugcheck:
        print("No se detectaron apagados o reinicios inesperados en el rango revisado.")
        return

    print(f"\nSe detectaron {len(inesperados)} evento(s) de apagado/reinicio no controlado:\n")
    for e in inesperados:
        print(f"  [{e['tiempo']}] {e['proveedor']} (ID {e['event_id']})")
        if e["mensaje"]:
            print(f"      {e['mensaje']}")

    if bugcheck:
        print(f"\nDe estos, {len(bugcheck)} corresponden a pantallas azules (BSOD) con codigo de error:\n")
        for e in bugcheck:
            codigo = e["mensaje"].split()[0].strip().lower() if e["mensaje"] else "desconocido"
            pista = BUGCHECK_HINTS.get(codigo, "codigo no catalogado, revisa el link de mas info")
            print(f"  [{e['tiempo']}] Codigo: {codigo}  ->  {pista}")
            print(f"      Mas info: {e['url_busqueda']}")

    sin_bugcheck = len(inesperados) - len(bugcheck)
    if sin_bugcheck > 0:
        print(f"\n{sin_bugcheck} apagado(s) inesperado(s) NO tienen un codigo de BSOD asociado.")
        print("  Esto suele indicar: corte de energia, apagado forzado (boton), sobrecalentamiento")
        print("  con apagado de proteccion, o fallo subito de la fuente de poder / hardware.")

    if planeados:
        print(f"\n(Contexto: se registraron {len(planeados)} apagados/reinicios planeados en el mismo rango)")

    print("\nRecomendacion:")
    print("  - Si se repite seguido, revisa temperaturas (HWMonitor/HWiNFO) y la fuente de poder.")
    print("  - Si hay un codigo BSOD repetido, actualiza o reinstala el driver/hardware relacionado.")
    print("  - Revisa el log 'System' con el Visor de Eventos justo en la hora del apagado para mas contexto.")


def guardar_csv(eventos, ruta):
    if os.path.isdir(ruta):
        sugerencia = os.path.join(ruta, "reporte.csv")
        print(f"\nERROR: '{ruta}' es una carpeta, no un archivo.")
        print(f"  --salida necesita la ruta COMPLETA incluyendo el nombre del CSV, por ejemplo:")
        print(f"  --salida \"{sugerencia}\"")
        return

    try:
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["log", "tiempo", "nivel", "proveedor", "event_id",
                               "tarea", "mensaje", "categoria", "url_busqueda"]
            )
            writer.writeheader()
            writer.writerows(eventos)
        print(f"\nReporte guardado en: {ruta}")
    except PermissionError:
        print(f"\nERROR: no se pudo escribir en '{ruta}'.")
        print("  Verifica que sea la ruta de un ARCHIVO (con nombre y extension .csv), no una carpeta,")
        print("  y que tengas permisos de escritura en esa ubicacion.")
    except OSError as e:
        print(f"\nERROR al guardar el CSV en '{ruta}': {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Revision de logs de Windows para detectar fallas y apagados inesperados."
    )
    parser.add_argument("--dias", type=int, default=7,
                         help="Cuantos dias hacia atras revisar (default: 7)")
    parser.add_argument("--logs", type=str, default="System,Application",
                         help="Logs a revisar, separados por coma (default: System,Application). "
                              "Escribe 'todos' para revisar TODOS los logs del sistema (mas lento). "
                              "Otras opciones comunes: Setup, Security (requiere admin).")
    parser.add_argument("--incluir-advertencias", action="store_true",
                         help="Incluir tambien advertencias (nivel 3), no solo errores/criticos")
    parser.add_argument("--sin-apagados", action="store_true",
                         help="Omitir la seccion de deteccion de apagados inesperados")
    parser.add_argument("--top", type=int, default=10,
                         help="Cuantos eventos recientes mostrar con detalle completo (default: 10)")
    parser.add_argument("--salida", type=str, default=None,
                         help="Ruta COMPLETA del archivo CSV a generar, incluyendo el nombre "
                              "(ej: D:\\Revision_PC\\reporte.csv). No es solo una carpeta. Opcional.")
    args = parser.parse_args()

    nivel_max = 3 if args.incluir_advertencias else 2
    query = construir_query(nivel_max, args.dias)

    todos_los_eventos = []
    lista_logs_input = [l.strip() for l in args.logs.split(",")]
    if len(lista_logs_input) == 1 and lista_logs_input[0].lower() in ("todos", "all", "*"):
        print("Enumerando todos los logs del sistema (puede tardar varios minutos)...")
        lista_logs = obtener_todos_los_logs()
        print(f"Se encontraron {len(lista_logs)} logs. Revisando cada uno "
              f"(los que requieran permisos que no tienes se omiten automaticamente)...\n")
    else:
        lista_logs = lista_logs_input

    for nombre_log in lista_logs:
        print(f"Consultando log '{nombre_log}'...")
        eventos = consultar_log(nombre_log, query, categoria="general")
        todos_los_eventos.extend(eventos)

    todos_los_eventos.sort(key=lambda e: e["tiempo"], reverse=True)
    imprimir_resumen(todos_los_eventos, top=args.top)

    resultado_apagados = None
    if not args.sin_apagados:
        resultado_apagados = detectar_apagados_inesperados(args.dias)
        imprimir_apagados_inesperados(resultado_apagados)

    if args.salida:
        combinados = {(e["log"], e["tiempo"], e["proveedor"], e["event_id"]): e for e in todos_los_eventos}
        if resultado_apagados:
            for grupo in resultado_apagados.values():
                for e in grupo:
                    clave = (e["log"], e["tiempo"], e["proveedor"], e["event_id"])
                    if clave not in combinados:
                        combinados[clave] = e
        guardar_csv(list(combinados.values()), args.salida)


if __name__ == "__main__":
    main()
