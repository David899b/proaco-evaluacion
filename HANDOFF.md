# HANDOFF — Evaluación Voicebot Proaco (Inbound + Outbound)

**Fecha:** 2026-08-13 (última actualización: reestructura + DeepEval)
**Proyecto:** `proaco-evaluacion/`
**Git:** repo en https://github.com/David899b/proaco-evaluacion.git

---

## Qué se hizo

| Flow | Llamadas | Suites | Juez |
|------|----------|--------|------|
| Inbound (Opik) | 13 | 4 (heurísticas, LLM-judges, 7-reglas juez1, 7-reglas juez2) | qwen2.5:7b / qwen2.5-coder:7b (Ollama local) |
| Inbound (DeepEval) | 13 | 1 (7 reglas Proaco, prompts mejorados) | qwen2.5:7b (Ollama) o Groq (cloud) |
| Outbound | 6* | 2 (heurísticas, LLM-judges GEval) | qwen2.5:7b |

\* *Los 6 touchpoints outbound de la campaña "Grupo Proaco" en Lula son en realidad las mismas llamadas inbound de QA; **no hay llamadas salientes reales todavía**.*

---

## Estructura del repo

```
proaco-evaluacion/
├── opik/                          # Código evaluación con Opik
│   ├── inbound/
│   │   ├── evaluar.py             # evaluador principal
│   │   ├── pruebas_ampliadas.py   # 3 suites (heurísticas, LLM-judges, 7 reglas)
│   │   ├── metricas_proaco.py     # juez LLM Opik (prompts simples)
│   │   └── transcripciones/       # llamadas_reales.json
│   ├── outbound/
│   │   ├── evaluar_outbound.py
│   │   ├── exportar_outbound.py
│   │   ├── metricas_proaco_outbound.py
│   │   └── transcripciones/
│   └── correr_todas.py            # orquestador Opik
├── langsmith/                     # Código evaluación con LangSmith
│   └── inbound/
│       └── evaluar.py             # juez mejorado + logging a LangSmith API
│   └── inbound/
│       └── deepeval_eval.py       # juez mejorado (rúbrica + CoT + anclas)
├── shared/                        # Código compartido
│   └── juez_mejorado.py           # prompts mejorados (reutilizable)
├── evaluaciones/                  # Output de evaluaciones
│   ├── inbound/                   # scores Opik por llamada
│   ├── outbound/                  # scores Opik outbound
│   ├── deepeval/                  # scores DeepEval por llamada
│   └── resultados_completos.json  # agregado
├── scripts/                       # Utilidades
│   ├── generar_docx.py
│   ├── generar_pdf_*.py
│   ├── generar_reporte.py
│   └── organizar_evaluaciones.py
└── reportes/                      # Reportes finales
    ├── REPORTE_COMPARATIVO_OPIK_DEEPEVAL.md
    ├── REPORTE_EVALUACION_PROACO.docx
    └── REPORTE_EVALUACION_PROACO_COMPLETO.pdf
```

---

## Comandos útiles

```bash
cd /Users/david899/Documents/Default\ Project/proaco-evaluacion

# ── Opik ──────────────────────────────────────────────
# Correr todas las suites (lento: ~1.5h en Ollama)
python opik/correr_todas.py

# Solo inbound
python opik/correr_todas.py --solo inbound

# Solo outbound
python opik/correr_todas.py --solo outbound

# ── DeepEval ──────────────────────────────────────────
# Ollama local (sin API key, ~45min)
python deepeval/inbound/deepeval_eval.py

# Groq cloud (requiere API key, ~5min)
export GROQ_API_KEY="gsk_..."
python deepeval/inbound/deepeval_eval.py --modelo groq/qwen/qwen3.6-27b

# Solo una llamada
python deepeval/inbound/deepeval_eval.py --solo llamada-1

# ── Reportes ──────────────────────────────────────────
# Generar DOCX
python scripts/generar_docx.py

# Generar PDF completo
python scripts/generar_pdf_completo.py

# ── LangSmith ─────────────────────────────────────────
# Evaluar + logear a LangSmith (sin SDK, solo requests)
export LANGCHAIN_API_KEY="lsv2_..."
python langsmith/inbound/evaluar.py

# Groq cloud
export GROQ_API_KEY="gsk_..."
python langsmith/inbound/evaluar.py --modelo groq/qwen/qwen3.6-27b

# Solo una llamada
python langsmith/inbound/evaluar.py --solo llamada-1

# Ver en LangSmith UI
open https://smith.langchain.com
```

---

## Hallazgos principales

**Inbound DeepEval (juez mejorado, qwen2.5:7b):**
- 🔴 saludo_correcto: 0.327 (el bot NO usa el saludo oficial exacto)
- 🟡 despedida_correcta: 0.538
- 🟡 tono_espanol_argentino: 0.558
- 🟡 deteccion_intent: 0.577
- 🟡 pide_contacto_una_vez: 0.577
- 🟢 deriva_web_si_no_sabe: 0.769
- 🟢 listado_max_3: 0.865

**Comparación Opik vs DeepEval:**
- Opik J1 (prompts simples): global 0.757 (inflado)
- DeepEval (prompts mejorados): global 0.602 (más realista)
- El juez mejorado es más estricto y preciso

---

## API keys

- **Groq:** `export GROQ_API_KEY="gsk_..."` (gratis en console.groq.com/keys, tier free 8000 TPM)
- **Ollama:** sin key, solo `ollama serve`

---

## Configuración de entorno

- **Ollama:** `qwen2.5:7b`, `qwen2.5-coder:7b` (throttle ~7 tok/s en MacBook Air M4 16GB)
- **Opik local:** Docker en `localhost:5173`
- **Lula API:** `https://api.lula.com` + header `X-API-Key` (export `LULA_API_KEY`)
- **Python venv:** `.venv/` en la raíz del proyecto
- **DeepEval:** `pip install deepeval` (ya instalado)

---

## Para retomar en nueva sesión

```bash
cd /Users/david899/Documents/Default\ Project/proaco-evaluacion
cat HANDOFF.md
cat evaluaciones/deepeval/resultados_deep.json | python3 -m json.tool | head -30
```
