"""Baja los feedback scores de TODAS las suites desde Opik (REST local) y arma:

1. evaluaciones/{inbound|outbound}/{llamada_id}/  → scores.json + resumen.md + transcripcion.txt
   (una carpeta por caso/llamada)
2. evaluaciones/resultados_completos.json           → agregado para el reporte

Suites inbound:  heurísticas (suite1), llm-judges (suite2), 7-reglas juez1 (qwen2.5:7b),
                 7-reglas juez2 (qwen2.5-coder:7b).
Suites outbound: 7-reglas (heurísticas), llm-judges GEval.

Uso: .venv/bin/python proaco-evaluacion/organizar_evaluaciones.py
"""
import json
import os
import sys
import urllib.request

INBOUND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proaco", "inbound")
OUTBOUND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proaco", "outbound")
sys.path.insert(0, INBOUND)
sys.path.insert(0, OUTBOUND)
from evaluar import cargar_items as cargar_inbound  # noqa: E402
from evaluar_outbound import cargar_items as cargar_outbound  # noqa: E402

BASE_ITEMS = "http://localhost:5173/api/v1/private/datasets/{}/items/experiments/items?size=50&experiment_ids={}"
EVALUACIONES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluaciones")

# suite -> (dataset_id, experiment_id, nombre_experimento)
SUITES = {
    "inbound_heur": ("019ff345-6867-729a-9680-4fab3c9e50ab", "019ff3f2-50ab-71e2-8b42-a3ba13deb0de", "proaco-inbound-heurísticas-deterministas"),
    "inbound_llmjudges": ("019ff3b9-a68f-7496-b1b8-46653d188249", "019ff3b9-a811-77db-b413-f62421484057", "proaco-inbound-llm-judges-adicionales"),
    "inbound_7reglas_juez1": ("019ff3f2-5c1a-707f-82d1-59624bf07f07", "019ff3f2-5d02-78f8-be1a-457ae9fde4b0", "proaco-inbound-reglas-proaco-juez-qwen2.5:7b"),
    "inbound_7reglas_juez2": ("019ff3f2-5c1a-707f-82d1-59624bf07f07", "019ff401-01e1-7e45-95c9-d1ba9d72057f", "proaco-inbound-reglas-proaco-juez-qwen2.5-coder:7b"),
    "outbound_7reglas": ("019ff3b0-0159-7036-9bd3-9a8df5470eae", "019ff41f-23a0-7763-a477-dbfb54767fd5", "proaco-outbound-7-reglas"),
    "outbound_llmjudges": ("019ff3b0-0159-7036-9bd3-9a8df5470eae", "019ff655-41ee-72ca-acfb-758d293181e5", "proaco-outbound-llmjudges"),
}


def fetch(dataset_id, experiment_id):
    url = BASE_ITEMS.format(dataset_id, json.dumps([experiment_id]).replace(" ", ""))
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def llamada_id(it):
    data = it.get("data") or {}
    if isinstance(data, dict):
        meta = data.get("metadata") or {}
        if isinstance(meta, dict) and meta.get("llamada_id"):
            return str(meta["llamada_id"])
    return it["id"][:8]


def main():
    resultados = {}
    for suite, (dsid, eid, nombre) in SUITES.items():
        if eid == "PENDIENTE":
            continue
        print(f"Bajando suite {suite} ({nombre})...")
        data = fetch(dsid, eid)
        n = 0
        for it in data["content"]:
            lid = llamada_id(it)
            for ei in it["experiment_items"]:
                scores = {s["name"]: {"value": s["value"], "reason": s.get("reason", "")}
                          for s in ei.get("feedback_scores", [])}
                if not scores:
                    continue
                resultados.setdefault(lid, {"llamada_id": lid, "suites": {}})
                resultados[lid]["suites"][suite] = scores
                n += 1
        print(f"  {n} llamadas con scores")
        if n == 0:
            print("  ATENCION: sin scores, revisar experiment_id")

    # transcripciones
    fuentes = {}
    for flow, fuente, cargar in (
        ("inbound", os.path.join(INBOUND, "transcripciones", "llamadas_reales.json"), cargar_inbound),
        ("outbound", os.path.join(OUTBOUND, "transcripciones", "llamadas_outbound.json"), cargar_outbound),
    ):
        fuentes[flow] = {str(it["llamada_id"]): it for it in cargar(fuente)}

    # carpetas por caso
    for lid, info in resultados.items():
        flow = "inbound" if lid in fuentes["inbound"] else "outbound"
        it = fuentes[flow].get(lid, {})
        carpeta = os.path.join(EVALUACIONES, flow, lid)
        os.makedirs(carpeta, exist_ok=True)
        with open(os.path.join(carpeta, "transcripcion.txt"), "w", encoding="utf-8") as f:
            f.write(it.get("transcripcion", ""))
        with open(os.path.join(carpeta, "scores.json"), "w", encoding="utf-8") as f:
            json.dump({"llamada_id": lid, "metadata": it.get("metadata", {}), "suites": info["suites"]},
                      f, ensure_ascii=False, indent=1)
        lineas = [f"# {flow} - {lid}", ""]
        meta = it.get("metadata", {})
        if meta.get("contacto"):
            lineas.append(f"Contacto: {meta['contacto']}")
        if meta.get("outcome"):
            lineas.append(f"Outcome: {meta['outcome']}")
        if meta.get("duration"):
            lineas.append(f"Duración: {meta['duration']}s")
        lineas += ["", "## Scores por suite", ""]
        for suite, metricas in sorted(info["suites"].items()):
            lineas.append(f"### {suite}")
            for metrica, s in sorted(metricas.items()):
                lineas.append(f"- {metrica}: {s['value']:.2f}")
                if s.get("reason"):
                    lineas.append(f"  - {s['reason']}")
            lineas.append("")
        with open(os.path.join(carpeta, "resumen.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lineas))

    lista = []
    for lid, info in resultados.items():
        flow = "inbound" if lid in fuentes["inbound"] else "outbound"
        info["flow"] = flow
        info["metadata"] = fuentes[flow].get(lid, {}).get("metadata", {})
        lista.append(info)
    with open(os.path.join(EVALUACIONES, "resultados_completos.json"), "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=1)
    print(f"\nCarpetas por caso en {EVALUACIONES} ({len(lista)} casos)")


if __name__ == "__main__":
    main()
