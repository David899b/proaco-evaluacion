#!/usr/bin/env python3
"""Genera PDF combinado: Reporte Completo + Resumen Equipo desde markdown."""
import os
import subprocess
import tempfile

BASE = "/Users/david899/Documents/Default Project/proaco-evaluacion"

# Leer los dos markdowns
with open(os.path.join(BASE, "REPORTE_EVALUACION_PROACO.md"), encoding="utf-8") as f:
    reporte_completo = f.read()

with open(os.path.join(BASE, "HANDOFF.md"), encoding="utf-8") as f:
    handoff = f.read()

# Extraer la sección "Resumen para el Equipo" del handoff (o usar el reporte completo + resumen)
# El handoff ya tiene la sección "Resumen para el Equipo (1 página)"

# CSS del md_a_html.py original
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
    """Conversión simple markdown -> HTML (tablas, headers, listas, código)."""
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
    
    # Procesar bloques de código
    bloques = re.split(r"```", md_text)
    out = []
    for i, bloque in enumerate(bloques):
        if i % 2 == 1:
            out.append("<pre>" + html.escape(bloque.strip("\n")) + "</pre>")
            continue
        # Procesar tablas en el bloque
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

# Construir HTML completo: Reporte Completo + separador + Resumen Equipo
html_parts = []

# 1. Reporte Completo
html_parts.append(md_to_html(reporte_completo))

# 2. Separador de página
html_parts.append('<div class="page-break"></div>')

# 3. Resumen para el Equipo (extraído de HANDOFF.md - sección después de "## Resumen para el Equipo")
# El handoff ya tiene una sección "## Resumen para el Equipo (1 página)" - la usamos
# Para simplificar, incluimos el handoff completo como apéndice
html_parts.append('<h1>Apéndice: Handoff y Próximos Pasos</h1>')
html_parts.append(md_to_html(handoff))

body = "\n\n".join(html_parts)
html_doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>{body}</body></html>"""

# Guardar HTML temporal
with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
    f.write(html_doc)
    html_path = f.name

# Generar PDF con Chrome headless
pdf_path = os.path.join(BASE, "REPORTE_EVALUACION_PROACO_COMPLETO.pdf")
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cmd = [
    chrome,
    "--headless",
    "--disable-gpu",
    "--no-margins",
    "--print-to-pdf=" + pdf_path,
    html_path
]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
os.unlink(html_path)

if result.returncode == 0:
    print(f"✅ PDF generado: {pdf_path}")
else:
    print(f"❌ Error: {result.stderr}")
