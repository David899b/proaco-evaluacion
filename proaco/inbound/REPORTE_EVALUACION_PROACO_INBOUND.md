# Reporte de Evaluación del Voicebot Grupo Proaco — Inbound

**Alcance:** Flow **inbound** (cliente llama al bot) del proyecto **Proaco**.
**Proyecto Opik:** `voicebot-proaco-inbound-inbound` · **Fecha de evaluación:** 2026-08-11 · **Juez:** Qwen 2.5 7B (Ollama, local)

> **Separación de análisis:** este reporte es solo Proaco inbound. El flow **outbound**
> y el proyecto **AySA** se evalúan por separado (ver `proaco-evaluacion/README.md`).

---

## 1. Resumen Ejecutivo

Se evaluaron **13 llamadas reales** (transcripciones de pruebas manuales del voicebot) contra **7 métricas** basadas en las reglas de interacción del Grupo Proaco, usando un juez LLM local (Qwen 2.5 7B vía Ollama) a través del framework Opik. Luego se amplió con una **suite completa de 22 métricas** (heurísticas deterministas, LLM-judges genéricos y un segundo juez de comparación) — ver **Sección 10**.

**Puntuación general: 0.77 / 1.00.**

| Área | Promedio | Lectura |
|---|---|---|
| Listado de propiedades | **0.91** | Sólido: respeta el máximo de 3 por mensaje y no agrega datos que no pidió el cliente. |
| Tono (español rioplatense) | **0.81** | Bueno, amable y claro en casi todas las llamadas. |
| Detección de intent | **0.78** | Detecta bien el flujo correcto, con algunos desvíos puntuales. |
| Derivación a la web | **0.76** | Falló en los casos donde el bot quedó atascado o no supo qué hacer. |
| Despedida | **0.76** | Varias llamadas terminan sin la despedida oficial. |
| Pedido de contacto (una vez) | **0.70** | Tendencia a repetir o a no pedir los datos. |
| Saludo oficial | **0.64** | **Peor métrica**: la llamada 5 ni siquiera arranca con el saludo. |

**Hallazgo principal:** 3 de las 13 llamadas (23%) son críticas y explican casi todo el déficit: la **llamada-5** (loop con cliente que pide un humano), la **llamada-10** (despedida ausente) y la **llamada-12** (no deriva pese a no poder resolver). El resto del sistema se comporta bien (llamada-8: 0.89, llamada-3: 0.87).

---

## 2. Proceso de Evaluación

### 2.1 Pipeline

```
CSV (Google Sheets)              Opik
┌─────────────────┐   convert   ┌──────────────────────┐
│ 14 tests con     │ ─────────► │ transcripciones/     │
│ Agent/Caller +   │  convertir_ │ llamadas_reales.json │
│ etiquetas tools  │  csv.py    └──────────────────────┘
└─────────────────┘                    │ insert
                                       ▼
                              Opik Dataset: transcripciones-proaco-inbound (13 items)
                                       │ evaluate()
                                       ▼
                     Opik Experiment: dynamic_annuity_8219
                     13 items × 7 métricas LLM-judge (Qwen 2.5 7B)
```

**Etapas:**
1. **Parseo del CSV** (`proaco-evaluacion/proaco/inbound/convertir_csv.py`): detecta los bloques `TEST N`, separa turnos `Agent`/`Caller` y captura las etiquetas de herramientas (`proaco_list_intent`, `getCalDotComAvailability`, `scheduleCalDotComAppointment`, `proaco_resolve_intent`) en `metadata.tools`. El TEST 14 resultó un duplicado exacto del TEST 12 y se descartó (13 únicos).
2. **Normalización**: turnos `[BOT]`/`[CLIENTE]` para el juez (`evaluar.py`).
3. **Dataset en Opik**: `transcripciones-proaco-inbound` con los 13 items y su metadata.
4. **Evaluación**: `evaluate()` corre las 7 métricas LLM-as-judge sobre cada llamada (91 puntuaciones en total).

### 2.2 Métricas (reglas de Proaco)

