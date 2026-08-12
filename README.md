# Evaluación de voicebots — organización por proyecto y flow

Cada **proyecto** (cliente) y cada **flow** se evalúa por separado. Nunca se mezclan
datos ni reglas entre proyectos.

```
proaco-evaluacion/
├── README.md                        ← este archivo
└── proaco/
    ├── inbound/                     ← PROACO RECIBIDAS (cliente llama al bot)
    │   ├── transcripciones/llamadas_reales.json   (13 llamadas, metadata proyecto/flow)
    │   ├── metricas_proaco.py        reglas de negocio inbound (7 LLM-judges)
    │   ├── evaluar.py                baseline de las 7 reglas (modo nube incluido)
    │   ├── pruebas_ampliadas.py      3 suites (heurísticas + LLM-judges + comparación)
    │   ├── convertir_csv.py          CSV de Google Sheets → JSON
    │   ├── descargar_resultados.py   scores por llamada → resultados_suites.json
    │   ├── md_a_html.py + Chrome     markdown → PDF
    │   └── REPORTE_EVALUACION_PROACO_INBOUND.md / .pdf
    └── outbound/                     ← PROACO SALIENTES (bot llama al lead) [DRAFT]
        ├── metricas_proaco_outbound.py
        └── README.md
```

(Otros proyectos — p. ej. AySA — se agregan como carpetas hermanas cuando existan
datos; no se mezclan con Proaco.)

## Convención (obligatoria)

| Ámbito         | Proyecto Opik              | Datasets                         | Experimentos              |
|----------------|----------------------------|----------------------------------|---------------------------|
| Proaco inbound | `voicebot-proaco-inbound`  | `transcripciones-proaco-inbound-*` | prefijo `proaco-inbound-` |
| Proaco outbound| `voicebot-proaco-outbound` | `transcripciones-proaco-outbound-*`| prefijo `proaco-outbound-` |

Cada transcripción lleva en `metadata` los campos `proyecto` y `flow`
(p. ej. `{"proyecto": "proaco", "flow": "inbound"}`).

## Regla de oro

- Un juez se fija como baseline **dentro de cada proyecto/flow** y no se cambia
  entre corridas (cada modelo puntúa distinto).
- No se reutilizan reglas entre proyectos (saludo/despedida/contacto/URL de Proaco
  no aplican a AySA, y viceversa).
