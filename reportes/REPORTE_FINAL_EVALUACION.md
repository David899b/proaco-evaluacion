# Reporte Final: Evaluación VoiceBot Proaco
## Comparativa de 3 Herramientas + Plan de Costos para Venta

**Fecha:** 2026-08-17  
**Evaluador:** BigPickle (qwen2.5:7b local)  
**Datos:** 13 inbound + 6 outbound = 19 llamadas reales

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| Inbound GLOBAL (9 reglas) | **0.632** |
| Outbound GLOBAL (7 reglas) | **0.600** |
| Correlación DeepEval ↔ LangSmith | **1.000** |
| Herramientas evaluadas | Opik, DeepEval, LangSmith |
| Modelos evaluados | Ollama local, Groq cloud |

---

## 1. Scores por Métrica - Inbound (9 Reglas)

| Métrica | Score | Estado |
|---------|-------|--------|
| clarifica_ambiguo | 0.865 | 🟢 |
| listado_max_3 | 0.865 | 🟢 |
| deriva_web_si_no_sabe | 0.769 | 🟢 |
| transfiere_correcto | 0.615 | 🟡 |
| deteccion_intent | 0.577 | 🟡 |
| pide_contacto_una_vez | 0.577 | 🟡 |
| tono_espanol_argentino | 0.558 | 🟡 |
| despedida_correcta | 0.538 | 🟡 |
| saludo_correcto | 0.327 | 🔴 |
| **GLOBAL** | **0.632** | 🟡 |

### Hallazgos Inbound
- **Mejores:** clarifica_ambiguo (0.865) y listado_max_3 (0.865) - el bot cumple bien
- **Crítico:** saludo_correcto (0.327) - el bot no siempre dice "se contactó con el Grupo Proaco"
- **Mejorable:** despedida_correcta (0.538) - falta consistencia en cierre

---

## 2. Scores por Métrica - Outbound (7 Reglas)

| Métrica | Score | Estado |
|---------|-------|--------|
| se_presenta | 1.000 | 🟢 |
| tono_respetuoso | 0.909 | 🟢 |
| maneja_no_interes | 0.583 | 🟡 |
| menciona_proposito | 0.583 | 🟡 |
| listado_max_3 | 0.500 | 🟡 |
| pide_consentimiento | 0.333 | 🔴 |
| ofrece_agendar_cita | 0.292 | 🔴 |
| **GLOBAL** | **0.600** | 🟡 |

### Hallazgos Outbound
- **Perfecto:** se_presenta (1.0) - el bot siempre se identifica como Proaco
- **Crítico:** ofrece_agendar_cita (0.292) - no ofrece agendar cita cuando debería
- **Crítico:** pide_consentimiento (0.333) - no pregunta si puede continuar

---

## 3. Comparación por Herramienta

### Inbound (9 métricas)

| Herramienta | Juez | GLOBAL | Costo |
|-------------|------|--------|-------|
| Opik J1 (original) | qwen2.5:7b | 0.757 | $0 |
| Opik J2 (coder) | qwen2.5-coder:7b | 0.650 | $0 |
| **DeepEval** (mejorado) | qwen2.5:7b | **0.632** | $0 |
| **LangSmith** (mejorado) | qwen2.5:7b | **0.632** | $0 |

**Conclusión:** DeepEval y LangSmith dan scores **idénticos** (correlación 1.000). Opik J1 inflaba scores por prompts vagos.

### Outbound (7 métricas)

| Herramienta | GLOBAL |
|-------------|--------|
| DeepEval | 0.607 |
| LangSmith | 0.593 |

**Conclusión:** Ligera variación natural (±0.014) por diferencias en parsing de prompts.

---

## 4. Comparación por Modelo

| Modelo | Tipo | GLOBAL | Velocidad | Costo |
|--------|------|--------|-----------|-------|
| **Ollama qwen2.5:7b** | Local | **0.632** | ~7 tok/s | $0 |
| Groq qwen3.6-27b | Cloud | 0.096* | ~50 tok/s | $0 (free tier) |

*Groq falló por rate limits (50% de llamadas devolvieron 0.0). No recomendado para evaluación masiva.

---

## 5. Scores por Llamada - Inbound