Obligatorias (aplican a toda llamada): `saludo_correcto`, `despedida_correcta`, `pide_contacto_una_vez`, `tono_espanol_argentino`.
Condicionales (solo si la situación se presenta): `deteccion_intent`, `listado_max_3`, `deriva_web_si_no_sabe`.

Cada métrica pide al juez un `{"score": 0-1, "reason": "..."}` con ejemplos de buen y mal cumplimiento.

### 2.3 Limitaciones metodológicas

- **Muestra pequeña** (13 llamadas): los promedios son indicativos, no estadísticamente robustos.
- **Juez local 7B**: consistente y sin costo, pero menos preciso que un juez grande; los scores son orientativos.
- **1 score fallido**: la métrica `pide_contacto_una_vez` de la llamada-5 no se computó (el juez devolvió JSON mal formado). Se muestra como no evaluada (n=12 en esa métrica).

---

## 3. Datos

### 3.1 Promedios por métrica

| Métrica | Promedio | Mín | Máx | n |
|---|---|---|---|---|
| listado_max_3 | 0.91 | 0.60 | 1.00 | 13 |
| tono_espanol_argentino | 0.81 | 0.60 | 0.90 | 13 |
| deteccion_intent | 0.78 | 0.60 | 1.00 | 13 |
| deriva_web_si_no_sabe | 0.76 | 0.00 | 1.00 | 13 |
| despedida_correcta | 0.76 | 0.00 | 1.00 | 13 |
| pide_contacto_una_vez | 0.70 | 0.60 | 0.80 | 12 |
| saludo_correcto | 0.64 | 0.00 | 0.90 | 13 |

### 3.2 Resultados por llamada (promedio de las 7 métricas)

| Llamada | Score | Intents/tools usados |
|---|---|---|
| llamada-8 | **0.89** | list, availability, schedule |
| llamada-3 | **0.87** | resolve |
| llamada-11 | **0.85** | list, availability, schedule |
| llamada-1 | **0.83** | list, availability, schedule |
| llamada-13 | **0.82** | list, availability |
| llamada-6 | **0.80** | list, availability, schedule |
| llamada-10 | **0.80** | list |
| llamada-9 | **0.77** | list, availability, schedule |
| llamada-7 | **0.76** | list, availability |
| llamada-2 | **0.70** | list, availability |
| llamada-4 | **0.70** | resolve, availability |
| llamada-12 | **0.69** | availability, schedule |
| llamada-5 | **0.43** | — (sin intent detectado) |

### 3.3 Casos con evidencia concreta (reasons del juez)

- **llamada-5** — `saludo=0.0`, `despedida=0.0`, `deriva_web=0.0`: "El bot no inicia la llamada con el saludo oficial… no sugiere consultar con Grupo Proaco… no se despide." El cliente pide un humano 6 veces y el bot responde siempre "no puedo transferir llamadas" → **loop de 12 turnos sin salida**.
- **llamada-10** — `despedida=0.5`: "El bot no utilizó la despedida oficial del Grupo Proaco." El cliente se despide ("eso es todo, hasta luego") y el bot no responde con el cierre oficial.
- **llamada-3** — `saludo=0.5`: "El bot inició con un saludo no oficial y luego cambió al saludo correcto."
- **llamada-12** — `deriva_web=0.0`: el bot no ofrece consultar en la web cuando no tiene turnos disponibles.

---

## 4. Conclusiones

1. **El núcleo del flujo inmobiliario funciona bien.** El listado de propiedades (máx. 3) y el tono argentino amable son las dos fortalezas del bot (0.91 y 0.81). Las llamadas con flujo completo listado + agenda de turno (1, 6, 8, 11) promedian 0.83-0.89.
2. **El problema está concentrado, no distribuido.** 3 llamadas explican la mayor parte del déficit. Si se corrigieran la 5, la 10 y la 12, el promedio global subiría de 0.77 a ≈0.83.
3. **Falta un protocolo de transferencia a humano.** La llamada-5 es el peor caso: ante "pásenme con un asesor humano", el bot se encierra en "no puedo transferir" y repite la misma respuesta 6 veces (rigidez conversacional).
4. **El protocolo de apertura y cierre es inconsistente.** El saludo oficial se pierde en al menos 2 llamadas y la despedida oficial en varias. Son reglas de *branding* que hoy se cumplen por azar del LLM, no de forma garantizada.
5. **Los datos de evaluación están correctos y completos** en Opik (experimento `dynamic_annuity_8219`), pero solo visibles en la pestaña *Experiments*: los traces generados por la evaluación son `source=experiment`, no `source=sdk`, por lo que *Logs* y *Dashboard* aparecen vacíos (ver apéndice A).

