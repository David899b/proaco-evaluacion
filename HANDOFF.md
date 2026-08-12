# HANDOFF — Evaluación Voicebot Proaco (Inbound + Outbound)

**Fecha:** 2026-08-12  
**Proyecto:** `proaco-evaluacion/`  
**Git:** inicializado (commit `cfedb5a`)

---

## Qué se hizo

| Flow | Llamadas | Suites | Juez |
|------|----------|--------|------|
| Inbound | 13 | 4 (heurísticas, LLM-judges, 7-reglas juez1, 7-reglas juez2) | qwen2.5:7b / qwen2.5-coder:7b (Ollama local) |
| Outbound | 6* | 2 (heurísticas, LLM-judges GEval) | qwen2.5:7b |

\* *Los 6 touchpoints outbound de la campaña "Grupo Proaco" en Lula son en realidad las mismas llamadas inbound de QA; **no hay llamadas salientes reales todavía**.*

---

## Estructura clave

```
proaco-evaluacion/
├── evaluaciones/
│   ├── inbound/llamada-{1..13}/    # 13 carpetas, cada una con scores.json, resumen.md, transcripcion.txt
│   ├── outbound/CA.../             # 6 carpetas (IDs de Lula)
│   └── resultados_completos.json   # agregado de todas las suites
├── REPORTE_EVALUACION_PROACO.md    # reporte consolidado (inbound + outbound)
├── REPORTE_EVALUACION_PROACO_INBOUND.md  # reporte inbound legacy
├── correr_todas.py                 # orquestador que corre todas las suites
├── organizar_evaluaciones.py       # baja scores de Opik y arma carpetas por caso
├── generar_reporte.py              # genera el reporte MD/HTML desde resultados_completos.json
├── proaco/inbound/                 # código inbound (evaluar.py, pruebas_ampliadas.py, métricas)
└── proaco/outbound/                # código outbound (evaluar_outbound.py, exportar_outbound.py, métricas)
```

---

## Comandos útiles

```bash
cd /Users/david899/Documents/Default\ Project/proaco-evaluacion

# Ver reporte
cat REPORTE_EVALUACION_PROACO.md

# Volver a armar carpetas + reporte (lee de Opik)
python organizar_evaluaciones.py
python generar_reporte.py

# Correr TODAS las suites de nuevo (lento: ~1.5h en Ollama)
python correr_todas.py

# Solo outbound LLM (GEval)
cd proaco/outbound
python -c "
from evaluar_outbound import cargar_items
items = cargar_items('transcripciones/llamadas_outbound.json')
import evaluar_outbound as eo
r = eo.run_evaluacion(items, llm=True, juez_modelo='qwen2.5:7b', threads=1)
"

# Exportar touchpoints frescos de Lula (requiere LULA_API_KEY)
export LULA_API_KEY="api-..."
python proaco/outbound/exportar_outbound.py

# Opik UI
open http://localhost:5173
# Proyectos: voicebot-proaco-inbound, voicebot-proaco-outbound
```

---

## Hallazgos principales (del reporte)

**Inbound (juez qwen2.5:7b):**
- ✅ Fuerte: listado máx 3 (0.93), tono (0.82), deriva web (0.83)
- ⚠ Débil: saludo oficial (0.62), pedido de contacto (0.59)

**Inbound (juez qwen2.5-coder:7b) — más estricto:**
- ⚠ Saludo 0.35, despedida 0.49, listado máx 3 0.54

**Outbound:**
- Todas las métricas de flow saliente en **0.00** (menciona_proposito, pide_consentimiento, ofrece_agendar_cita, GEval) porque **no hay llamadas outbound reales** en la campaña Lula — solo touchpoints de QA inbound.

---

## Próximos pasos sugeridos

1. **Esperar llamadas outbound reales** en la campaña "Grupo Proaco" (Lula) → volver a correr `exportar_outbound.py` + `correr_todas.py --solo outbound`.
2. **Probar juez cloud** (Groq `llama-3.3-70b-versatile` gratis, o OpenAI `gpt-4o-mini`) para acelerar y evitar throttle térmico.
3. **Refinar heurística `maneja_no_interes`** (falso positivo por "gracias" en saludo).

---

## Configuración de entorno

- **Ollama:** `qwen2.5:7b`, `qwen2.5-coder:7b` (throttle ~7 tok/s en MacBook Air M4 16GB)
- **Opik local:** Docker en `localhost:5173`
- **Lula API:** `https://api.lula.com` + header `X-API-Key` (export `LULA_API_KEY`)
- **Python venv:** `.venv/` en la raíz del proyecto

---

## Para retomar en nueva sesión

```bash
cd /Users/david899/Documents/Default\ Project/proaco-evaluacion
cat REPORTE_EVALUACION_PROACO.md
cat evaluaciones/resultados_completos.json | head -50
```