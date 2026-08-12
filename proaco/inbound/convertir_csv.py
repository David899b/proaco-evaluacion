"""
Convierte el CSV exportado de Google Sheets (voicebot scripts) al formato JSON
que espera evaluar.py:

  {"transcripciones": [{"id", "transcripcion": [{"speaker", "text"}], "metadata"}]}

Estructura del CSV:
  - fila "TEST N"  -> comienza un nuevo test
  - fila "Agent"/"Caller" -> speaker, seguido de su texto
  - filas con etiquetas (proaco_list_intent, getCalDotComAvailability,
    scheduleCalDotComAppointment, proaco_resolve_intent) entre turnos -> se
    registran en metadata como intents/tools usados
  - filas "Prev Test"/"Next Test" -> navegación, se ignoran
"""

import csv
import json
import os
import re
import sys

RUTA_CSV = os.path.expanduser("~/Downloads/voicebot scripts - Sheet1.csv")
RUTA_SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcripciones", "llamadas_reales.json")

SPEAKERS = {"Agent", "Caller"}
HERRAMIENTAS = {
    "proaco_list_intent",
    "proaco_resolve_intent",
    "getCalDotComAvailability",
    "scheduleCalDotComAppointment",
}


def parsear(ruta):
    with open(ruta, newline="", encoding="utf-8") as f:
        filas = [row[0] for row in csv.reader(f) if row]

    tests = []
    actual = None
    speaker_pendiente = None

    for celda in filas:
        if celda is None:
            continue
        celda = celda.strip()
        if not celda:
            continue
        if celda == "Prev Test" or celda == "Next Test":
            continue

        m = re.fullmatch(r"TEST\s+(\d+)", celda, flags=re.IGNORECASE)
        if m:
            actual = {"id": f"llamada-{int(m.group(1))}", "turnos": [], "herramientas": []}
            tests.append(actual)
            speaker_pendiente = None
            continue

        if not actual:
            continue

        if celda in SPEAKERS:
            speaker_pendiente = celda
            continue

        if celda in HERRAMIENTAS:
            actual["herramientas"].append(celda)
            speaker_pendiente = None
            continue

        if speaker_pendiente:
            actual["turnos"].append({
                "speaker": "BOT" if speaker_pendiente == "Agent" else "CLIENTE",
                "text": celda,
            })
            speaker_pendiente = None

    return tests


def a_json(tests):
    items = []
    vistos = set()
    for t in tests:
        clave = (json.dumps(t["turnos"], ensure_ascii=False), tuple(t["herramientas"]))
        if clave in vistos:
            print(f"  (duplicado omitido: {t['id']})")
            continue
        vistos.add(clave)
        items.append({
            "id": t["id"],
            "transcripcion": t["turnos"],
            "metadata": {
                "canal": "voz",
                "origen": "google_sheets",
                "intents": list(dict.fromkeys(t["herramientas"])),
                "tools": t["herramientas"],
            },
        })
    return {"transcripciones": items}


def main():
    tests = parsear(RUTA_CSV)
    if not tests:
        raise SystemExit("No se encontraron tests en el CSV")

    datos = a_json(tests)
    os.makedirs(os.path.dirname(RUTA_SALIDA), exist_ok=True)
    with open(RUTA_SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    print(f"Parseados {len(tests)} tests -> {RUTA_SALIDA}")
    for t in tests:
        print(f"  {t['id']}: {len(t['turnos'])} turnos, tools={t['herramientas']}")
    return RUTA_SALIDA


if __name__ == "__main__":
    main()