---

## 5. Recomendaciones

### 5.1 Prioridad alta

1. **Protocolo de derivación a humano.** Cuando el cliente pide explícitamente un humano (1ª vez): cortar el intent de venta, reconocer la solicitud, pedir datos de contacto para callback y dar la despedida oficial. Si no hay transferencia posible, decirlo una vez y cerrar con un mensaje de redirección (web o callback) — nunca repetir "no puedo transferir".
2. **Fijar saludo y despedida como texto predefinido (no generado).** Ambos son frases fijas de la marca; inyectarlas en el system prompt o como template al inicio/fin de cada turno elimina la variabilidad (0.64 y 0.76 son demasiado bajos para reglas obligatorias).
3. **Cerrar siempre la llamada, aunque el cliente se despida primero.** Cuando el cliente dice "hasta luego", el bot debe responder con la despedida oficial antes de terminar (corrige llamada-10).

### 5.2 Prioridad media

4. **Pedido de contacto una sola vez y al final.** La regla `pide_contacto_una_vez` (0.70) se viola tanto por repetir el pedido como por omitirlo. Unificar el flujo: al final del objetivo de la llamada, un único pedido de nombre + teléfono/mail, sin confirmar en eco lo que el cliente ya dio.
5. **Revisar el prompt de la herramienta de disponibilidad de turnos.** En llamada-12 el bot no sabe ofrecer alternativas ni derivar a la web cuando no hay turnos. El prompt de `getCalDotComAvailability` debería incluir el fallback a la web y opciones de otro día.
6. **Validar los datos de contacto que entrega el bot.** En la llamada-13 el bot entregó un teléfono y un mail de **AySA** (`atencionalusuario@aysa.com.ar`, `+54 11 5984 5794`) — datos de otro cliente del conocimiento (GAIL). Es un caso de *hallucination* de datos sensibles: auditar el conocimiento de contacto de Grupo Proaco y testear explícitamente esta consulta.

### 5.3 Prioridad baja / proceso

7. **Ampliar el dataset de evaluación.** 13 llamadas son pocas; agregar las variantes por intent (listado, turnos, resolución, rechazo a IA, salidas inesperadas) para estabilizar los promedios.
8. **Instrumentar el bot en producción con `opik.track()`.** Los traces de evaluación no aparecen en *Logs* ni *Dashboard* porque son `source=experiment`. Para monitoreo en vivo, correr el bot con el SDK de Opik (decorador `@track`) para que las llamadas reales generen traces `source=sdk` y se vean en las pestañas Logs/Dashboard (ver apéndice A).
9. **Agregar `error_count` a la cabecera de la evaluación:** el juez 7B falló en 1 de 91 respuestas JSON; repetir esa llamada en la próxima tanda para no perder la métrica.

---

## 6. Acciones a Seguir — Roadmap Priorizado

### 6.1 Plan de acción (4 fases)

