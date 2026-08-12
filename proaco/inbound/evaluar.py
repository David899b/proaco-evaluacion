"""
Evaluación offline del voicebot Grupo Proaco (Camila Mendoza CNX).

1. Lee las transcripciones de transcripciones/ (JSON, JSONL o carpeta de .txt).
2. Crea/actualiza el dataset en Opik.
3. Corre evaluate() con las métricas LLM-judge de Proaco (Qwen 2.5 vía Ollama).

Formato de transcripción:
  JSON:  [{"id": "...", "transcripcion": "texto" | [{"speaker": "BOT", "text": "..."}, ...]}, ...]
  JSONL: un objeto por línea (mismos campos)
  TXT:   archivos con turnos "[BOT] ..." / "[CLIENTE] ..." (el nombre del archivo es el id)

Uso:
  .venv/bin/python proaco-evaluacion/evaluar.py [ruta_dataset|ruta_archivo|carpeta]
"""

import json
import os
import sys

import opik
from opik.evaluation import evaluate
from opik.evaluation.models import LiteLLMChatModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metricas_proaco import crear_metricas_proaco  # noqa: E402

PROJECT_NAME = "voicebot-proaco-inbound"
DATASET_NAME = "transcripciones-proaco-inbound"
PREFIX = "proaco-inbound"
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


def leer_archivo(ruta):
    """Lee un archivo JSON/JSONL/TXT y devuelve items {id, transcripcion, ...}."""
    items = []
    ext = os.path.splitext(ruta)[1].lower()
    with open(ruta, encoding="utf-8") as f:
        if ext in (".json", ".jsonl"):
            if ext == ".json":
                data = json.load(f)
                data = data.get("transcripciones", data) if isinstance(data, dict) else data
            else:
                data = [json.loads(linea) for linea in f if linea.strip()]
            for i, item in enumerate(data):
                items.append({
                    "llamada_id": str(item.get("id", f"item_{i}")),
                    "transcripcion": a_texto(item["transcripcion"]),
                    "metadata": item.get("metadata", {}),
                })
        elif ext == ".txt":
            texto = f.read()
            items.append({
                "llamada_id": os.path.splitext(os.path.basename(ruta))[0],
                "transcripcion": texto,
                "metadata": {},
            })
    return items


def cargar_items(fuente):
    """Carga items desde un archivo o una carpeta."""
    items = []
    if os.path.isfile(fuente):
        items.extend(leer_archivo(fuente))
    elif os.path.isdir(fuente):
        for nombre in sorted(os.listdir(fuente)):
            if nombre.lower().endswith((".json", ".jsonl", ".txt")):
                items.extend(leer_archivo(os.path.join(fuente, nombre)))
    else:
        raise SystemExit(f"No existe la ruta: {fuente}")
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


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("fuente", nargs="?", default=CARPETA_DEFECTO)
    parser.add_argument("--juez", default=os.environ.get("JUEZ_MODELO", JUEZ_MODELO),
                        help=f"modelo juez. Default: {JUEZ_MODELO}. Con '/' = proveedor cloud.")
    parser.add_argument("--threads", type=int, default=None,
                        help="task_threads. Default: 8 en nube, 1 en Ollama")
    args = parser.parse_args()
    fuente = args.fuente

    items = cargar_items(fuente)
    if not items:
        raise SystemExit("No se encontraron transcripciones. Revisá la carpeta transcripciones/")

    print(f"Cargadas {len(items)} transcripciones desde: {fuente}")

    opik.configure(project_name=PROJECT_NAME, use_local=True)

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

    juez = crear_juez(args.juez)
    metricas = crear_metricas_proaco(juez)

    def tarea(item):
        return {"transcripcion": item["transcripcion"]}

    threads = args.threads if args.threads is not None else (8 if "/" in args.juez else 1)
    print(f"Juez: {args.juez} | task_threads={threads}")

    resultado = evaluate(
        dataset=dataset,
        task=tarea,
        scoring_metrics=metricas,
        task_threads=threads,
        experiment_name=f"{PREFIX}-7-reglas",
    )

    print("\n=== RESUMEN POR LLAMADA ===")
    for test in resultado.test_results:
        contenido = test.test_case.dataset_item.get_content()
        llamada = contenido["metadata"]["llamada_id"]
        scores = ", ".join(f"{s.name}={s.value:.2f}" for s in test.score_results)
        print(f"{llamada:<20} -> {scores}")
    print("\nResultados completos en http://localhost:5173 → proyecto 'voicebot-proaco-inbound'")


if __name__ == "__main__":
    main()
