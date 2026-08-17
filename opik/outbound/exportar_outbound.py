"""Exporta llamadas del voicebot OUTBOUND de Proaco desde el API de Lula.

API: https://api.lula.com  (auth por header X-API-Key)
Flujo:
  1. GET /v1/campaigns                  → busca la campaña de Proaco por nombre.
  2. GET /v1/campaigns/{id}/touchpoints → toca todos los touchpoints (con transcript).
  3. Convierte los transcripts (role: user/assistant/tool_call) a turnos [CLIENTE]/[BOT]/[TOOL].
  4. Guarda transcripciones/llamadas_outbound.json con metadata proyecto/flow/outcome/duration.

Uso:
  export LULA_API_KEY="api-..."
  .venv/bin/python opik/outbound/exportar_outbound.py [--campaign "Grupo Proaco"] [--size 100]
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_BASE = "https://api.lula.com"
CARPETA_DEFECTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcripciones")
SALIDA_DEFECTO = os.path.join(CARPETA_DEFECTO, "llamadas_outbound.json")


def api_get(url, api_key, reintentos=3):
    req = urllib.request.Request(url, headers={"X-API-Key": api_key, "Accept": "application/json"})
    for intento in range(reintentos):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} en {url} ({e.reason})", file=sys.stderr)
            if e.code in (429, 500, 502, 503, 504) and intento < reintentos - 1:
                time.sleep(2 ** intento)
                continue
            raise SystemExit(f"Error HTTP {e.code} en {url}")
    raise SystemExit(f"No se pudo consultar {url}")


def paginar_touchpoints(campaign_id, api_key, size):
    """Recorre la paginación (data/page/pages/size/total) del endpoint de touchpoints."""
    items = []
    page = 1
    while True:
        url = (f"{API_BASE}/v1/campaigns/{campaign_id}/touchpoints"
               f"?includeTranscripts=true&size={size}&page={page}")
        body = api_get(url, api_key)
        data = body.get("data", [])
        items.extend(data)
        pages = body.get("pages", body.get("totalPages", 1))
        total = body.get("total", body.get("count", len(data)))
        print(f"  página {page}/{pages} · {len(data)} touchpoints ({len(items)}/{total})")
        if page >= pages or not data:
            break
        page += 1
    return items


def a_turnos(transcript):
    """Normaliza un transcript del API (role: user/assistant/tool_call) a turnos [CLIENTE]/[BOT]/[TOOL]."""
    if not transcript:
        return []
    if isinstance(transcript, str):
        return transcript
    lineas = []
    for t in transcript:
        if not isinstance(t, dict):
            continue
        role = str(t.get("role", "")).lower()
        etiqueta = {"user": "CLIENTE", "assistant": "BOT", "tool_call": "TOOL",
                    "tool_call_result": "TOOL", "system": "SISTEMA"}.get(role, role.upper())
        texto = t.get("content", "").strip()
        if not texto:
            continue
        lineas.append({"speaker": etiqueta, "text": texto})
    return lineas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default="Grupo Proaco", help="nombre de la campaña en el API")
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--salida", default=SALIDA_DEFECTO)
    args = parser.parse_args()

    api_key = os.environ.get("LULA_API_KEY")
    if not api_key:
        raise SystemExit("Falta LULA_API_KEY (export LULA_API_KEY=\"api-...\")")

    print("Buscando campañas en el API de Lula...")
    resp_campanas = api_get(f"{API_BASE}/v1/campaigns", api_key)
    campanas = resp_campanas.get("data", resp_campanas) if isinstance(resp_campanas, dict) else resp_campanas
    match = [c for c in campanas if args.campaign.lower() in str(c.get("name", "")).lower()]
    if not match:
        print("Campañas disponibles:")
        for c in campanas:
            print(f"  - {c.get('name')} ({c.get('id')}, status={c.get('status')})")
        raise SystemExit(f"No se encontró la campaña '{args.campaign}'")
    campana = match[0]
    print(f"Campaña: {campana.get('name')} · id={campana.get('id')} · status={campana.get('status')}")

    print("Descargando touchpoints con transcripts...")
    touchpoints = paginar_touchpoints(campana["id"], api_key, args.size)

    items = []
    for t in touchpoints:
        transcript = t.get("transcript")
        nombre = " ".join(filter(None, [t.get("contactFirstName"), t.get("contactLastName")])) or "sin-nombre"
        duration = t.get("duration") or 0
        outcome = t.get("outcome") or t.get("status") or "unknown"
        if t.get("errorMessage"):
            print(f"  - {nombre}: {t['errorMessage']}")
            continue
        turnos = a_turnos(transcript)
        if not turnos:
            continue
        items.append({
            "id": t.get("externalId") or nombre.replace(" ", "-"),
            "transcripcion": turnos,
            "metadata": {
                "proyecto": "proaco",
                "flow": "outbound",
                "contacto": nombre,
                "outcome": outcome,
                "duration": duration,
                "campaign_id": campana["id"],
                "campaign": campana.get("name"),
                "externalId": t.get("externalId"),
                "customFields": (t.get("additionalData") or {}).get("customFields"),
            },
        })

    os.makedirs(os.path.dirname(args.salida), exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Guardadas {len(items)} transcripciones outbound en {args.salida}")


if __name__ == "__main__":
    main()
