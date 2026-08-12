"""Descarga por-call feedback scores de las suites ampliadas desde Opik y arma tablas."""
import json
import os
import urllib.request

BASE = "http://localhost:5173/api/v1/private/datasets/{}/items/experiments/items?size=20&experiment_ids={}"

SUITES = {
    "heur": {
        "dsid": "019ff16c-c7a3-7095-9a83-1f04e3c21040",
        "eid": "019ff171-6401-726f-9516-87521f2cd7fa",
        "metricas": ["saludo_presente", "despedida_presente", "url_derivacion_presente",
                     "sin_datos_aysa", "sin_loop_no_transferir", "tono_respetuoso", "adherencia_espanol"],
    },
    "judge": {
        "dsid": "019ff175-5063-776b-bc87-4d05a5996f93",
        "eid": "019ff1f6-e507-72d6-b8b7-5276c59e016f",
        "metricas": ["usefulness", "answer_relevance", "moderation",
                     "agent_tool_correctness_judge", "agent_task_completion_judge",
                     "conversational_coherence", "user_frustration", "session_completeness"],
    },
    "juez2": {
        "dsid": "019ff21e-9b65-7628-bc8b-471c97579534",
        "eid": "019ff21e-9da4-7bd8-90a1-0b8778fa410a",
        "metricas": ["saludo_correcto", "despedida_correcta", "deteccion_intent",
                     "pide_contacto_una_vez", "listado_max_3", "tono_espanol_argentino",
                     "deriva_web_si_no_sabe"],
    },
}


def fetch(dsid, eid):
    url = BASE.format(dsid, json.dumps([eid]).replace(" ", ""))
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def llamada_id(it):
    data = it.get("data") or {}
    if isinstance(data, dict):
        meta = data.get("metadata") or {}
        if isinstance(meta, dict) and meta.get("llamada_id"):
            return meta["llamada_id"]
    return it["id"][:8]


def main():
    orden = None
    por_llamada = {}
    for tag, cfg in SUITES.items():
        data = fetch(cfg["dsid"], cfg["eid"])
        for it in data["content"]:
            for ei in it["experiment_items"]:
                lid = llamada_id(it)
                por_llamada.setdefault(lid, {})[tag] = {
                    fs["name"]: fs["value"] for fs in ei["feedback_scores"]
                }
    orden = sorted(por_llamada)
    for tag, cfg in SUITES.items():
        print(f"\n### {tag} ###")
        print("llamada | " + " | ".join(m[:12] for m in cfg["metricas"]))
        for lid in orden:
            fila = por_llamada[lid].get(tag, {})
            celda = []
            for m in cfg["metricas"]:
                v = fila.get(m)
                celda.append("-" if v is None else f"{v:.2f}")
            print(lid + " | " + " | ".join(celda))
    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados_suites.json")
    json.dump(por_llamada, open(salida, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nsalvado en {salida}")


if __name__ == "__main__":
    main()
