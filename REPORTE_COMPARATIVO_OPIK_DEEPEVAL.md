# Reporte Comparativo: Opik vs DeepEval

**Fecha:** 2026-08-13
**Mismo modelo:** qwen2.5:7b (Ollama local)
**Diferencia:** prompts simples (Opik) vs prompts mejorados con rúbrica + CoT (DeepEval)
**Datos:** 13 llamadas inbound reales

---

## Tabla Comparativa

| Métrica | Opik J1 | Opik J2 | DeepEval | Δ J1→DE | Estado |
|---------|---------|---------|----------|---------|--------|
| saludo_correcto | 0.623 | 0.350 | 0.327 | -0.296 | 🔴 |
| despedida_correcta | 0.750 | 0.492 | 0.538 | -0.212 | 🟡 |
| pide_contacto_una_vez | 0.592 | 0.654 | 0.577 | -0.015 | 🟡 |
| tono_espanol_argentino | 0.819 | 0.865 | 0.558 | -0.262 | 🟡 |
| deteccion_intent | 0.754 | 0.765 | 0.577 | -0.177 | 🟡 |
| listado_max_3 | 0.931 | 0.538 | 0.865 | -0.065 | 🟢 |
| deriva_web_si_no_sabe | 0.831 | 0.885 | 0.769 | -0.062 | 🟢 |
| **GLOBAL** | **0.757** | **0.650** | **0.602** | **-0.155** | 🟡 |

---

## Leyenda
- **Opik J1** = qwen2.5:7b con prompts simples (el juez original)
- **Opik J2** = qwen2.5-coder:7b con prompts simples
- **DeepEval** = qwen2.5:7b con prompts mejorados (rúbrica + CoT + anclas de score 0/0.25/0.5/0.75/1.0)

## Análisis

### ¿Por qué los scores bajaron con DeepEval?

El juez mejorado es **más estricto y más preciso**:

1. **Prompts con rúbrica explícita**: el modelo sabe exactamente qué es 1.0, 0.75, 0.5, 0.25 y 0.0
2. **Chain-of-thought**: el modelo razona paso a paso antes de puntuar
3. **Edge cases**: el modelo considera situaciones límite que antes ignoraba
4. **Ejemplos de cumplimiento parcial**: el modelo distingue mejor entre "casi cumple" y "no cumple"

### Resultados por métrica

- **saludo_correcto (🔴 0.327):** 
  La métrica más baja. El juez mejorado verifica el saludo oficial EXACTO, no "cualquier saludo".
  Oportunidad de mejora clara en el voicebot.

- **listado_max_3 (🟢 0.865):** 
  La métrica más fuerte. El bot cumple bien con listar max 3 propiedades.

- **deriva_web_si_no_sabe (🟢 0.769):** 
  Buena. El bot deriva correctamente cuando no sabe.

- **despedida_correcta (🟡 0.538):** 
  Regular. A veces usa la despedida oficial, a veces una variante.

- **tono_espanol_argentino (🟡 0.558):** 
  Regular. El tono es amable pero no siempre usa expresiones rioplatenses.

---

## Scores por llamada (DeepEval)

| Llamada | avg | saludo | despedida | contacto | tono | intent | listado | web |
|---------|-----|--------|-----------|----------|------|--------|---------|-----|
| llamada-1 | 0.71 | 0.25 | 0.75 | 0.75 | 0.75 | 0.75 | 0.75 | 1.00 |
| llamada-2 | 0.43 | 0.25 | 0.25 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 |
| llamada-3 | 0.75 | 0.25 | 0.75 | 0.75 | 0.50 | 1.00 | 1.00 | 1.00 |
| llamada-4 | 0.57 | 0.50 | 0.75 | 0.50 | 0.50 | 0.50 | 0.50 | 0.75 |
| llamada-5 | 0.29 | 0.00 | 0.25 | 0.00 | 0.25 | 0.00 | 1.00 | 0.50 |
| llamada-6 | 0.61 | 0.25 | 0.25 | 0.25 | 0.75 | 0.75 | 1.00 | 1.00 |
| llamada-7 | 0.64 | 0.25 | 0.75 | 0.75 | 0.50 | 0.50 | 1.00 | 0.75 |
| llamada-8 | 0.82 | 0.75 | 1.00 | 0.75 | 0.50 | 0.75 | 1.00 | 1.00 |
| llamada-9 | 0.61 | 0.25 | 0.75 | 0.50 | 0.75 | 0.75 | 0.75 | 0.50 |
| llamada-10 | 0.64 | 0.25 | 0.25 | 0.75 | 0.50 | 0.75 | 1.00 | 1.00 |
| llamada-11 | 0.71 | 0.25 | 0.75 | 0.75 | 0.50 | 0.75 | 1.00 | 1.00 |
| llamada-12 | 0.46 | 0.25 | 0.25 | 0.75 | 0.50 | 0.00 | 1.00 | 0.50 |
| llamada-13 | 0.57 | 0.75 | 0.25 | 0.50 | 0.75 | 0.50 | 0.75 | 0.50 |

---

## Próximos pasos

1. **Mejorar el saludo oficial** en el voicebot (métrica más crítica)
2. **Mejorar la despedida** para que siempre sea la oficial
3. **Probar con Groq** (tier de pago) para acelerar ~10x y evitar throttle
4. **Agregar métricas Opik genéricas** (Usefulness, AnswerRelevance) con prompts mejorados
5. **Evaluar outbound** cuando hayan llamadas salientes reales
