"""
Evaluación del voicebot Proaco con LangSmith (juez Ollama local).

Usa requests directo contra la API de LangSmith (sin SDK).
Crea dataset, corre evaluaciones con juez mejorado, y logea resultados
en LangSmith para visualización en la UI.

Uso:
  export LANGCHAIN_API_KEY="lsv2_..."
  python langsmith/inbound/evaluar.py [--solo llamada-1] [--modelo ollama/qwen2.5:7b]

Requiere: requests (ya instalado) + LANGCHAIN_API_KEY
"""

import json
import os
import sys
import time
import re
import uuid

# ── Configuración ──────────────────────────────────────────────────────────────
INBOUND_DIR = os.path.dirname(os.path.abspath(__file__))
LANGSMITH_DIR = os.path.dirname(INBOUND_DIR)
ROOT = os.path.dirname(LANGSMITH_DIR)
EVALUACIONES = os.path.join(ROOT, "evaluaciones")
LANGSMITH_OUT = os.path.join(EVALUACIONES, "langsmith")
SHARED = os.path.join(ROOT, "shared")
FUENTE = os.path.join(ROOT, "opik", "inbound", "transcripciones", "llamadas_reales.json")
DEFAULT_MODEL = "ollama/qwen2.5:7b"
API_BASE = "https://api.smith.langchain.com/api/v1"
PROJECT_NAME = "voicebot-proaco"
DATASET_NAME = "transcripciones-proaco-evaluacion"

sys.path.insert(0, SHARED)
from juez_mejorado import REGLAS_PROACO, build_system_prompt, build_evaluation_prompt

# ── LangSmith API helpers ──────────────────────────────────────────────────────
import requests as req


def get_headers():
    api_key = os.environ.get("LANGCHAIN_API_KEY")
    if not api_key:
        raise SystemExit(
            "Falta LANGCHAIN_API_KEY: export LANGCHAIN_API_KEY='lsv2_...'\n"
            "Obtenela en https://smith.langchain.com/settings"
        )
    return {"X-API-Key": api_key, "Content-Type": "application/json"}