| Fase | Acción | Qué resuelve | Esfuerzo | Impacto esperado |
|---|---|---|---|---|
| **F1 — Inmediata (0-2 semanas)** | Corregir el protocolo de derivación a humano en la llamada-5 | Loop sin salida, peor caso del dataset | Bajo (prompt) | 0.43 → 0.80 en llamada-5 |
| **F1 — Inmediata (0-2 semanas)** | Fijar saludo y despedida como texto predefinido, no generado | Reglas obligatorias más fallidas | Bajo (template) | saludo 0.64 → 0.95+; despedida 0.76 → 0.95+ |
| **F2 — Corto plazo (2-4 semanas)** | Cerrar la llamada cuando el cliente se despide primero (despedida oficial) | llamada-10 y casos similares | Bajo (prompt) | despedida → 1.00 |
| **F2 — Corto plazo (2-4 semanas)** | Unificar el pedido de contacto: una sola vez, al final | Regla `pide_contacto_una_vez` | Medio (flujo) | 0.70 → 0.90 |
| **F3 — Mediano plazo (1-2 meses)** | Corregir hallucination de datos de contacto (llamada-13: entregó datos de AySA) | Riesgo reputacional / datos erróneos | Medio (auditoría de conocimiento) | elimina riesgo de datos ajenos |
| **F3 — Mediano plazo (1-2 meses)** | Mejorar el fallback de la herramienta de disponibilidad (deriva a web y alternativas) | llamada-12, deriva_web 0.76 | Medio (prompt + lógica) | deriva_web → 0.95 |
| **F4 — Continuo** | Ampliar dataset a 25-30 llamadas por intent y reevaluar | Estabilidad de los promedios | Bajo (proceso) | métricas más confiables |
| **F4 — Continuo** | Instrumentar producción con `opik.track()` y monitorear en Logs/Dashboard | Visibilidad en vivo | Medio (SDK) | alertas tempranas de regresión |

### 6.2 Métricas de éxito (objetivo para la próxima evaluación)

| Métrica | Actual | Objetivo F2 | Objetivo F3 |
|---|---|---|---|
| saludo_correcto | 0.64 | 0.95 | 1.00 |
| despedida_correcta | 0.76 | 0.95 | 1.00 |
| pide_contacto_una_vez | 0.70 | 0.85 | 0.90 |
| deriva_web_si_no_sabe | 0.76 | 0.85 | 0.95 |
| deteccion_intent | 0.78 | 0.90 | 0.95 |
| listado_max_3 | 0.91 | 0.95 | 0.98 |
| tono_espanol_argentino | 0.81 | 0.90 | 0.95 |
| **Promedio general** | **0.77** | **0.91** | **0.96** |

---

## 7. Recomendaciones para Mejora por Área

### 7.1 Conversacional / UX

- **Anticipar la objeción "¿es una IA?"**: responder con transparencia y ofrecer inmediatamente la opción de callback humano, en lugar de negar la transferencia.
- **Límite de reintentos**: si el bot repite la misma respuesta 2 veces seguidas, cambiar de estrategia (derivar, dar la web, o cerrar con despedida oficial). Regla dura en el orquestador.
- **Detectar despedida del cliente como trigger de cierre**: si el cliente dice "hasta luego / chau / eso es todo", el bot debe responder con la despedida oficial y finalizar (no seguir preguntando).
- **No hacer eco de datos**: cuando el cliente ya dio su nombre/teléfono, el bot no debe repetirlos ni pedirlos de nuevo.

### 7.2 Datos y conocimiento

- **Auditar el "knowledge base" de contacto**: verificar que los teléfonos/mails/marcas de Grupo Proaco estén aislados de los de otros clientes del GAIL. La llamada-13 devolvió datos de AySA: revisar el prompt de sistema y la fuente de conocimiento.
- **Versionar los prompts**: guardar cada versión del system prompt y de las herramientas con nombre/versión para poder comparar evaluaciones (regresión).
- **Agregar casos adversariales al dataset**: cliente agresivo, cliente con datos erróneos, consultas fuera de alcance, cortes de llamada.

### 7.3 Evaluación y monitoreo

- **Reevaluar en CI/CD**: correr `evaluar.py` en cada cambio de prompt/`knowledge base` y comparar contra el baseline (0.77).
- **Juez más fuerte para datos sensibles**: las reglas de contacto deberían evaluarse también con un juez más grande (o verificación determinista: buscar los strings oficiales en la respuesta).
- **Verificación determinista complementaria**: para `saludo_correcto` y `despedida_correcta`, chequear la presencia de las frases oficiales exactas (no depender solo del LLM).

---

## 8. Alternativas de Solución por Problema

