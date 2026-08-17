"""Corre TODAS las suites de evaluación (inbound + outbound) y guarda resultados por caso.

Estructura de salida (una carpeta por llamada/caso):
  evaluaciones/
    inbound/llamada-{N}/scores.json + transcripcion.txt + resumen.md
    outbound/{externalId}/scores.json + transcripcion.txt + resumen.md
    resultados_completos.json          (agregado para el reporte)

Suites inbound:  suite1 heurísticas, suite2 LLM-judges (juez1 qwen2.5:7b),
                 suite3 reglas Proaco (juez2 qwen2.5-coder:7b), 7-reglas (juez1).
Suites outbound: heurísticas outbound, LLM-judges GEval (cliente_no_interesado,
                 agendamiento_cita).

Uso:
  .venv/bin/python opik/correr_todas.py [--solo inbound|outbound]
      [--sin-llm] [--juez qwen2.5:7b] [--juez2 qwen2.5-coder:7b] [--threads 1]
"""

import argparse
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
INBOUND = os.path.join(BASE, "inbound")
OUTBOUND = os.path.join(BASE, "outbound")
EVALUACIONES = os.path.join(BASE, os.pardir, "evaluaciones")
sys.path.insert(0, INBOUND)
sys.path.insert(0, OUTBOUND)

import opik  # noqa: E402

from evaluar import cargar_items as cargar_inbound  # noqa: E402
import pruebas_ampliadas as pa  # noqa: E402
from evaluar_outbound import cargar_items as cargar_outbound  # noqa: E402
import evaluar_outbound as eo  # noqa: E402

FUENTE_INBOUND = os.path.join(INBOUND, "transcripciones", "llamadas_reales.json")
FUENTE_OUTBOUND = os.path.join(OUTBOUND, "transcripciones", "llamadas_outbound.json")


def recolectar_por_caso(resultado):
    """Devuelve {llamada_id: {metric: {value, reason}}} desde un resultado de evaluate()."""
    casos = {}
    for test in resultado.test_results:
        contenido = test.test_case.dataset_item.get_content()
        llamada = contenido["metadata"]["llamada_id"]
        casos[llamada] = {
            s.name: {"value": s.value, "reason": s.reason}
            for s in test.score_results
        }
    return casos