def api_get(path):
    r = req.get(f"{API_BASE}{path}", headers=get_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def api_post(path, data):
    r = req.post(f"{API_BASE}{path}", headers=get_headers(), json=data, timeout=60)
    r.raise_for_status()
    return r.json()


def api_put(path, data):
    r = req.put(f"{API_BASE}{path}", headers=get_headers(), json=data, timeout=60)
    r.raise_for_status()
    return r.json()


def api_delete(path):
    r = req.delete(f"{API_BASE}{path}", headers=get_headers(), timeout=30)
    return r.status_code in (200, 204)


# ── Dataset management ─────────────────────────────────────────────────────────
def get_or_create_project():
    """Obtiene o crea el proyecto (session) en LangSmith."""
    try:
        sessions = api_get("/sessions")
        for s in sessions:
            if s.get("name") == PROJECT_NAME:
                return s["id"]
    except Exception:
        pass

    result = api_post("/sessions", {"name": PROJECT_NAME})
    return result["id"]


def get_or_create_dataset(project_id):
    """Obtiene o crea el dataset asociado al proyecto."""
    try:
        datasets = api_get("/datasets")
        for d in datasets:
            if d.get("name") == DATASET_NAME:
                return d["id"]
    except Exception:
        pass

    result = api_post("/datasets", {
        "name": DATASET_NAME,
        "description": "13 transcripciones inbound reales del voicebot Grupo Proaco",
        "metadata": {"proyecto": "proaco", "flow": "inbound", "n_llamadas": 13},
    })
    return result["id"]


def upload_examples(dataset_id, items):
    """Sube transcripciones como examples al dataset."""
    # Limpiar examples existentes
    try:
        existing = api_get(f"/examples?dataset_id={dataset_id}")
        for ex in existing.get("examples", []):
            api_delete(f"/examples/{ex['id']}")
    except Exception:
        pass

    # Subir nuevos
    count = 0
    for item in items:
        api_post("/examples", {
            "dataset_id": dataset_id,
            "inputs": {
                "transcripcion": item["transcripcion"],
                "llamada_id": item["llamada_id"],
            },
            "outputs": {},
            "metadata": item.get("metadata", {}),
        })
        count += 1
    return count


# ── LLM Judge ──────────────────────────────────────────────────────────────────
def parse_score_json(text):
    """Extrae score y reason del response del modelo."""
    if not text:
        return 0.0, "empty response"

    match = re.search(r'\{[^{}]*"score"\s*:\s*([0-9.]+)\s*,\s*"reason"\s*:\s*"([^"]*)"[^{}]*\}', text)
    if match:
        return max(0.0, min(1.0, float(match.group(1)))), match.group(2)

    nums = re.findall(r'"score"\s*:\s*([01]\.?\d*)', text)
    reasons = re.findall(r'"reason"\s*:\s*"([^"]*)"', text)
    if nums:
        return max(0.0, min(1.0, float(nums[0]))), reasons[0] if reasons else "partial"

    return 0.0, f"parse_error: {text[:100]}"


def llamar_modelo(model_name, system_prompt, user_prompt, retries=4):
    import litellm
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    for attempt in range(retries):
        try:
            response = litellm.completion(
                model=model_name,
                messages=messages,
                temperature=0,
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < retries - 1:
                wait = (attempt + 1) * 6
                print(f"\n    [rate limit, esperando {wait}s...]", end="", flush=True)
                time.sleep(wait)
            else:
                raise
    return None


def evaluar_regla(transcripcion, rule_key, model_name):
    """Evalúa una regla sobre una transcripción."""
    system_prompt = build_system_prompt()
    user_prompt = build_evaluation_prompt(rule_key).replace("{transcripcion}", transcripcion)
    try:
        raw = llamar_modelo(model_name, system_prompt, user_prompt)
        score, reason = parse_score_json(raw)
        return score, reason
    except Exception as e:
        return 0.0, f"Error: {e}"


# ── Log results to LangSmith ───────────────────────────────────────────────────
def log_evaluation(project_id, dataset_id, item, scores):
    """Loguea una evaluación como run + feedback en LangSmith."""
    try:
        run_id = str(uuid.uuid4())
        # Crear run
        api_post("/runs", {
            "id": run_id,
            "session_id": project_id,
            "name": f"eval-{item['llamada_id']}",
            "run_type": "chain",
            "inputs": {"llamada_id": item["llamada_id"], "transcripcion": item["transcripcion"][:500]},
            "outputs": {"scores": {k: v["value"] for k, v in scores.items()}},
            "metadata": item.get("metadata", {}),
        })

        # Log feedback scores
        for metric_name, info in scores.items():
            api_post("/feedback", {
                "run_id": run_id,
                "key": metric_name,
                "score": info["value"],
                "comment": info.get("reason", ""),
            })

        return run_id
    except Exception as e:
        print(f"    [warn: no se pudo loguear a LangSmith: {e}]")
        return None


# ── Main ───────────────────────────────────────────────────────────────────────
def a_texto(transcripcion):
    if isinstance(transcripcion, str):
        return transcripcion
    lineas = []
    for turno in transcripcion:
        speaker = str(turno.get("speaker", "")).upper()
        etiqueta = "BOT" if speaker in ("BOT", "AGENTE", "AGENT", "ASISTENTE") else "CLIENTE"
        lineas.append(f"[{etiqueta}] {turno.get('text', '')}")
    return "\n".join(lineas)


def cargar_items(fuente):
    with open(fuente, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("transcripciones", data) if isinstance(data, dict) else data
    return [
        {
            "llamada_id": str(item.get("id", f"item_{i}")),
            "transcripcion": a_texto(item["transcripcion"]),
            "metadata": item.get("metadata", {}),
        }
        for i, item in enumerate(items)
    ]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--modelo", default=DEFAULT_MODEL, help=f"Modelo juez. Default: {DEFAULT_MODEL}")
    parser.add_argument("--solo", help="Evaluar solo la llamada con este ID (ej: llamada-1)")
    parser.add_argument("--no-langsmith", action="store_true", help="No loguear a LangSmith (solo evaluar local)")
    args = parser.parse_args()

    items = cargar_items(FUENTE)
    print(f"Cargadas {len(items)} llamadas desde {FUENTE}")

    if args.solo:
        items = [it for it in items if it["llamada_id"] == args.solo]
        if not items:
            raise SystemExit(f"No se encontró la llamada {args.solo}")

    print(f"Modelo juez: {args.modelo}")
    print(f"Métricas: {', '.join(REGLAS_PROACO.keys())}")

    os.makedirs(LANGSMITH_OUT, exist_ok=True)

    # ── Configurar LangSmith ────────────────────────────────────────────────
    project_id = None
    dataset_id = None
    if not args.no_langsmith:
        try:
            print("\nConectando a LangSmith...", end=" ", flush=True)
            project_id = get_or_create_project()
            dataset_id = get_or_create_dataset(project_id)
            n = upload_examples(dataset_id, items)
            print(f"OK (project={project_id[:8]}..., dataset={dataset_id[:8]}..., {n} examples)")
        except Exception as e:
            print(f"Error: {e}")
            print("Continuando sin LangSmith (resultados se guardan localmente)")
            args.no_langsmith = True

    # ── Evaluar ─────────────────────────────────────────────────────────────
    resultados = []
    for i, item in enumerate(items):
        llamada_id = item["llamada_id"]
        print(f"\n[{i+1}/{len(items)}] Evaluando llamada {llamada_id}...", flush=True)

        scores = {}
        for j, rule_key in enumerate(REGLAS_PROACO):
            score, reason = evaluar_regla(item["transcripcion"], rule_key, args.modelo)
            scores[rule_key] = {"value": score, "reason": reason}
            if j < len(REGLAS_PROACO) - 1:
                time.sleep(1)

        avg = sum(s["value"] for s in scores.values()) / len(scores) if scores else 0
        print(f"  avg={avg:.3f}  ", end="")
        for nombre, info in scores.items():
            print(f"{nombre[:12]}={info['value']:.2f}", end=" ")
        print()

        # Log a LangSmith
        if not args.no_langsmith and project_id:
            log_evaluation(project_id, dataset_id, item, scores)

        resultado = {
            "llamada_id": llamada_id,
            "metadata": item.get("metadata", {}),
            "scores": scores,
            "avg": avg,
        }
        resultados.append(resultado)

        carpeta = os.path.join(LANGSMITH_OUT, llamada_id)
        os.makedirs(carpeta, exist_ok=True)
        with open(os.path.join(carpeta, "scores_langsmith.json"), "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)

    # ── Resumen ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESUMEN LangSmith - Juez Mejorado (" + args.modelo + ")")
    print("=" * 70)
    metricas_acum = {}
    for r in resultados:
        for nombre, info in r["scores"].items():
            metricas_acum.setdefault(nombre, []).append(info["value"])

    for nombre, valores in sorted(metricas_acum.items()):
        avg = sum(valores) / len(valores)
        print(f"  {nombre:<30} avg={avg:.3f}  n={len(valores)}")

    global_avg = sum(
        p["value"] for r in resultados for p in r["scores"].values()
    ) / sum(len(r["scores"]) for r in resultados) if resultados else 0
    print(f"\n  {'GLOBAL':<30} avg={global_avg:.3f}")

    consolidado = {
        "tool": "langsmith",
        "judge": "juez_mejorado",
        "model": args.modelo,
        "n_llamadas": len(resultados),
        "promedios": {n: sum(v)/len(v) for n, v in sorted(metricas_acum.items())},
        "global_avg": global_avg,
        "por_llamada": resultados,
        "langsmith_project_id": project_id,
        "langsmith_dataset_id": dataset_id,
    }
    out_path = os.path.join(LANGSMITH_OUT, "resultados_langsmith.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(consolidado, f, ensure_ascii=False, indent=2)
    print(f"\nResultados guardados en: {out_path}")

    if project_id:
        print(f"LangSmith UI: https://smith.langchain.com/projects/{project_id}")


if __name__ == "__main__":
    main()
