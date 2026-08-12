# Reporte de Evaluación del Voicebot Grupo Proaco — Inbound + Outbound

**Fecha:** 2026-08-12 · **Flows:** inbound (cliente llama) y outbound (bot llama a leads) · **Juez:** Qwen 2.5 7B / 7B-Coder (Ollama local)

---

## 1. Inbound

Se evaluaron **13 llamadas inbound** con 4 suites: heurísticas deterministas, LLM-judges adicionales y las 7 reglas de Proaco con dos jueces (comparación de consistencia).

### S1 · Heurísticas deterministas

|  | Métrica | Promedio |
|---|---|---|
| ~ | URL de derivación | 0.308 |
| ~ | Saludo presente | 0.308 |
| ⚠ | Despedida presente | 0.846 |
| ⚠ | Sin loop de transferencia | 0.923 |
| ⚠ | Sin datos de AySA | 0.923 |
| ⚠ | Tono respetuoso | 1.000 |
| ⚠ | Adherencia a español | 1.000 |

### S2 · LLM-judges adicionales

|  | Métrica | Promedio |
|---|---|---|
| ⚠ | Moderación | 0.000 |
| ⚠ | Frustración del usuario | 0.094 |
| ✓ | Correctitud de herramientas | 0.300 |
| ~ | Utilidad | 0.323 |
| ~ | Relevancia de respuesta | 0.354 |
| ⚠ | Completitud de tarea | 0.523 |
| ⚠ | Completitud de sesión | 0.603 |
| ⚠ | Coherencia conversacional | 0.639 |

### S3 · Reglas Proaco (juez qwen2.5:7b)

|  | Métrica | Promedio |
|---|---|---|
| ⚠ | Pedido de contacto (una vez) | 0.592 |
| ⚠ | Saludo oficial | 0.623 |
| ⚠ | Despedida oficial | 0.750 |
| ⚠ | Detección de intent | 0.754 |
| ⚠ | Tono español rioplatense | 0.819 |
| ⚠ | Deriva a la web | 0.831 |
| ⚠ | Listado máximo 3 | 0.931 |

### S3 · Reglas Proaco (juez qwen2.5-coder:7b)

|  | Métrica | Promedio |
|---|---|---|
| ~ | Saludo oficial | 0.350 |
| ~ | Despedida oficial | 0.492 |
| ⚠ | Listado máximo 3 | 0.538 |
| ⚠ | Pedido de contacto (una vez) | 0.654 |
| ⚠ | Detección de intent | 0.765 |
| ⚠ | Tono español rioplatense | 0.865 |
| ⚠ | Deriva a la web | 0.885 |

---

## 2. Outbound

Se evaluaron **6 llamadas outbound** (touchpoints de la campaña Grupo Proaco en Lula). Nota: al momento de la evaluación la campaña solo contiene las llamadas de QA inbound; no hay llamadas salientes reales todavía.

### O1 · Reglas outbound (heurísticas)

|  | Métrica | Promedio |
|---|---|---|
| ✓ | Ofrece agendar cita | 0.000 |
| ✓ | Pide consentimiento | 0.000 |
| ✓ | Menciona el motivo | 0.167 |
| ⚠ | Listado máximo 3 | 0.833 |
| ⚠ | Se presenta como Proaco | 1.000 |
| ⚠ | Tono respetuoso | 1.000 |
| ⚠ | Maneja no-interés | 1.000 |

### O2 · Reglas outbound (LLM-judge)

|  | Métrica | Promedio |
|---|---|---|
| ✓ | Agendamiento de cita (LLM) | 0.000 |
| ✓ | Ofrece agendar cita | 0.000 |
| ✓ | Pide consentimiento | 0.000 |
| ✓ | Cliente no interesado (LLM) | 0.133 |
| ✓ | Menciona el motivo | 0.167 |
| ⚠ | Listado máximo 3 | 0.833 |
| ⚠ | Maneja no-interés | 1.000 |
| ⚠ | Tono respetuoso | 1.000 |
| ⚠ | Se presenta como Proaco | 1.000 |

---

## 3. Detalle por llamada

Cada llamada tiene su propia carpeta en `evaluaciones/{flow}/{llamada_id}/` con `scores.json`, `resumen.md` y `transcripcion.txt`.

### Inbound

| Llamada | S1 | S2 | S3 | S3 |
|---|---|---|---|---|
| llamada-1 | 0.71 | 0.40 | 0.83 | 0.83 |
| llamada-10 | 0.71 | 0.49 | 0.81 | 0.79 |
| llamada-11 | 0.71 | 0.32 | 0.86 | 0.46 |
| llamada-12 | 0.57 | 0.22 | 0.66 | 0.60 |
| llamada-13 | 0.86 | 0.34 | 0.81 | 0.99 |
| llamada-2 | 0.57 | 0.42 | 0.69 | 0.48 |
| llamada-3 | 0.71 | 0.34 | 0.90 | 0.93 |
| llamada-4 | 0.86 | 0.48 | 0.81 | 0.59 |
| llamada-5 | 0.71 | 0.30 | 0.37 | 0.34 |
| llamada-6 | 0.86 | 0.29 | 0.74 | 0.51 |
| llamada-7 | 1.00 | 0.30 | 0.73 | 0.39 |
| llamada-8 | 0.86 | 0.28 | 0.87 | 0.93 |
| llamada-9 | 0.71 | 0.43 | 0.76 | 0.63 |

### Outbound

| Llamada | O1 | O2 |
|---|---|---|
| CA18a4abd08a | 0.57 | 0.44 |
| CA19ee8401e8 | 0.71 | 0.64 |
| CA1cc4b3a43b | 0.57 | 0.44 |
| CAc57514332e | 0.57 | 0.44 |
| CAd7af8dc9b3 | 0.43 | 0.33 |
| CAf8fa6d0fc1 | 0.57 | 0.44 |

---

## 4. Hallazgos

**Métricas con promedio bajo (< 0.60):**

| Métrica | Promedio | Suite |
|---|---|---|
| inbound/pide_contacto_una_vez | 0.592 | Reglas Proaco (juez qwen2.5:7b) |
| outbound/ofrece_agendar_cita | 0.000 | O1 · Reglas outbound (heurísticas) |
| outbound/pide_consentimiento | 0.000 | O1 · Reglas outbound (heurísticas) |
| outbound/menciona_proposito | 0.167 | O1 · Reglas outbound (heurísticas) |
| outbound/agendamiento_cita | 0.000 | O2 · Reglas outbound (LLM-judge) |
| outbound/ofrece_agendar_cita | 0.000 | O2 · Reglas outbound (LLM-judge) |
| outbound/pide_consentimiento | 0.000 | O2 · Reglas outbound (LLM-judge) |
| outbound/cliente_no_interesado | 0.133 | O2 · Reglas outbound (LLM-judge) |
| outbound/menciona_proposito | 0.167 | O2 · Reglas outbound (LLM-judge) |

### Recomendaciones

- **Inbound saludo/deriva:** reforzar el saludo oficial al inicio y la derivación a la web cuando el bot no puede resolver.
- **Inbound despedida/pedido de contacto:** asegurar despedida oficial y pedido de datos una sola vez al cierre.
- **Outbound:** validar las reglas con llamadas salientes reales (la campaña todavía no tiene). Se espera `pide_consentimiento` bajo si el flow no lo implementa.
