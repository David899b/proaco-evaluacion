#!/usr/bin/env python3
"""Genera PDF: Reporte Completo + Resumen Equipo (sin sección quién hace qué)."""
import os
import subprocess
import tempfile
import re

BASE = "/Users/david899/Documents/Default Project/proaco-evaluacion"

with open(os.path.join(BASE, "REPORTE_EVALUACION_PROACO.md"), encoding="utf-8") as f:
    reporte_completo = f.read()

CSS = """
body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 10.5pt; color: #1a1a1a; line-height: 1.55; margin: 0; }
h1 { font-size: 19pt; color: #0f4c81; border-bottom: 2.5px solid #0f4c81; padding-bottom: 6px; page-break-after: avoid; }
h2 { font-size: 14pt; color: #0f4c81; margin-top: 22px; border-bottom: 1px solid #c9d6e5; padding-bottom: 3px; page-break-after: avoid; }
h3 { font-size: 11.5pt; color: #0f4c81; margin-top: 16px; page-break-after: avoid; }
h4 { font-size: 10.5pt; color: #333; page-break-after: avoid; }
p { margin: 6px 0; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 8.5pt; page-break-inside: avoid; }
th { background: #0f4c81; color: #fff; text-align: left; padding: 5px 8px; }
td { border: 0.6px solid #b8c6d6; padding: 4px 8px; }
tr:nth-child(even) td { background: #f0f4f9; }
ul, ol { margin: 6px 0; padding-left: 20px; }
li { margin: 3px 0; }
code, pre { font-family: 'Menlo', monospace; font-size: 8.5pt; background: #f2f2f2; }
pre { padding: 8px; border-left: 3px solid #0f4c81; white-space: pre-wrap; }
strong { color: #0f4c81; }
hr { border: none; border-top: 1px solid #c9d6e5; margin: 20px 0; }
.page-break { page-break-before: always; }
"""

def md_to_html(md_text):
    import html
    import re
    
    def inline(texto):
        texto = html.escape(texto)
        texto = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)
        texto = re.sub(r"`([^`]+)`", r"<code>\1</code>", texto)
        return texto
    
    def tablas(texto):
        lineas = texto.split("\n")
        out = []
        i = 0
        while i < len(lineas):
            if lineas[i].startswith("|"):
                tabla = []
                while i < len(lineas) and lineas[i].startswith("|"):
                    tabla.append(lineas[i])
                    i += 1
                if len(tabla) >= 2:
                    out.append(_tabla_html(tabla))
                continue
            out.append(lineas[i])
            i += 1
        return "\n".join(out)
    
    def _tabla_html(tabla):
        filas = []
        for k, linea in enumerate(tabla):
            celdas = [c.strip() for c in linea.strip("|").split("|")]
            if k == 1 and all(re.fullmatch(r":?-{3,}:?", c) for c in celdas):
                continue
            etiqueta = "th" if k == 0 else "td"
            filas.append("<tr>" + "".join(f"<{etiqueta}>{inline(c)}</{etiqueta}>" for c in celdas) + "</tr>")
        return "<table>" + "\n".join(filas) + "</table>"
    
    bloques = re.split(r"```", md_text)
    out = []
    for i, bloque in enumerate(bloques):
        if i % 2 == 1:
            out.append("<pre>" + html.escape(bloque.strip("\n")) + "</pre>")
            continue
        bloque = tablas(bloque)
        for parrafo in bloque.split("\n\n"):
            p = parrafo.strip()
            if not p:
                continue
            if re.fullmatch(r"-{3,}", p):
                out.append("<hr>")
            elif p.startswith("# "):
                out.append(f"<h1>{inline(p[2:])}</h1>")
            elif p.startswith("## "):
                out.append(f"<h2>{inline(p[3:])}</h2>")
            elif p.startswith("### "):
                out.append(f"<h3>{inline(p[4:])}</h3>")
            elif p.startswith("#### "):
                out.append(f"<h4>{inline(p[5:])}</h4>")
            elif p.startswith("<table>"):
                out.append(p)
            elif p.startswith("<!---"):
                pass
            elif p.startswith("- ") or p.startswith("* "):
                items = [inline(l[2:]) for l in p.split("\n")]
                out.append("<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>")
            elif re.match(r"^\d+\. ", p):
                items = [inline(re.sub(r"^\d+\.\s*", "", l)) for l in p.split("\n")]
                out.append("<ol>" + "".join(f"<li>{it}</li>" for it in items) + "</ol>")
            else:
                out.append(f"<p>{inline(p)}</p>")
    return "\n\n".join(out)

