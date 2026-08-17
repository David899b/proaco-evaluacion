#!/usr/bin/env python3
"""Genera PDF mejorado: tablas con headers claros, códigos de color, semáforo visual."""
import os
import subprocess
import tempfile
import re

BASE = "/Users/david899/Documents/Default Project/proaco-evaluacion"

with open(os.path.join(BASE, "REPORTE_EVALUACION_PROACO.md"), encoding="utf-8") as f:
    reporte_completo = f.read()

CSS = """
body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 10pt; color: #1a1a1a; line-height: 1.5; margin: 0; }
h1 { font-size: 18pt; color: #0f4c81; border-bottom: 2.5px solid #0f4c81; padding-bottom: 6px; page-break-after: avoid; }
h2 { font-size: 13pt; color: #0f4c81; margin-top: 18px; border-bottom: 1px solid #c9d6e5; padding-bottom: 3px; page-break-after: avoid; }
h3 { font-size: 11pt; color: #0f4c81; margin-top: 14px; page-break-after: avoid; }
p { margin: 5px 0; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 8.5pt; page-break-inside: avoid; }
th { background: #0f4c81; color: #fff; text-align: center; padding: 5px 6px; font-weight: 600; }
td { border: 0.6px solid #b8c6d6; padding: 4px 6px; text-align: center; }
tr:nth-child(even) td { background: #f0f4f9; }
td.left { text-align: left; }
td.good { background: #d4edda !important; color: #155724; font-weight: 600; }
td.warn { background: #fff3cd !important; color: #856404; font-weight: 600; }
td.bad { background: #f8d7da !important; color: #721c24; font-weight: 600; }
ul, ol { margin: 5px 0; padding-left: 18px; }
li { margin: 2px 0; }
code { font-family: 'Menlo', monospace; font-size: 8pt; background: #f2f2f2; padding: 1px 3px; border-radius: 3px; }
pre { font-family: 'Menlo', monospace; font-size: 8pt; background: #f2f2f2; padding: 6px; border-left: 3px solid #0f4c81; white-space: pre-wrap; overflow-x: auto; }
strong { color: #0f4c81; }
hr { border: none; border-top: 1px solid #c9d6e5; margin: 16px 0; }
.page-break { page-break-before: always; }
.legend { font-size: 8pt; margin: 8px 0; }
.legend span { display: inline-block; width: 14px; height: 14px; margin-right: 6px; vertical-align: middle; border-radius: 3px; }
.legend .lg { background: #d4edda; }
.legend .lw { background: #fff3cd; }
.legend .lb { background: #f8d7da; }
"""

def md_to_html(md_text):
    import html
    import re
    
    def inline(texto):
        texto = html.escape(texto)
        texto = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)
        texto = re.sub(r"`([^`]+)`", r"<code>\1</code>", texto)
        return texto
    
    def score_class(val_str):
        """Devuelve clase CSS según score 0-1."""
        try:
            v = float(val_str)
        except:
            return ""
        if v >= 0.75:
            return "good"
        elif v >= 0.50:
            return "warn"
        else:
            return "bad"
    
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
            fila_html = []
            for j, c in enumerate(celdas):
                contenido = inline(c)
                cls = ""
                if k == 0:
                    cls = "th"
                elif k > 0:
                    if j == 0:
                        cls = "left"
                    else:
                        cls = score_class(c)
                fila_html.append(f"<{etiqueta} class='{cls}'>{contenido}</{etiqueta}>")
            filas.append("<tr>" + "".join(fila_html) + "</tr>")
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

# --- Leyenda semáforo ---
LEYENDA = """
<div class="legend">
<strong>Leyenda:</strong>
<span class="lg"></span> Bueno (≥ 0.75)
<span class="lw"></span> Regular (0.50 – 0.74)
<span class="lb"></span> Crítico (< 0.50)
</div>
"""

with open(os.path.join(BASE, "REPORTE_EVALUACION_PROACO.md"), encoding="utf-8") as f:
    reporte_completo = f.read()

html_main = md_to_html(reporte_completo)

# Resumen ejecutivo con semáforo
resumen_equipo = """# Resumen Ejecutivo para el Equipo

## Evaluación Voicebot Proaco — Agosto 2026

**Qué se evaluó:** 13 llamadas inbound reales + 6 touchpoints outbound (QA) contra reglas de negocio Proaco.

**Resultado general:** Inbound **77% promedio** (reglas Proaco, juez qwen2.5:7b). Outbound **0% en métricas de flow saliente** (no hay llamadas outbound reales todavía).

---

## ✅ Lo que funciona bien (🟢 ≥ 0.75)

| Métrica | Score | Estado |
|---------|-------|--------|
| Listado máx 3 (juez1) | 0.93 | 🟢 Excelente |
| Tono español rioplatense (juez1) | 0.82 | 🟢 Bueno |
| Derivación a web (juez1) | 0.83 | 🟢 Bueno |
| Detección de intent (juez1) | 0.75 | 🟢 Límite |
| Tono español rioplatense (juez2) | 0.87 | 🟢 Excelente |
| Derivación a web (juez2) | 0.89 | 🟢 Excelente |

## ⚠️ Qué hay que arreglar (🟡 0.50–0.74 / 🔴 < 0.50)

| Métrica | Score | Estado | Acción |
|---------|-------|--------|--------|
| Saludo oficial (juez1) | 0.62 | 🟡 Regular | Prompt obligatorio + test |
| Pedido de contacto (juez1) | 0.59 | 🟡 Regular | Exactly-once al cierre + test |
| Despedida oficial (juez1) | 0.75 | 🟡 Límite | Fallback obligatorio |
| Saludo oficial (juez2) | 0.35 | 🔴 Crítico | Revisar criterio juez2 |
| Despedida oficial (juez2) | 0.49 | 🔴 Crítico | Revisar criterio juez2 |
| Listado máx 3 (juez2) | 0.54 | 🟡 Regular | Revisar criterio juez2 |
| Heurística `maneja_no_interes` | Falso positivo | 🔴 Bug | Reescribir (match "gracias" saludo) |

## 🚫 Outbound — Sin datos reales
Las 6 llamadas son **inbound de QA**, no outbound. Métricas de flow saliente = **0%**.  
**Próximo paso:** configurar campaña outbound real en Lula con leads de prueba.

---

## Roadmap (Próximos Sprints)

| Sprint | Foco | Entregable | Tiempo |
|--------|------|------------|--------|
| 1 | Inbound crítico | Saludo, contacto, despedida, heurística fix → >0.80 reglas | 1-2 sem |
| 2 | Outbound real | Campaña Lula con leads → exportar → evaluar heurísticas + GEval | 2-3 sem |
| 3 | Juez cloud + CI | Groq llama-3.3-70b (gratis) + pipeline automático en merge | 1 sem |

---

## Artefactos listos
- `evaluaciones/inbound/llamada-{1..13}/` — scores.json, resumen.md, transcripcion.txt
- `evaluaciones/outbound/CA.../` — 6 carpetas
- `REPORTE_EVALUACION_PROACO.md` — reporte completo
- `evaluaciones/resultados_completos.json` — agregado para BI
"""

# Construir HTML final
html_main = md_to_html(reporte_completo)
html_resumen = md_to_html(resumen_equipo)

body = f"""{LEYENDA}
{html_main}
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