"""
Evaluación del voicebot Proaco con DeepEval (juez mejorado).

Métrica custom que llama directamente al modelo con prompts mejorados
(rúbrica + CoT + anclas de score). Soporta Ollama local y Groq cloud.

Uso:
  # Ollama local (sin API key):
  .venv/bin/python deepeval/inbound/evaluar.py

  # Groq cloud (requiere API key):
  export GROQ_API_KEY="gsk_..."
  .venv/bin/python deepeval/inbound/evaluar.py --modelo groq/qwen/qwen3.6-27b

Requiere: pip install deepeval
"""

import json
import os
import sys
import time
import re

INBOUND_DIR = os.path.dirname(os.path.abspath(__file__))
DEEPEVAL_DIR = os.path.dirname(INBOUND_DIR)
ROOT = os.path.dirname(DEEPEVAL_DIR)
EVALUACIONES = os.path.join(ROOT, "evaluaciones")
DEEPEVAL_OUT = os.path.join(EVALUACIONES, "deepeval")
SHARED = os.path.join(ROOT, "shared")
FUENTE = os.path.join(ROOT, "opik", "inbound", "transcripciones", "llamadas_reales.json")
DEFAULT_MODEL = "ollama/qwen2.5:7b"
sys.path.insert(0, SHARED)
from juez_mejorado import REGLAS_PROACO, build_system_prompt, build_evaluation_prompt

# ── Cargar transcripciones ─────────────────────────────────────────────────────
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
    result = []
    for i, item in enumerate(items):
        result.append({
            "llamada_id": str(item.get("id", f"item_{i}")),
            "transcripcion": a_texto(item["transcripcion"]),
            "metadata": item.get("metadata", {}),
        })
    return result


# ── Llamada al modelo con retry ───────────────────────────────────────────────
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


def parse_score_json(text):
    """Extrae score y reason del response del modelo. Maneja thinking tokens de Qwen."""
    if not text:
        return 0.0, "empty response"

    # Buscar JSON directamente en el texto COMPLETO (antes de limpiar thinking)
    # El JSON puede estar dentro o fuera del bloque <think>
    match = re.search(r'\{[^{}]*"score"\s*:\s*([0-9.]+)\s*,\s*"reason"\s*:\s*"([^"]*)"[^{}]*\}', text)
    if match:
        score = float(match.group(1))
        reason = match.group(2)
        return max(0.0, min(1.0, score)), reason

    # Buscar patrón score en texto
    nums = re.findall(r'"score"\s*:\s*([01]\.?\d*)', text)
    reasons = re.findall(r'"reason"\s*:\s*"([^"]*)"', text)
    if nums:
        return max(0.0, min(1.0, float(nums[0]))), reasons[0] if reasons else f"partial parse: {text[:80]}"

    # Limpiar thinking y reintentar
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"<think>.*", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<tool_call>.*", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    try:
        obj = json.loads(cleaned)
        return max(0.0, min(1.0, float(obj["score"]))), str(obj.get("reason", ""))
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    return 0.0, f"parse_error: {text[:150]}"


# ── Evaluar una llamada ────────────────────────────────────────────────────────
def evaluar_llamada(item, model_name):
    """Evalúa las 7 reglas Proaco con el juez mejorado."""
    transcription = item["transcripcion"]
    system_prompt = build_system_prompt()
    scores = {}

    for key in REGLAS_PROACO:
        user_prompt = build_evaluation_prompt(key).replace("{transcripcion}", transcription)
        try:
            raw = llamar_modelo(model_name, system_prompt, user_prompt)
            score, reason = parse_score_json(raw)
            scores[key] = {"value": score, "reason": reason}
        except Exception as e:
            scores[key] = {"value": 0.0, "reason": f"Error: {e}"}
        time.sleep(1)  # Ollama local no tiene rate limit, pero evita sobrecarga

    return scores


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--modelo", default=DEFAULT_MODEL, help=f"Modelo juez. Default: {DEFAULT_MODEL}. Con '/' = cloud (necesita API key).")
    parser.add_argument("--solo", help="Evaluar solo la llamada con este ID (ej: llamada-1)")
    args = parser.parse_args()

    if "/" in args.modelo and not args.modelo.startswith("ollama/"):
        proveedor = args.modelo.split("/")[0]
        key_var = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY",
                   "anthropic": "ANTHROPIC_API_KEY"}.get(proveedor)
        if key_var and not os.environ.get(key_var):
            raise SystemExit(
                f"Modelo cloud '{args.modelo}' requiere {key_var}.\n"
                f"export {key_var}='...'\n"
                "O usá --modelo ollama/qwen2.5:7b (local, sin key)"
            )

    items = cargar_items(FUENTE)
    print(f"Cargadas {len(items)} llamadas desde {FUENTE}")

    if args.solo:
        items = [it for it in items if it["llamada_id"] == args.solo]
        if not items:
            raise SystemExit(f"No se encontró la llamada {args.solo}")

    print(f"Modelo juez: {args.modelo}")
    print(f"Métricas: {', '.join(REGLAS_PROACO.keys())}")

    os.makedirs(DEEPEVAL_OUT, exist_ok=True)

    resultados = []
    for i, item in enumerate(items):
        llamada_id = item["llamada_id"]
        print(f"\n[{i+1}/{len(items)}] Evaluando llamada {llamada_id}...", flush=True)

        scores = evaluar_llamada(item, args.modelo)
        avg = sum(s["value"] for s in scores.values()) / len(scores) if scores else 0
        print(f"  avg={avg:.3f}  ", end="")
        for nombre, info in scores.items():
            print(f"{nombre[:12]}={info['value']:.2f}", end=" ")
        print()

        resultado = {
            "llamada_id": llamada_id,
            "metadata": item.get("metadata", {}),
            "scores": scores,
            "avg": avg,
        }
        resultados.append(resultado)

        carpeta = os.path.join(DEEPEVAL_OUT, llamada_id)
        os.makedirs(carpeta, exist_ok=True)
        with open(os.path.join(carpeta, "scores_deep.json"), "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)

    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN DeepEval - Juez Mejorado (Groq " + args.modelo + ")")
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
        "tool": "deepeval",
        "judge": "juez_mejorado",
        "model": args.modelo,
        "n_llamadas": len(resultados),
        "promedios": {n: sum(v)/len(v) for n, v in sorted(metricas_acum.items())},
        "global_avg": global_avg,
        "por_llamada": resultados,
    }
    out_path = os.path.join(DEEPEVAL_OUT, "resultados_deep.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(consolidado, f, ensure_ascii=False, indent=2)
    print(f"\nResultados guardados en: {out_path}")


if __name__ == "__main__":
    main()