# 1. Reporte completo
html_main = md_to_html(reporte_completo)

# 2. Resumen ejecutivo (sección extraída del reporte: 1-2 páginas clave)
resumen_equipo = """# Resumen Ejecutivo para el Equipo

## Evaluación Voicebot Proaco — Agosto 2026

**Qué se evaluó:** 13 llamadas inbound reales + 6 touchpoints outbound (QA) contra reglas de negocio Proaco.

**Resultado general:** Inbound **77% promedio** (reglas Proaco, juez qwen2.5:7b). Outbound **0% en métricas de flow saliente** (no hay llamadas outbound reales todavía).

---

## ✅ Lo que funciona bien
- Listado de propiedades (máx 3 items): **93%**
- Tono español rioplatense: **82%**
- Derivación a web cuando no sabe: **83%**
- Detección de intent: **75%**

## ⚠️ Qué hay que arreglar (Inbound)

| Métrica | Score | Acción |
|---------|-------|--------|
| Saludo oficial | 62% | Prompt obligatorio + test |
| Pedido de contacto | 59% | Exactly-once al cierre + test |
| Despedida oficial | 75% | Fallback obligatorio |
| Heurística `maneja_no_interes` | Falso positivo | Reescribir (evitar match "gracias" del saludo) |

## 🚫 Outbound — Sin datos reales
Las 6 llamadas son **inbound de QA**, no outbound. Métricas de flow saliente (presentación, consentimiento, agenda cita) = **0%**.  
**Próximo paso:** configurar campaña outbound real en Lula con leads de prueba.

---

## Pasos a Seguir (Roadmap)

### Sprint 1 — Correcciones Inbound Críticas (1-2 semanas)
- [ ] Fix saludo obligatorio + test unitario
- [ ] Fix pedido de contacto exactly-once + test
- [ ] Fix despedida obligatoria + fallback
- [ ] Reescribir heurística `maneja_no_interes`
- [ ] Correr suite completa y validar >0.80 en reglas Proaco

### Sprint 2 — Outbound Real (2-3 semanas)
- [ ] Configurar campaña outbound real en Lula con leads de prueba
- [ ] Ejecutar `exportar_outbound.py` → `correr_todas.py --solo outbound`
- [ ] Validar heurísticas outbound contra llamadas reales
- [ ] Ajustar prompts outbound (presentación, consentimiento, agenda cita)

### Sprint 3 — Juez Cloud y Automatización (1 semana)
- [ ] Probar juez Groq `llama-3.3-70b-versatile` (gratis, rápido)
- [ ] Migrar pipeline a juez cloud para evitar throttle térmico
- [ ] CI: correr `organizar_evaluaciones.py` + `generar_reporte.py` en merge

---

## Artefactos Generados
- `evaluaciones/inbound/llamada-{1..13}/` — scores.json, resumen.md, transcripcion.txt
- `evaluaciones/outbound/CA.../` — 6 carpetas
- `REPORTE_EVALUACION_PROACO.md` — reporte completo
- `evaluaciones/resultados_completos.json` — agregado para BI
"""

html_resumen = md_to_html(resumen_equipo)

body = f"""{html_main}
<div class="page-break"></div>
{html_resumen}"""

html_doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>{body}</body></html>"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
    f.write(html_doc)
    html_path = f.name

pdf_path = os.path.join(BASE, "REPORTE_EVALUACION_PROACO_COMPLETO.pdf")
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cmd = [
    chrome, "--headless", "--disable-gpu", "--no-margins",
    "--print-to-pdf=" + pdf_path, html_path
]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
os.unlink(html_path)

if result.returncode == 0:
    print(f"✅ PDF generado: {pdf_path}")
else:
    print(f"❌ Error: {result.stderr}")