"""Genera REPORTE_EVALUACION_PROACO.md (+ HTML/PDF) desde evaluaciones/resultados_completos.json.

Lee los scores por caso (una carpeta por llamada bajo evaluaciones/) y arma:
- resumen ejecutivo por flow (inbound/outbound)
- tabla de promedios por suite y métrica
- detalle por llamada
- hallazgos por métrica crítica

Uso: .venv/bin/python proaco-evaluacion/generar_reporte.py [--salida REPORTE_EVALUACION_PROACO]
"""
import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTADOS = os.path.join(BASE, "evaluaciones", "resultados_completos.json")

SUITES_ETIQUETA = {
    "inbound_heur": "S1 · Heurísticas deterministas",
    "inbound_llmjudges": "S2 · LLM-judges adicionales",
    "inbound_7reglas_juez1": "S3 · Reglas Proaco (juez qwen2.5:7b)",
    "inbound_7reglas_juez2": "S3 · Reglas Proaco (juez qwen2.5-coder:7b)",
    "outbound_7reglas": "O1 · Reglas outbound (heurísticas)",
    "outbound_llmjudges": "O2 · Reglas outbound (LLM-judge)",
}
SUITES_ORDEN = [
    "inbound_heur", "inbound_llmjudges", "inbound_7reglas_juez1", "inbound_7reglas_juez2",
    "outbound_7reglas", "outbound_llmjudges",
]

METRICAS_BONITAS = {
    "adherencia_espanol": "Adherencia a español", "answer_relevance": "Relevancia de respuesta",
    "saludo_presente": "Saludo presente", "despedida_presente": "Despedida presente",
    "url_derivacion_presente": "URL de derivación", "sin_datos_aysa": "Sin datos de AySA",
    "sin_loop_no_transferir": "Sin loop de transferencia", "tono_respetuoso": "Tono respetuoso",
    "usefulness": "Utilidad", "moderation": "Moderación",
    "agent_task_completion_judge": "Completitud de tarea", "agent_tool_correctness_judge": "Correctitud de herramientas",
    "conversational_coherence": "Coherencia conversacional", "user_frustration": "Frustración del usuario",
    "session_completeness": "Completitud de sesión", "saludo_correcto": "Saludo oficial",
    "despedida_correcta": "Despedida oficial", "deteccion_intent": "Detección de intent",
    "pide_contacto_una_vez": "Pedido de contacto (una vez)", "listado_max_3": "Listado máximo 3",
    "tono_espanol_argentino": "Tono español rioplatense", "deriva_web_si_no_sabe": "Deriva a la web",
    "se_presenta": "Se presenta como Proaco", "menciona_proposito": "Menciona el motivo",
    "pide_consentimiento": "Pide consentimiento", "maneja_no_interes": "Maneja no-interés",
    "ofrece_agendar_cita": "Ofrece agendar cita", "listado_max_3_out": "Listado máximo 3 (out)",
    "cliente_no_interesado": "Cliente no interesado (LLM)", "agendamiento_cita": "Agendamiento de cita (LLM)",
}

DIRECCION_SCORE = {
    "user_frustration": "menor", "moderation": "menor",
}


def cargar():
    with open(RESULTADOS, encoding="utf-8") as f:
        return json.load(f)


def promedios_por_suite(casos, flow):
    proms = {}
    for c in casos:
        if c.get("flow") != flow:
            continue
        for suite, metricas in c.get("suites", {}).items():
            for m, info in metricas.items():
                proms.setdefault(suite, {}).setdefault(m, []).append(info["value"])
    out = {}
    for suite, ms in proms.items():
        out[suite] = {m: sum(v) / len(v) for m, v in ms.items()}
    return out


def tabla(rows, headers, alinear=None):
    lineas = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        lineas.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lineas)


