#!/usr/bin/env python
"""
Evaluación OUTBOUND con LangSmith + juez mejorado (sin SDK, solo requests).
"""
import json
import os
import sys
import time
import re
import uuid
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from juez_mejorado import build_system_prompt, build_evaluation_prompt

FUENTE = os.path.join(os.path.dirname(__file__), '..', '..', 'opik', 'outbound', 'transcripciones', 'llamadas_outbound.json')
EVAL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'evaluaciones', 'outbound')

LANGSMITH_API_KEY = os.environ.get("LANGCHAIN_API_KEY", "")
LANGSMITH_API = "https://api.smith.langchain.com/api/v1"

MODELO_DEFAULT = "ollama/qwen2.5:7b"

REGLAS_OUTBOUND = {
    "se_presenta": (
        "sePresenta: El bot se identifica como Grupo Proaco al inicio de la llamada. "
        "Puntuá 1.0 si dice 'Grupo Proaco' o 'Proaco' al principio. "
        "Puntuá 0.5 si se presenta genéricamente pero no dice la marca. "
        "Puntuá 0.0 si no se presenta."
    ),
    "menciona_proposito": (
        "mencionaProposito: El bot explica el motivo de la llamada. "
        "Puntuá 1.0 si dice por qué llama. "
        "Puntuá 0.5 si es ambiguo. "
        "Puntuá 0.0 si no explica el motivo."
    ),
    "pide_consentimiento": (
        "pideConsentimiento: El bot pregunta si puede continuar. "
        "Puntuá 1.0 si pregunta explícitamente. "
        "Puntuá 0.5 si lo implifica. "
        "Puntuá 0.0 si no pregunta."
    ),
    "maneja_no_interes": (
        "manejaNoInteres: Ante 'no me interesa', cierra cortésmente sin insistir. "
        "Puntuá 1.0 si cierra con gracia. "
        "Puntuá 0.5 si insiste una vez. "
        "Puntuá 0.0 si insiste más de una vez."
    ),
    "ofrece_agendar_cita": (
        "ofreceAgendarCita: Si hay interés, ofrece agendar cita/visita. "
        "Puntuá 1.0 si ofrece agendar o derivar. "
        "Puntuá 0.5 si menciona opciones pero no concreta. "
        "Puntuá 0.0 si no ofrece nada."
    ),
    "listado_max_3": (
        "listadoMax3: Si lista propiedades, máximo 3 y solo lo que pidió. "
        "Puntuá 1.0 si lista 1-3 correctas. "
        "Puntuá 0.5 si lista más de 3 o incorrectas. "
        "Puntuá 0.0 si lista muchas sin filtrar."
    ),
    "tono_respetuoso": (
        "tonoRespetuoso: Tono respetuoso, sin insultos ni agresividad. "
        "Puntuá 1.0 si es cortés. "
        "Puntuá 0.0 si hay insultos o agresividad."
    ),
}


def api_get(path):
    r = requests.get(f"{LANGSMITH_API}{path}", headers={"X-API-Key": LANGSMITH_API_KEY}, timeout=30)
    r.raise_for_status()
    return r.json()


def api_post(path, data):
    r = requests.post(f"{LANGSMITH_API}{path}", headers={"X-API-Key": LANGSMITH_API_KEY, "Content-Type": "application/json"},
                      json=data, timeout=30)
    r.raise_for_status()
    return r.json()


def a_texto(transcripcion):
    if isinstance(transcripcion, str):
        return transcripcion
    lineas = []
    for turno in transcripcion:
        speaker = str(turno.get("speaker", "")).upper()
        etiqueta = "BOT" if speaker in ("BOT", "AGENTE", "AGENT") else "CLIENTE"
        lineas.append(f"[{etiqueta}] {turno.get('text', '')}")
    return "\n".join(lineas)