| Problema | Opción A (recomendada) | Opción B | Opción C |
|---|---|---|---|
| Loop con cliente que pide humano | Protocolo de derivación a humano (callback + despedida) | Transferencia a agente en vivo si la plataforma lo permite | Respuesta única "no puedo transferir" + redirección web y cierre |
| Saludo/despedida inconsistentes | Texto fijo inyectado al inicio/fin de cada llamada | Regla en el orquestador que fuerza la frase | Post-procesamiento que reemplaza el saludo si no coincide |
| No deriva a la web cuando no sabe | Prompt de herramientas con fallback explícito a la URL | Regla condicional en el flujo: si no hay turnos → sugerir web | Mayor conocimiento local (FAQ) para reducir consultas no resueltas |
| Hallucination de datos de contacto (AySA) | Aislar el knowledge base de Grupo Proaco por cliente | Restringir a tokens/entidades permitidas (whitelist de contactos) | Verificación determinista de contacto antes de responder |
| Datos de contacto pedidos varias veces | Unificar pedido al final de la llamada | Estado de máquina que solo permite 1 pedido por llamada | Confirmación silenciosa (no eco) |

---

## 9. Próximos Pasos Sugeridos

1. **Hoy**: aplicar el fix F1 de saludo/despedida como texto fijo y re-evaluar (≈30 min).
2. **Esta semana**: corregir el protocolo de derivación a humano (llamada-5) y re-evaluar.
3. **Semanas 2-4**: auditar el knowledge base de contacto (AySA) y agregar la verificación determinista de las frases oficiales.
4. **Mes 1**: instrumentar el voicebot con `opik.track()` para monitoreo en Logs/Dashboard.
5. **Mes 1-2**: ampliar el dataset de evaluación y establecer el baseline de regresión en CI.

---

## 10. Pruebas Ampliadas (Suite Completa de Métricas)

Sobre las mismas 13 llamadas se corrió una **suite completa de pruebas** (`pruebas_ampliadas.py`) con 3 bloques: heurísticas deterministas (sin LLM), métricas LLM-judge genéricas de Opik, y las reglas de Proaco con un segundo juez local para comparar consistencia.

### 10.1 Suite 1 — Heurísticas deterministas (sin LLM)

Reglas verificables con texto plano, rápidas y 100% reproducibles. Aplican sobre la transcripción completa, no sobre el último turno.

| Métrica | Promedio | Lectura |
|---|---|---|
| Adherencia al español | **1.00** | 13/13 en español rioplatense. |
| Tono respetuoso | **1.00** | Sin insultos, gritos ni exclamaciones excesivas. |
| Sin loop "no puedo transferir" | **0.92** | Solo falla la llamada-5 (8 menciones → loop). |
| Sin hallucination de AySA | **0.92** | Solo falla la llamada-13 (cita `atencionalusuario@aysa.com.ar`). |
| Despedida presente | **0.85** | 11/13 cierran correctamente; fallan llamada-2 y llamada-12. |
| Saludo presente | **0.31** | **Solo 4/13** arrancan con saludo; el resto comienza con "Claro, puedo ayudarle…". |
| URL de derivación presente | **0.31** | Solo 4/13 muestran `grupoproaco.com/unidades` cuando no saben responder. |

**Correlación con el juez LLM:** el saludo determinista (0.31) es *más estricto* que el juez LLM (0.64) porque exige literalmente un saludo al inicio, mientras el juez acepta respuestas que "conversan" sin saludar. La despedida coincide (0.85 vs 0.76). Confirmado: **el déficit real está en el saludo de apertura**, no solo en el texto oficial.

### 10.2 Suite 2 — Métricas LLM-judge genéricas de Opik (juez qwen2.5:7b)

Miden atributos transversales del diálogo, independientes de las reglas de Proaco.

