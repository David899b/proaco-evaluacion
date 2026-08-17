"""Convierte REPORTE_EVALUACION_PROACO_INBOUND.md a HTML autocontenido para PDF vía Chrome headless."""
import html
import os
import re
import sys

FUENTE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "REPORTE_EVALUACION_PROACO_INBOUND.md")
SALIDA = "/tmp/reporte_proaco_inbound.html"

CSS = """
body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 10.5pt; color: #1a1a1a; line-height: 1.55; margin: 0; }
h1 { font-size: 19pt; color: #0f4c81; border-bottom: 2.5px solid #0f4c81; padding-bottom: 6px; }
h2 { font-size: 14pt; color: #0f4c81; margin-top: 22px; border-bottom: 1px solid #c9d6e5; padding-bottom: 3px; }
h3 { font-size: 11.5pt; color: #0f4c81; margin-top: 16px; }
h4 { font-size: 10.5pt; color: #333; }
p { margin: 6px 0; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 8.5pt; }
th { background: #0f4c81; color: #fff; text-align: left; padding: 5px 8px; }
td { border: 0.6px solid #b8c6d6; padding: 4px 8px; }
tr:nth-child(even) td { background: #f0f4f9; }
ul, ol { margin: 6px 0; padding-left: 20px; }
li { margin: 3px 0; }
code, pre { font-family: 'Menlo', monospace; font-size: 8.5pt; background: #f2f2f2; }
pre { padding: 8px; border-left: 3px solid #0f4c81; white-space: pre-wrap; }
strong { color: #0f4c81; }
"""


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


def main():
    md = open(FUENTE, encoding="utf-8").read()
    md = tablas(md)
    bloques = re.split(r"```", md)
    out = []
    for i, bloque in enumerate(bloques):
        if i % 2 == 1:
            out.append("<pre>" + html.escape(bloque.strip("\n")) + "</pre>")
            continue
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
    body = "\n\n".join(out)
    html_doc = f"<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"><style>{CSS}</style></head>\n<body>{body}</body></html>"
    open(SALIDA, "w", encoding="utf-8").write(html_doc)
    print(f"HTML escrito en {SALIDA} ({len(html_doc)} bytes)")


if __name__ == "__main__":
    main()