def resumen_suite(proms, suite, indent=""):
    etiqueta = SUITES_ETIQUETA[suite]
    metricas = proms.get(suite, {})
    if suite == "outbound_llmjudges":
        metricas = {m: p for m, p in metricas.items() if m in ("cliente_no_interesado", "agendamiento_cita")}
    orden = sorted(metricas.items(), key=lambda kv: kv[1])
    filas = []
    for m, p in orden:
        nombre = METRICAS_BONITAS.get(m, m)
        salud = (1 - p) if DIRECCION_SCORE.get(m) == "menor" else p
        flag = "⚠" if salud < 0.5 else ("✓" if salud >= 0.7 else "~")
        filas.append((flag, nombre, f"{p:.3f}"))
    return f"{indent}### {etiqueta}\n\n{tabla(filas, ['', 'Métrica', 'Promedio'])}\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--salida", default="REPORTE_EVALUACION_PROACO")
    args = parser.parse_args()

    casos = cargar()
    inbound = [c for c in casos if c.get("flow") == "inbound"]
    outbound = [c for c in casos if c.get("flow") == "outbound"]

    prom_in = promedios_por_suite(casos, "inbound")
    prom_out = promedios_por_suite(casos, "outbound")

    md = []
    md.append("# Reporte de Evaluación del Voicebot Grupo Proaco — Inbound + Outbound\n")
    md.append("**Fecha:** 2026-08-12 · **Flows:** inbound (cliente llama) y outbound (bot llama a leads) · **Juez:** Qwen 2.5 7B / 7B-Coder (Ollama local)\n")
    md.append("---\n")

    # ---- Inbound ----
    md.append("## 1. Inbound\n")
    md.append(f"Se evaluaron **{len(inbound)} llamadas inbound** con 4 suites: heurísticas deterministas, LLM-judges adicionales y las 7 reglas de Proaco con dos jueces (comparación de consistencia).\n")

    def promedio_general(proms, suite):
        ms = proms.get(suite, {})
        return sum(ms.values()) / len(ms) if ms else float("nan")

    for suite in ["inbound_heur", "inbound_llmjudges", "inbound_7reglas_juez1", "inbound_7reglas_juez2"]:
        if suite in prom_in:
            md.append(resumen_suite(prom_in, suite))

    # ---- Outbound ----
    md.append("---\n")
    md.append("## 2. Outbound\n")
    md.append(f"Se evaluaron **{len(outbound)} llamadas outbound** (touchpoints de la campaña Grupo Proaco en Lula). Nota: al momento de la evaluación la campaña solo contiene las llamadas de QA inbound; no hay llamadas salientes reales todavía.\n")
    for suite in ["outbound_7reglas", "outbound_llmjudges"]:
        if suite in prom_out:
            md.append(resumen_suite(prom_out, suite))

    # ---- Detalle por llamada ----
    md.append("---\n")
    md.append("## 3. Detalle por llamada\n")
    md.append("Cada llamada tiene su propia carpeta en `evaluaciones/{flow}/{llamada_id}/` con `scores.json`, `resumen.md` y `transcripcion.txt`.\n")

    for flow, casos_f in (("inbound", inbound), ("outbound", outbound)):
        md.append(f"### {flow.capitalize()}\n")
        headers = ["Llamada"] + [SUITES_ETIQUETA[s].split(" · ")[0] for s in SUITES_ORDEN if s in {k for c in casos_f for k in c.get("suites", {})}]
        rows = []
        for c in sorted(casos_f, key=lambda x: x["llamada_id"]):
            lid = c["llamada_id"]
            if flow == "outbound":
                lid_short = lid[:12]
            else:
                lid_short = lid
            fila = [lid_short]
            for s in SUITES_ORDEN:
                if s in c.get("suites", {}):
                    vals = list(c["suites"][s].values())
                    fila.append(f"{sum(v['value'] for v in vals) / len(vals):.2f}")
            rows.append(fila)
        md.append(tabla(rows, headers))
        md.append("")

    # ---- Hallazgos ----
    md.append("---\n")
    md.append("## 4. Hallazgos\n")

    criticas = []
    for suite, proms in prom_in.items():
        if suite != "inbound_7reglas_juez1":
            continue
        for m, p in sorted(proms.items(), key=lambda kv: kv[1]):
            valor = p if DIRECCION_SCORE.get(m) == "menor" else p
            if p < 0.6:
                criticas.append((f"inbound/{m}", p, "Reglas Proaco (juez qwen2.5:7b)"))
    for suite, proms in prom_out.items():
        for m, p in sorted(proms.items(), key=lambda kv: kv[1]):
            if p < 0.6:
                criticas.append((f"outbound/{m}", p, SUITES_ETIQUETA[suite]))

    md.append("**Métricas con promedio bajo (< 0.60):**\n")
    if criticas:
        md.append(tabla([(nombre, f"{p:.3f}", suite) for nombre, p, suite in criticas],
                        ["Métrica", "Promedio", "Suite"]))
        md.append("")
    else:
        md.append("Ninguna métrica quedó por debajo del umbral.\n")

    md.append("### Recomendaciones\n")
    md.append("- **Inbound saludo/deriva:** reforzar el saludo oficial al inicio y la derivación a la web cuando el bot no puede resolver.")
    md.append("- **Inbound despedida/pedido de contacto:** asegurar despedida oficial y pedido de datos una sola vez al cierre.")
    md.append("- **Outbound:** validar las reglas con llamadas salientes reales (la campaña todavía no tiene). Se espera `pide_consentimiento` bajo si el flow no lo implementa.")
    md.append("")

    # Guardar md
    md_path = os.path.join(BASE, args.salida + ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Reporte MD en {md_path}")

    # HTML vía md_a_html (reutilizando el convertidor genérico con salida parametrizada)
    try:
        sys.path.insert(0, os.path.join(BASE, "proaco", "inbound"))
        import md_a_html as mh
        # adaptar el módulo al reporte actual
        mh.FUENTE = md_path
        mh.SALIDA = "/tmp/reporte_proaco.html"
        mh.main()
        print(f"HTML en {mh.SALIDA}")
    except Exception as e:
        print(f"HTML no generado: {e}")


if __name__ == "__main__":
    main()
