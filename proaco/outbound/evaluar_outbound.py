"""
Evaluación offline del voicebot OUTBOUND de Grupo Proaco (llamadas salientes).

Flujo idéntico a ../inbound/evaluar.py pero con las reglas del flow outbound:
  1. Lee transcripciones/llamadas_outbound.json (generado por exportar_outbound.py).
  2. Crea/actualiza el dataset en Opik (proyecto voicebot-proaco-outbound).
  3. Corre las heurísticas de metricas_proaco_outbound.py (y opcionalmente los
     LLM-judges GEval con --llm).

Uso:
  .venv/bin/python proaco-evaluacion/proaco/outbound/evaluar_outbound.py [--llm]
"""

import json
import os
import sys

import opik
from opik.evaluation import evaluate
from opik.evaluation.models import LiteLLMChatModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metricas_proaco_outbound import HEURISTICAS_OUTBOUND, crear_metricas_proaco_outbound  # noqa: E402

PROJECT_NAME = "voicebot-proaco-outbound"
DATASET_NAME = "transcripciones-proaco-outbound-heuristicas"
PREFIX = "proaco-outbound"
CARPETA_DEFECTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcripciones")
JUEZ_MODELO = "qwen2.5:7b"


def a_texto(transcripcion):
    """Normaliza una transcripción (string o lista de turnos) a texto [BOT]/[CLIENTE]."""
    if isinstance(transcripcion, str):
        return transcripcion
    lineas = []
    for turno in transcripcion:
        speaker = str(turno.get("speaker", "")).upper()
        etiqueta = "BOT" if speaker in ("BOT", "AGENTE", "AGENT", "ASISTENTE") else "CLIENTE"
        lineas.append(f"[{etiqueta}] {turno.get('text', '')}")
    return "\n".join(lineas)


def cargar_items(fuente):
    """Carga items desde el JSON exportado por exportar_outbound.py."""
    with open(fuente, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("transcripciones", [])
    items = []
    for i, item in enumerate(data):
        items.append({
            "llamada_id": str(item.get("id", f"item_{i}")),
            "transcripcion": a_texto(item["transcripcion"]),
            "metadata": item.get("metadata", {}),
        })
    return items


def crear_juez(modelo):
    """LiteLLMChatModel para el juez. Con '/' = proveedor cloud (valida API key); sin '/' = Ollama local."""
    if "/" not in modelo:
        modelo = f"ollama/{modelo}"
    proveedor = modelo.split("/", 1)[0].lower()
    var = {
        "openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY", "mistral": "MISTRAL_API_KEY",
        "together": "TOGETHER_API_KEY", "deepseek": "DEEPSEEK_API_KEY", "cohere": "COHERE_API_KEY",
    }.get(proveedor)
    if var and not os.environ.get(var):
        raise SystemExit(
            f"Falta la API key para el proveedor '{proveedor}': export {var}=... "
            f"(o usá --juez con un modelo de otro proveedor)."
        )
    return LiteLLMChatModel(model_name=modelo)


def run_evaluacion(items, llm=False, juez_modelo=JUEZ_MODELO, threads=None, experiment_name=None):
    """Corre la evaluación outbound y devuelve el resultado de opik.evaluate().

    items: lista de {llamada_id, transcripcion, metadata}
    llm: suma los LLM-judges GEval (cliente_no_interesado, agendamiento_cita).
    """
    opik.configure(project_name=PROJECT_NAME, use_local=True, install_mcp=False, automatic_approvals=True)

    client = opik.Opik()
    dataset = client.get_or_create_dataset(name=DATASET_NAME, project_name=PROJECT_NAME)
    dataset.clear()
    dataset.insert([
        {
            "transcripcion": item["transcripcion"],
            "metadata": {"llamada_id": item["llamada_id"], **item["metadata"]},
        }
        for item in items
    ])
    print(f"Dataset '{DATASET_NAME}' actualizado con {dataset.dataset_items_count} items")

    def tarea(item):
        return {"transcripcion": item["transcripcion"], "output": item["transcripcion"]}

    metricas = HEURISTICAS_OUTBOUND
    nombre_exp = experiment_name or (f"{PREFIX}-llmjudges" if llm else f"{PREFIX}-7-reglas")
    if llm:
        juez = crear_juez(juez_modelo)
        metricas = metricas + crear_metricas_proaco_outbound(juez)

    threads = threads if threads is not None else (8 if "/" in juez_modelo else 1)
    print(f"Juez: {juez_modelo} | task_threads={threads} | métricas: {[m.name for m in metricas]}")

    return evaluate(
        dataset=dataset,
        task=tarea,
        scoring_metrics=metricas,
        task_threads=threads,
        experiment_name=nombre_exp,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("fuente", nargs="?", default=os.path.join(CARPETA_DEFECTO, "llamadas_outbound.json"))
    parser.add_argument("--llm", action="store_true", help="correr también los LLM-judges GEval")
    parser.add_argument("--juez", default=os.environ.get("JUEZ_MODELO", JUEZ_MODELO),
                        help=f"modelo juez. Default: {JUEZ_MODELO}. Con '/' = proveedor cloud.")
    parser.add_argument("--threads", type=int, default=None,
                        help="task_threads. Default: 8 en nube, 1 en Ollama")
    args = parser.parse_args()

    items = cargar_items(args.fuente)
    if not items:
        raise SystemExit("No se encontraron transcripciones en: " + args.fuente)

    print(f"Cargadas {len(items)} transcripciones desde: {args.fuente}")

    resultado = run_evaluacion(items, llm=args.llm, juez_modelo=args.juez, threads=args.threads)

    print("\n=== RESUMEN POR LLAMADA ===")
    for test in resultado.test_results:
        contenido = test.test_case.dataset_item.get_content()
        llamada = contenido["metadata"]["llamada_id"]
        scores = ", ".join(f"{s.name}={s.value:.2f}" for s in test.score_results)
        print(f"{llamada:<20} -> {scores}")
    print("\nResultados completos en http://localhost:5173 → proyecto 'voicebot-proaco-outbound'")


if __name__ == "__main__":
    main()
