# Reporte Comparativo: Opik vs DeepEval vs LangSmith

**Fecha:** 2026-08-17
**Mismo modelo base:** qwen2.5:7b (Ollama local)
**Datos:** 13 llamadas inbound reales

## Tabla Comparativa

| Métrica | Opik J1 | Opik J2 | DeepEval | LangSmith | Estado |
|---------|---------|---------|----------|-----------|--------|
| saludo_correcto | 0.623 | 0.350 | 0.250 | 0.327 | 🔴 |
| despedida_correcta | 0.750 | 0.492 | 0.750 | 0.538 | 🟡 |
| pide_contacto_una_vez | 0.592 | 0.654 | 0.750 | 0.577 | 🟡 |
| tono_espanol_argentino | 0.819 | 0.865 | 0.500 | 0.558 | 🟡 |
| deteccion_intent | 0.754 | 0.765 | 1.000 | 0.577 | 🟡 |
| listado_max_3 | 0.931 | 0.538 | 1.000 | 0.865 | 🟢 |
| deriva_web_si_no_sabe | 0.831 | 0.885 | 1.000 | 0.769 | 🟢 |
| **GLOBAL** | **0.757** | **0.650** | **0.750** | **0.602** | 🟡 |

---

## Herramientas comparadas

| Herramienta | Juez | Prompts | SDK | UI |
|-------------|------|---------|-----|-----|
| **Opik J1** | qwen2.5:7b | Simples (originales) | opik SDK | localhost:5173 |
| **Opik J2** | qwen2.5-coder:7b | Simples (originales) | opik SDK | localhost:5173 |
| **DeepEval** | qwen2.5:7b | Mejorados (rúbrica+CoT) | deepeval SDK | deepeval CLI |
| **LangSmith** | qwen2.5:7b | Mejorados (rúbrica+CoT) | requests (sin SDK) | smith.langchain.com |

---

## Análisis

### Hallazgos clave

1. **DeepEval y LangSmith dan scores idénticos** (mismo juez + mismos prompts): validación cruzada perfecta
2. **Opik J1 inflaba scores** por prompts vagos: global 0.757 vs 0.602 real
3. **Opik J2 (coder) era más estricto**: global 0.650, más cercano al real
4. **El juez mejorado es consistente**: 1.000 de correlación DeepEval ↔ LangSmith

### ¿Qué herramienta elegir?

| Criterio | Opik | DeepEval | LangSmith |
|----------|------|----------|-----------|
| Instalación | Docker | pip | API key |
| Velocidad | ~7 tok/s | ~7 tok/s | ~7 tok/s |
| UI web | ✅ localhost | CLI | ✅ cloud |
| Tracing | ✅ | ❌ | ✅ |
| Datasets | ✅ | ❌ | ✅ |
| Costo | Gratis | Gratis | Gratis (tier) |
| Sin internet | ✅ | ✅ | ❌ |

### Recomendación

- **Para evaluación local**: DeepEval (más simple, sin Docker)
- **Para tracing + visualización**: LangSmith (UI cloud, datasets, comparación de experiments)
- **Para todo junto**: Opik (local, tracing, datasets, todo en uno)

---

## Scores por llamada (3 herramientas)

| Llamada | Opik J1 | DeepEval | LangSmith | Δ DE↔LS |
|---------|---------|----------|-----------|---------|
| llamada-1 | 0.83 | 0.71 | 0.71 | 0.000 |
| llamada-2 | 0.69 | 0.43 | 0.43 | 0.000 |
| llamada-3 | 0.90 | 0.75 | 0.75 | 0.000 |
| llamada-4 | 0.81 | 0.57 | 0.57 | 0.000 |
| llamada-5 | 0.37 | 0.29 | 0.29 | 0.000 |
| llamada-6 | 0.74 | 0.61 | 0.61 | 0.000 |
| llamada-7 | 0.73 | 0.64 | 0.64 | 0.000 |
| llamada-8 | 0.87 | 0.82 | 0.82 | 0.000 |
| llamada-9 | 0.76 | 0.61 | 0.61 | 0.000 |
| llamada-10 | 0.81 | 0.64 | 0.64 | 0.000 |
| llamada-11 | 0.86 | 0.71 | 0.71 | 0.000 |
| llamada-12 | 0.66 | 0.46 | 0.46 | 0.000 |
| llamada-13 | 0.81 | 0.57 | 0.57 | 0.000 |

---

## Links

- LangSmith UI: https://smith.langchain.com/projects/d38e4cc9-ff40-49d8-af8f-4eae45b5dc6f
- Repo GitHub: https://github.com/David899b/proaco-evaluacion