def guardar_caso(flow, llamada_id, transcripcion, metadata, suites_por_caso):
    """Escribe la carpeta de evaluación de una llamada."""
    carpeta = os.path.join(EVALUACIONES, flow, llamada_id)
    os.makedirs(carpeta, exist_ok=True)

    if transcripcion:
        with open(os.path.join(carpeta, "transcripcion.txt"), "w", encoding="utf-8") as f:
            f.write(transcripcion)

    with open(os.path.join(carpeta, "scores.json"), "w", encoding="utf-8") as f:
        json.dump({"llamada_id": llamada_id, "metadata": metadata, "suites": suites_por_caso},
                  f, ensure_ascii=False, indent=2)

    lineas = [f"# {flow} - {llamada_id}", ""]
    if metadata.get("contacto"):
        lineas.append(f"Contacto: {metadata['contacto']}")
    if metadata.get("outcome"):
        lineas.append(f"Outcome: {metadata['outcome']}")
    if metadata.get("duration"):
        lineas.append(f"Duración: {metadata['duration']}s")
    lineas += ["", "## Scores por suite", ""]
    for suite, metricas in suites_por_caso.items():
        lineas.append(f"### {suite}")
        for metrica, info in sorted(metricas.items()):
            valor = info["value"]
            if isinstance(valor, float):
                lineas.append(f"- {metrica}: {valor:.2f}")
            else:
                lineas.append(f"- {metrica}: {valor}")
            if info.get("reason"):
                lineas.append(f"  - {info['reason']}")
        lineas.append("")
    with open(os.path.join(carpeta, "resumen.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo", choices=["inbound", "outbound"], help="correr solo un flow")
    parser.add_argument("--sin-llm", action="store_true", help="solo heurísticas (sin LLM)")
    parser.add_argument("--juez", default="qwen2.5:7b")
    parser.add_argument("--juez2", default="qwen2.5-coder:7b")
    parser.add_argument("--threads", type=int, default=None)
    args = parser.parse_args()

    opik.configure(use_local=True, install_mcp=False, automatic_approvals=True)
    resultados = {}
    reporte = {}

    if args.solo != "outbound":
        print("\n======== INBOUND ========", flush=True)
        items = cargar_inbound(FUENTE_INBOUND)
        payloads = pa.construir_payloads(items)
        print(f"Cargadas {len(payloads)} llamadas inbound", flush=True)
        threads = args.threads or 1
        opik.configure(project_name="voicebot-proaco-inbound", use_local=True, install_mcp=False, automatic_approvals=True)

        if not args.sin_llm:
            pa.suite_llm_judges(payloads, args.juez, threads)
        pa.suite_heuristicas(payloads)
        r = pa.suite_reglas_proaco(payloads, args.juez, threads)
        reporte["inbound_7reglas_juez1"] = recolectar_por_caso(r)
        if not args.sin_llm:
            r = pa.suite_reglas_proaco(payloads, args.juez2, threads)
            reporte["inbound_7reglas_juez2"] = recolectar_por_caso(r)

    if args.solo != "inbound":
        print("\n======== OUTBOUND ========", flush=True)
        items = cargar_outbound(FUENTE_OUTBOUND)
        print(f"Cargadas {len(items)} llamadas outbound", flush=True)
        threads = args.threads or 1
        opik.configure(project_name="voicebot-proaco-outbound", use_local=True, install_mcp=False, automatic_approvals=True)

        r = eo.run_evaluacion(items, llm=False, juez_modelo=args.juez, threads=threads,
                              experiment_name="proaco-outbound-7-reglas")
        reporte["outbound_7reglas"] = recolectar_por_caso(r)
        if not args.sin_llm:
            r = eo.run_evaluacion(items, llm=True, juez_modelo=args.juez, threads=threads,
                                  experiment_name="proaco-outbound-llmjudges")
            reporte["outbound_llmjudges"] = recolectar_por_caso(r)

    # --- guardar una carpeta por caso ---
    print("\n======== GUARDANDO CARPETAS POR CASO ========", flush=True)

    # 1. transcripciones (una carpeta por llamada)
    for flow, fuente, cargar in (
        ("inbound", FUENTE_INBOUND, cargar_inbound),
        ("outbound", FUENTE_OUTBOUND, cargar_outbound),
    ):
        for it in cargar(fuente):
            carpeta = os.path.join(EVALUACIONES, flow, str(it["llamada_id"]))
            os.makedirs(carpeta, exist_ok=True)
            with open(os.path.join(carpeta, "transcripcion.txt"), "w", encoding="utf-8") as f:
                f.write(it["transcripcion"])

    # 2. scores por caso (unión de todas las suites)
    for suite, casos in reporte.items():
        flow = "inbound" if suite.startswith("inbound_") else "outbound"
        fuentes = cargar_inbound(FUENTE_INBOUND) if flow == "inbound" else cargar_outbound(FUENTE_OUTBOUND)
        for llamada, metricas in casos.items():
            metadata = next((it.get("metadata", {}) for it in fuentes if str(it["llamada_id"]) == llamada), {})
            resultados.setdefault(llamada, {"llamada_id": llamada, "flow": flow,
                                            "metadata": metadata, "suites": {}})
            resultados[llamada]["suites"][suite] = metricas

    for llamada, info in resultados.items():
        guardar_caso(info["flow"], llamada, "", info["metadata"], info["suites"])

    with open(os.path.join(EVALUACIONES, "resultados_completos.json"), "w", encoding="utf-8") as f:
        json.dump(list(resultados.values()), f, ensure_ascii=False, indent=1)
    print(f"Guardadas {len(resultados)} carpetas en {EVALUACIONES}", flush=True)


if __name__ == "__main__":
    main()