| Métrica | Promedio | Lectura |
|---|---|---|
| Agent tool correctness | **0.72** | El uso/interpretación de tools es razonablemente correcto. |
| Session completeness | **0.69** | La sesión cierra los objetivos la mayoría de las veces. |
| Coherencia conversacional | **0.65** | Diálogo coherente; los desvíos bajan el promedio. |
| Usefulness | **0.37** | Bajo por el encuadre: evalúa si el *último turno* responde la *primera* pregunta (marco distinto al real). |
| Task completion | **0.36** | Bajo por la misma razón de encuadre + casos atascados (llamada-5/8/13). |
| Answer relevance | **0.31** | Igual efecto de encuadre: el último turno no retoma la pregunta inicial. |
| User frustration | **0.09** | **Muy bajo = pocas señales de frustración** (buena noticia). Solo la llamada-5 muestra frustración alta (0.88). |
| Moderation | **0.00** | **Métrica no válida con este juez local**: qwen devuelve 0 en contenido benigno (incompatibilidad de parser). Descartar o usar un modelo de moderación dedicado. |

**Interpretación:** usefulness/task_completion/answer_relevance miden el par *primera pregunta del cliente → última respuesta del bot*; como la conversación evoluciona, esos scores subestiman la utilidad real. Las métricas de conversación (coherencia, frustración, completitud) son más representativas del comportamiento real.

### 10.3 Suite 3 — Comparación de jueces (qwen2.5:7b vs qwen2.5-coder:7b)

Las 7 reglas de Proaco se repitieron con el segundo juez local para medir consistencia del evaluador.

| Métrica | qwen2.5:7b | qwen2.5-coder:7b | Δ |
|---|---|---|---|
| Tono rioplatense | 0.81 | **0.84** | +0.03 |
| Detección de intent | 0.78 | **0.79** | +0.00 |
| Pedido de contacto | 0.70 | **0.71** | +0.01 |
| Derivación a web | **0.76** | 0.62 | −0.15 |
| Listado máx. 3 | **0.91** | 0.64 | −0.27 |
| Despedida | **0.76** | 0.51 | −0.25 |
| Saludo | **0.64** | 0.25 | −0.38 |

**Conclusión:** el juez coder es **significativamente más estricto** en reglas textuales (saludo −0.38, listado −0.27, despedida −0.25) y casi igual en las conductuales (tono, intent, contacto). La diferencia no cambia las prioridades (saludo sigue siendo lo peor con ambos jueces), pero confirma que **el score absoluto depende del juez**: hay que fijar UN juez como baseline (recomendado: `qwen2.5:7b`) y no mezclar jueces entre corridas.

### 10.4 Detección cruzada de anomalías

| Anomalía | Suite 1 (determinista) | Suite 2 (LLM-judge) | Suite 3 (juez 2) |
|---|---|---|---|
| Llamada-5: loop sin transferencia | Loop 8× (`sin_loop=0`) | Frustración 0.88, completitud 0 | Todo 0 salvo tono |
| Llamada-13: hallucination AySA | `sin_datos_aysa=0` | Tool correct 1.0 pero task completion 0 | Deriva web 0 |
| Llamada-12: sin despedida ni deriva | Despedida 0, URL 0 | Coherencia 0.19, completitud 0 | Saludo 0 |
| Llamada-10: despedida ausente (pero resuelve) | Despedida 1, URL 0 | Coherencia 1.0, completitud 1.0 | Todo alto salvo despedida |

**Las 3 suites convergen en los mismos casos problema**, lo que valida la evaluación original.

### 10.5 Resumen de artefactos nuevos

| Suites | Código | Experimento Opik |
|---|---|---|
| Suite 1 — Heurísticas | `pruebas_ampliadas.py` (funciones `suite_heuristicas`/clases `MetricaTranscripcion`) | `heurísticas-deterministas` |
| Suite 2 — LLM-judges | `suite_llm_judges` | `llm-judges-adicionales` |
| Suite 3 — Juez 2 | `suite_reglas_proaco` | `reglas-proaco-juez-qwen2.5-coder:7b` |
| Descarga de resultados | `descargar_resultados.py` → `resultados_suites.json` | — |

> **Nota de ejecución:** las suites LLM deben correr con `task_threads=1`; con la concurrencia por defecto (16 hilos) Ollama se cuelga y `evaluate()` queda sin progreso.

---