def cargar_items():
    with open(FUENTE, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for item in data:
        texto = a_texto(item.get("transcripcion", []))
        items.append({
            "id": item["id"],
            "transcripcion": texto,
            "metadata": item.get("metadata", {}),
        })
    return items


def llamar_modelo(system_prompt, user_prompt, modelo, max_retries=3):
    import litellm
    for intento in range(max_retries):
        try:
            resp = litellm.completion(
                model=modelo,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                num_predict=512,
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"    [error] {e}")
            if intento < max_retries - 1:
                time.sleep(5)
    return None


def parse_score_json(texto):
    match = re.search(r'\{[^{}]*"score"[^{}]*\}', texto, re.DOTALL)
    if match:
        try:
            d = json.loads(match.group())
            return float(d.get("score", 0)), d.get("reason", "")
        except (json.JSONDecodeError, ValueError):
            pass
    if '"score"' in texto:
        scores = re.findall(r'"score"\s*:\s*([\d.]+)', texto)
        reasons = re.findall(r'"reason"\s*:\s*"([^"]*)"', texto)
        if scores:
            return float(scores[0]), reasons[0] if reasons else ""
    return 0.0, "no se pudo parsear"


def evaluar_llamada(item, modelo):
    system_prompt = build_system_prompt()
    scores = {}
    for metrica, criterio in REGLAS_OUTBOUND.items():
        user_prompt = criterio + "\n\nTRANSCRIPCIÓN:\n" + item["transcripcion"]
        raw = llamar_modelo(system_prompt, user_prompt, modelo)
        if raw:
            score, reason = parse_score_json(raw)
        else:
            score, reason = 0.0, "modelo no respondió"
        scores[metrica] = {"value": round(score, 2), "reason": reason}
    return scores


def log_to_langsmith(project_id, item, scores):
    try:
        run_id = str(uuid.uuid4())
        api_post("/runs", {
            "id": run_id,
            "session_id": project_id,
            "name": f"eval-outbound-{item['id'][:16]}",
            "run_type": "chain",
            "inputs": {"id": item["id"], "transcripcion": item["transcripcion"][:500]},
            "outputs": {"scores": {k: v["value"] for k, v in scores.items()}},
        })
        for metrica, info in scores.items():
            api_post("/feedback", {
                "run_id": run_id,
                "key": metrica,
                "score": info["value"],
                "comment": info.get("reason", ""),
            })
        return run_id
    except Exception as e:
        print(f"    [warn: no se pudo loguear: {e}]")
        return None


def connect_langsmith():
    print("Conectando a LangSmith...", end=" ", flush=True)
    sessions = api_get("/sessions")
    if isinstance(sessions, list):
        sessions_list = sessions
    else:
        sessions_list = sessions.get("sessions", [])
    project_id = None
    for s in sessions_list:
        if s.get("name") == "proaco-outbound-eval":
            project_id = s["id"]
            break
    if not project_id:
        r = api_post("/sessions", {"name": "proaco-outbound-eval"})
        project_id = r["id"]
    print(f"OK (project={project_id[:8]}...)")
    return project_id


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--modelo", default=MODELO_DEFAULT)
    parser.add_argument("--solo", help="ID de una llamada específica")
    args = parser.parse_args()

    if not LANGSMITH_API_KEY:
        print("Error: LANGCHAIN_API_KEY no configurada")
        return

    items = cargar_items()
    if args.solo:
        items = [i for i in items if i["id"] == args.solo or i["id"].startswith(args.solo)]
        if not items:
            print(f"No se encontró llamada: {args.solo}")
            return

    print(f"Cargadas {len(items)} llamadas outbound")
    print(f"Modelo: {args.modelo}\n")

    project_id = connect_langsmith()

    resultados = []
    for idx, item in enumerate(items, 1):
        print(f"[{idx}/{len(items)}] Evaluando {item['id'][:20]}...")
        scores = evaluar_llamada(item, args.modelo)
        avg = sum(s["value"] for s in scores.values()) / len(scores)
        print(f"  avg={avg:.3f}  " + "  ".join(f"{k[:12]}={v['value']:.2f}" for k, v in scores.items()))

        os.makedirs(os.path.join(EVAL_DIR, item["id"]), exist_ok=True)
        with open(os.path.join(EVAL_DIR, item["id"], "scores_langsmith.json"), "w") as f:
            json.dump({"id": item["id"], "avg": round(avg, 3), "scores": scores}, f, indent=2, ensure_ascii=False)

        log_to_langsmith(project_id, item, scores)
        resultados.append({"id": item["id"], "avg": round(avg, 3), "scores": scores})

    promedios = {}
    for regla in REGLAS_OUTBOUND:
        vals = [r["scores"][regla]["value"] for r in resultados if regla in r["scores"]]
        promedios[regla] = round(sum(vals) / len(vals), 3) if vals else 0

    global_avg = round(sum(promedios.values()) / len(promedios), 3)

    summary = {
        "herramienta": "LangSmith",
        "modelo": args.modelo,
        "tipo": "outbound",
        "n_llamadas": len(resultados),
        "promedios": promedios,
        "global_avg": global_avg,
        "langsmith_project_id": project_id,
        "llamadas": resultados,
    }

    os.makedirs(EVAL_DIR, exist_ok=True)
    with open(os.path.join(EVAL_DIR, "resultados_langsmith_outbound.json"), "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"RESUMEN LangSmith OUTBOUND - {args.modelo}")
    print(f"{'='*60}")
    for k, v in sorted(promedios.items()):
        print(f"  {k:30s} avg={v:.3f}")
    print(f"\n  GLOBAL  avg={global_avg:.3f}")
    print(f"LangSmith UI: https://smith.langchain.com/projects/{project_id}")


if __name__ == "__main__":
    main()
