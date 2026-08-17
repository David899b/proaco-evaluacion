# Proaco OUTBOUND — evaluación del voicebot de llamadas salientes

**Estado: pipeline en producción, esperando datos outbound reales.** Hoy la
campaña "Grupo Proaco" del API de Lula solo tiene las llamadas inbound de QA
(8 touchpoints: 2 con número inválido + 6 con transcript). Las reglas se
validarán con llamadas salientes reales cuando existan.

## Contexto

Flow distinto al inbound: el bot **llama** a un lead (campaña / emprendimiento /
interés previo). La estructura de turnos es la misma (`[BOT]`/`[CLIENTE]`), pero
las reglas de negocio cambian:

- El bot habla primero → no aplica "saludo oficial de bienvenida".
- El bot ya tiene el contacto del lead → no aplica "pide_contacto".
- Importan: presentación, motivo, consentimiento, agendamiento de cita,
  manejo de "no me interesa" sin insistir ni entrar en loop.

## Pipeline

1. `exportar_outbound.py` — baja los touchpoints con transcript de la campaña
   desde el API de Lula (`LULA_API_KEY` por env) → `transcripciones/llamadas_outbound.json`
   con `metadata: {proyecto: "proaco", flow: "outbound", outcome, duration, ...}`.
2. `evaluar_outbound.py` — corre las heurísticas de `metricas_proaco_outbound.py`
   contra Opik en el proyecto `voicebot-proaco-outbound`. Con `--llm` suma los
   LLM-judges GEval (`cliente_no_interesado`, `agendamiento_cita`).
3. `REPORTE_EVALUACION_PROACO_OUTBOUND.md` — reporte propio del flow.

## Convención (NO mezclar)

- Proyecto Opik: `voicebot-proaco-outbound`
- Datasets: `transcripciones-proaco-outbound-*`
- Experimentos: prefijo `proaco-outbound-`
- Las reglas del inbound viven en `../inbound/` y no se reutilizan acá tal cual.