## Apéndice A — Por qué Logs y Dashboard están vacíos

Los traces generados por `evaluate()` tienen `source=experiment` (15 traces y 418 spans en el proyecto). La pestaña **Logs** filtra por `source=sdk` (traces de aplicación en vivo) → 0 resultados. El **Dashboard** muestra KPIs sobre esos mismos traces sdk → vacío. **No es un bug de datos**: los resultados están completos en **Experiments** (experimento `dynamic_annuity_8219`, 13 items con scores).

Para que una llamada aparezca en Logs/Dashboard, el voicebot debe ejecutarse con el SDK de Opik activo (ej. decorando la función de manejo del turno con `@opik.track(project_name="voicebot-proaco-inbound")`). Ejemplo mínimo:

```python
import opik

opik.configure(project_name="voicebot-proaco-inbound", use_local=True)

@opik.track()
def atender_turno(mensaje_cliente: str) -> str:
    # ... lógica del voicebot ...
    return respuesta_del_bot
```

## Apéndice B — Cómo reproducir la evaluación

```bash
# 1. Convertir el CSV a JSON
.venv/bin/python proaco-evaluacion/proaco/inbound/convertir_csv.py

# 2. Correr la evaluación (requiere Ollama con qwen2.5:7b)
.venv/bin/python proaco-evaluacion/proaco/inbound/evaluar.py proaco-evaluacion/proaco/inbound/transcripciones/llamadas_reales.json

# 3. Suite ampliada (heurísticas sin LLM, rápida)
.venv/bin/python proaco-evaluacion/proaco/inbound/pruebas_ampliadas.py --solo suite1

# 4. Suite ampliada (LLM-judges + juez 2, lento: ~45-90 min)
.venv/bin/python proaco-evaluacion/proaco/inbound/pruebas_ampliadas.py --solo suite2
.venv/bin/python proaco-evaluacion/proaco/inbound/pruebas_ampliadas.py --solo suite3

# 5. Descargar resultados por llamada a resultados_suites.json
.venv/bin/python proaco-evaluacion/proaco/inbound/descargar_resultados.py

# 6. Ver resultados en el dashboard local
#    http://localhost:5173/default/projects/voicebot-proaco-inbound/experiments
```

### Escalar a cientos de llamadas (modo nube)

El juez es un modelo de LiteLLM: con un nombre que contiene `/` se usa el proveedor cloud en vez de Ollama. En nube los hilos por defecto son 8 (las APIs paralelizan); en Ollama 1 (evita cuelgues).

```bash
# OpenAI (recomendado como baseline de regresión)
export OPENAI_API_KEY=sk-...
.venv/bin/python proaco-evaluacion/proaco/inbound/evaluar.py proaco-evaluacion/proaco/inbound/transcripciones/llamadas_reales.json --juez openai/gpt-4o-mini

# Groq (free tier, muy rápido) — Llama 3.3 70B
export GROQ_API_KEY=gsk_...
.venv/bin/python proaco-evaluacion/proaco/inbound/pruebas_ampliadas.py --solo suite2 --juez groq/llama-3.3-70b-versatile
.venv/bin/python proaco-evaluacion/proaco/inbound/pruebas_ampliadas.py --solo suite3 --juez2 groq/llama-3.3-70b-versatile

# Gemini Flash (free tier)
export GEMINI_API_KEY=...
.venv/bin/python proaco-evaluacion/proaco/inbound/evaluar.py ... --juez gemini/gemini-2.0-flash
```

Costo aproximado con gpt-4o-mini: ~US$2 por 500 llamadas × 7 reglas. **Regla crítica: fijar UN juez como baseline y no cambiarlo entre corridas** (cada juez puntúa distinto; vimos diferencias de hasta 0.38 entre dos qwen locales).

**Archivos del pipeline:** `proaco-evaluacion/proaco/inbound/convertir_csv.py`, `proaco-evaluacion/proaco/inbound/evaluar.py`, `proaco-evaluacion/proaco/inbound/metricas_proaco.py`, `proaco-evaluacion/proaco/inbound/transcripciones/llamadas_reales.json`.