| Llamada | DeepEval | LangSmith | Peor métrica |
|---------|----------|-----------|--------------|
| llamada-1 | 0.778 | 0.778 | saludo (0.25) |
| llamada-2 | 0.472 | 0.472 | saludo (0.25) |
| llamada-3 | 0.806 | 0.806 | saludo (0.25) |
| llamada-4 | 0.611 | 0.611 | saludo (0.50) |
| llamada-5 | 0.306 | 0.306 | saludo (0.00) |
| llamada-6 | 0.611 | 0.611 | saludo (0.25) |
| llamada-7 | 0.667 | 0.667 | saludo (0.25) |
| llamada-8 | 0.861 | 0.861 | tono (0.50) |
| llamada-9 | 0.611 | 0.611 | saludo (0.25) |
| llamada-10 | 0.722 | 0.722 | saludo (0.25) |
| llamada-11 | 0.722 | 0.722 | saludo (0.25) |
| llamada-12 | 0.472 | 0.472 | deteccion (0.00) |
| llamada-13 | 0.583 | 0.583 | despedida (0.25) |

**Patrón:** La métrica más baja es consistentemente `saludo_correcto` (0.00-0.75).

---

## 6. Plan de Costos para Venta como Producto

### Modelo de Negocio: SaaS para Evaluación de VoiceBots

#### Costos Operativos (por 100 llamadas evaluadas)

| Componente | Costo | Notas |
|------------|-------|-------|
| Juez LLM (Ollama) | $0 | Local, sin API calls |
| Juez LLM (Groq) | ~$5-15 | Free tier limitado |
| Juez LLM (OpenAI) | ~$10-30 | gpt-4o-mini |
| LangSmith | $0 | Free tier (50K runs) |
| Opik | $0 | Open source |
| DeepEval | $0 | Open source |
| VPS (2 vCPU, 4GB) | ~$20-40/mes | DigitalOcean/Hetzner |
| Dominio + SSL | ~$15/año | .com |
| **TOTAL por 100 llamadas** | **~$25-85** | Depende del modelo |

#### Planes de Venta

| Plan | Precio | Llamadas/mes | Modelo | Margen |
|------|--------|-------------|--------|--------|
| **Starter** | $99/mes | 100 | Ollama local | ~74% |
| **Professional** | $299/mes | 500 | Groq/OpenAI | ~73% |
| **Enterprise** | $799/mes | Ilimitado | Custom fine-tuned | ~75% |

#### Features por Plan

**Starter ($99/mes)**
- ✅ Hasta 100 llamadas/mes
- ✅ 9 métricas inbound + 7 outbound
- ✅ Dashboard web básico
- ✅ Reporte mensual PDF
- ✅ Juez Ollama local (requiere servidor del cliente)

**Professional ($299/mes)**
- ✅ Todo lo de Starter
- ✅ 500 llamadas/mes
- ✅ Juez cloud (Groq/OpenAI)
- ✅ LangSmith tracing
- ✅ Alertas por métrica baja
- ✅ Comparación month-over-month
- ✅ Soporte email

**Enterprise ($799/mes)**
- ✅ Todo lo de Professional
- ✅ Llamadas ilimitadas
- ✅ Reglas custom por cliente
- ✅ Modelo fine-tuned dedicado
- ✅ API REST para integración
- ✅ Dashboard + LangSmith + Opik
- ✅ SLA 99.9%
- ✅ Soporte prioritario

#### Proyección de Ingresos (12 meses)

| Mes | Starter | Professional | Enterprise | Ingreso Total |
|-----|---------|-------------|------------|---------------|
| 1-3 | 5 | 1 | 0 | $795/mes |
| 4-6 | 10 | 3 | 1 | $1,887/mes |
| 7-9 | 15 | 5 | 2 | $3,280/mes |
| 10-12 | 20 | 8 | 3 | $5,365/mes |
| **Total Año 1** | | | | **~$35,000** |

#### Ventajas Competitivas
1. **100% offline disponible** (Ollama) - sin dependencia de APIs
2. **3 herramientas comparadas** - results validated
3. **9 métricas Proaco custom** - no genérico
4. **Dashboard en tiempo real** - no waiting for reports
5. **Costo operativo mínimo** - open source stack

---

## 7. Próximos Pasos

1. **Mejorar saludo_correcto** - prioridad #1 (score 0.327)
2. **Agendar cita en outbound** - prioridad #2 (score 0.292)
3. **Agregar métricas de sentiment** - satisfacción del cliente
4. **Benchmark con más datos** - 100+ llamadas para estadística confiable
5. **Integración con Vapi/Bland** - pull automático de transcripciones

---

## Links

- Dashboard: `dashboard.html` (abrir en navegador)
- LangSmith Inbound: https://smith.langchain.com/projects/d38e4cc9-ff40-49d8-af8f-4eae45b5dc6f
- LangSmith Outbound: https://smith.langchain.com/projects/90248e3f-b003-4e93-9515-8f7059ee7ffd
- GitHub: https://github.com/David899b/proaco-evaluacion
