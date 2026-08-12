"""
Suite ampliada de pruebas del voicebot Grupo Proaco con Opik.

Agrupa TODAS las pruebas posibles con la instalación local (Opik + Ollama):

  Suite 1 - Heurísticas deterministas (sin LLM): saludo exacto, despedida exacta,
            URL de derivación presente, tono (VADER), adherencia al idioma español,
            respuesta no vacía. Rápidas y reproducibles.

  Suite 2 - Métricas LLM-judge adicionales de Opik: Usefulness, AnswerRelevance,
            Moderation, AgentTaskCompletionJudge, AgentToolCorrectnessJudge,
            ConversationalCoherence, UserFrustration, SessionCompleteness.

  Suite 3 - Reglas de Proaco (las 7 métricas originales) con el segundo juez
            (qwen2.5-coder:7b) para comparar consistencia entre jueces.

Cada suite se guarda como un experimento separado en Opik (proyecto voicebot-proaco).
Se imprimen promedios por métrica y un resumen de comparación entre jueces.

MODO NUBE: el juez puede ser cualquier modelo soportado por LiteLLM. Con un nombre que
contenga "/" (proveedor/modelo) se usa tal cual; sin "/" se asume Ollama local. Ejemplos:
  --juez "openai/gpt-4o-mini"          (requiere OPENAI_API_KEY)
  --juez "groq/llama-3.3-70b-versatile" (requiere GROQ_API_KEY)
  --juez "gemini/gemini-2.0-flash"      (requiere GEMINI_API_KEY)
  --juez "anthropic/claude-3-5-sonnet-20241022" (requiere ANTHROPIC_API_KEY)
En nube los hilos por defecto son 8 (las APIs paralelizan); en Ollama 1 (evita cuelgues).

Uso:
  .venv/bin/python proaco-evaluacion/pruebas_ampliadas.py [--solo suite1|suite2|suite3]
      [--juez openai/gpt-4o-mini] [--juez2 qwen2.5-coder:7b] [--threads N]
"""

import argparse
import os
import sys

import opik
from opik.evaluation import evaluate
from opik.evaluation.metrics.base_metric import BaseMetric
from opik.evaluation.metrics import (
    Usefulness,
    AnswerRelevance,
    Moderation,
    AgentTaskCompletionJudge,
    AgentToolCorrectnessJudge,
    ConversationalCoherenceMetric,
    UserFrustrationMetric,
    SessionCompletenessQuality,
)
from opik.evaluation.metrics.score_result import ScoreResult

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluar import a_texto, cargar_items  # noqa: E402
from metricas_proaco import crear_metricas_proaco  # noqa: E402

PROJECT_NAME = "voicebot-proaco-inbound"
PREFIX = "proaco-inbound"
JUEZ1 = "qwen2.5:7b"
JUEZ2 = "qwen2.5-coder:7b"
FUENTE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcripciones", "llamadas_reales.json")

SALUDO_OFICIAL = "Hola, se contactó con el Grupo Proaco"
DESPEDIDA_OFICIAL = "Gracias por contactarse con el Grupo Proaco"
URL_OFICIAL = "grupoproaco.com/unidades"

PROVEEDOR_KEY = {
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "together": "TOGETHER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "cohere": "COHERE_API_KEY",
}


def crear_juez(modelo):
    """Devuelve un LiteLLMChatModel para el juez. Con '/' se usa el proveedor tal cual;
    sin '/' se asume Ollama local. Valida que esté la API key del proveedor en el entorno."""
    if "/" not in modelo:
        modelo = f"ollama/{modelo}"
    proveedor = modelo.split("/", 1)[0].lower()
    var = PROVEEDOR_KEY.get(proveedor)
    if var and not os.environ.get(var):
        raise SystemExit(
            f"Falta la API key para el proveedor '{proveedor}': export {var}=... "
            f"(o usá --juez con un modelo de otro proveedor)."
        )
    return opik.evaluation.models.LiteLLMChatModel(model_name=modelo)


def hilos_defecto(modelo):
    """Ollama serializa por modelo (-np 1) y se cuelga con mucha concurrencia: 1 hilo.
    En nube las APIs paralelizan: 8 hilos por defecto."""
    return 8 if "/" in modelo else 1


def construir_payloads(items):
    """Convierte cada item en dicts para las métricas: input/output/transcripcion/conversation."""
    payloads = []
    for item in items:
        texto = item["transcripcion"]  # ya es texto [BOT]/[CLIENTE]
        turnos = []
        lineas = [l for l in texto.split("\n") if l.strip()]
        # primera y última intervención del bot como input/output de la llamada
        entrada_cliente = ""
        salida_bot = ""
        for l in lineas:
            if l.startswith("[BOT]"):
                salida_bot = l.replace("[BOT] ", "", 1)
            elif l.startswith("[CLIENTE]"):
                if not entrada_cliente:
                    entrada_cliente = l.replace("[CLIENTE] ", "", 1)
        # conversación en formato Opik (user/assistant alternados)
        conversation = []
        for l in lineas:
            if l.startswith("[CLIENTE]"):
                conversation.append({"role": "user", "content": l.replace("[CLIENTE] ", "", 1)})
            elif l.startswith("[BOT]"):
                conversation.append({"role": "assistant", "content": l.replace("[BOT] ", "", 1)})
        payloads.append({
            "input": entrada_cliente,
            "output": salida_bot,
            "transcripcion": texto,
            "conversation": conversation,
            "llamada_id": item["llamada_id"],
            "metadata": item.get("metadata", {}),
        })
    return payloads


def tarea(payload):
    return {k: v for k, v in payload.items() if k != "llamada_id"}


def imprimir_resultados(nombre_suite, resultado):
    print(f"\n=== {nombre_suite} ===")
    acum = {}
    for test in resultado.test_results:
        for s in test.score_results:
            acum.setdefault(s.name, []).append(s.value)
    for nombre, valores in sorted(acum.items()):
        media = sum(valores) / len(valores)
        print(f"  {nombre:<32} avg={media:.3f}  n={len(valores)}")
    return acum


class MetricaTranscripcion(BaseMetric):
    """Base para métricas deterministas que leen la transcripción completa (transcripcion kwarg)."""

    def __init__(self, name, track=True, project_name=None):
        super().__init__(name=name, track=track, project_name=project_name)

    def score(self, transcripcion, **kwargs):
        cumple, razon = self._evaluar(transcripcion)
        return ScoreResult(name=self.name, value=1.0 if cumple else 0.0, reason=razon)

    def _evaluar(self, transcripcion):
        raise NotImplementedError


def turnos_bot(texto):
    return [l.replace("[BOT] ", "", 1) for l in texto.split("\n") if l.strip().startswith("[BOT]")]


class SaludoPresente(MetricaTranscripcion):
    def _evaluar(self, transcripcion):
        bot = turnos_bot(transcripcion)
        if not bot:
            return False, "sin turnos del bot"
        t1 = bot[0].lower()
        saludos = ["hola", "buen dia", "buen día", "gracias por comunicarte", "mucho gusto", "bienvenido"]
        ok = any(s in t1 for s in saludos)
        return ok, f"primer turno bot: {bot[0][:80]!r}"


class DespedidaPresente(MetricaTranscripcion):
    def _evaluar(self, transcripcion):
        bot = turnos_bot(transcripcion)
        if not bot:
            return False, "sin turnos del bot"
        tlast = bot[-1].lower()
        despedidas = ["en lo que pueda ayudar", "que te ayude con algo más", "para asistirle",
                      "para ayudarte", "gracias por contactarse", "quedo a tu disposición"]
        ok = any(s in tlast for s in despedidas)
        return ok, f"último turno bot: {bot[-1][:80]!r}"


class UrlDerivacionPresente(MetricaTranscripcion):
    def _evaluar(self, transcripcion):
        ok = URL_OFICIAL in transcripcion.lower()
        return ok, f"url {URL_OFICIAL!r} {'presente' if ok else 'ausente'}"


class SinDatosAysa(MetricaTranscripcion):
    def _evaluar(self, transcripcion):
        ok = "aysa" not in transcripcion.lower()
        return ok, "sin referencia a AySA" if ok else "hallucination: bot citó datos de AySA"


class SinLoopNoTransferir(MetricaTranscripcion):
    def _evaluar(self, transcripcion):
        texto = transcripcion.lower()
        n = texto.count("no puedo transferir") + texto.count("no poder transferir") + texto.count("transferir llamadas")
        return n <= 2, f"{n} menciones de no-poder-transferir"


class TonoRespetuoso(MetricaTranscripcion):
    def _evaluar(self, transcripcion):
        prohibidas = ["callate", "cállate", "estúpido", "estupido", "idiota", "hdp", "boludo", "tarado"]
        texto_baja = transcripcion.lower()
        if any(p in texto_baja for p in prohibidas):
            return False, f"frase prohibida detectada"
        mayus = [p.strip(".,;:()¿?¡!\"'") for p in transcripcion.split()
                 if p.strip(".,;:()¿?¡!\"'").isupper() and len(p.strip(".,;:()¿?¡!\"'")) > 3
                 and "[" not in p and "]" not in p]
        if len(mayus) > 3:
            return False, f"demasiadas palabras en mayúsculas: {mayus[:3]}"
        if transcripcion.count("!") > 5:
            return False, "demasiadas exclamaciones"
        return True, "tono respetuoso"


class AdherenciaEspanol(MetricaTranscripcion):
    def _evaluar(self, transcripcion):
        marcadores = "áéíóúÁÉÍÓÚñÑ¿¡"
        stopwords_es = {"de", "la", "el", "que", "y", "en", "un", "por", "con", "no", "una", "su", "al", "los", "las", "se"}
        palabras = [p.lower().strip(",.¿?¡!") for p in transcripcion.split()]
        peso = sum(1 for c in transcripcion if c in marcadores) + sum(1 for p in palabras if p in stopwords_es)
        return peso > 0, f"marcadores de español: {peso}"


def suite_heuristicas(items):
    """Suite 1: heurísticas deterministas sobre la transcripción completa, sin LLM."""
    metricas = [
        SaludoPresente(name="saludo_presente"),
        DespedidaPresente(name="despedida_presente"),
        UrlDerivacionPresente(name="url_derivacion_presente"),
        SinDatosAysa(name="sin_datos_aysa"),
        SinLoopNoTransferir(name="sin_loop_no_transferir"),
        TonoRespetuoso(name="tono_respetuoso"),
        AdherenciaEspanol(name="adherencia_espanol"),
    ]
    resultado = evaluate(
        dataset=crear_dataset(dataset_name="transcripciones-proaco-inbound-heuristicas", items=items),
        task=tarea,
        scoring_metrics=metricas,
        experiment_name=f"{PREFIX}-heurísticas-deterministas",
        verbose=1,
    )
    imprimir_resultados("SUITE 1 - Heurísticas deterministas", resultado)
    return resultado


def suite_llm_judges(items, modelo, threads=1):
    """Suite 2: métricas LLM-judge adicionales de Opik."""
    juez = crear_juez(modelo)
    metricas = [
        Usefulness(model=juez, name="usefulness"),
        AnswerRelevance(model=juez, name="answer_relevance", require_context=False),
        Moderation(model=juez, name="moderation"),
        AgentTaskCompletionJudge(model=juez),
        AgentToolCorrectnessJudge(model=juez),
        ConversationalCoherenceMetric(model=juez, name="conversational_coherence"),
        UserFrustrationMetric(model=juez, name="user_frustration"),
        SessionCompletenessQuality(model=juez, name="session_completeness"),
    ]
    resultado = evaluate(
        dataset=crear_dataset(dataset_name="transcripciones-proaco-inbound-llmjudges", items=items),
        task=tarea,
        scoring_metrics=metricas,
        experiment_name=f"{PREFIX}-llm-judges-adicionales",
        verbose=1,
        task_threads=threads,
    )
    imprimir_resultados(f"SUITE 2 - LLM-judge adicionales ({modelo})", resultado)
    return resultado


def suite_reglas_proaco(items, modelo, threads=1):
    """Suite 3: reglas de Proaco con el segundo juez (comparación de jueces)."""
    juez = crear_juez(modelo)
    metricas = crear_metricas_proaco(juez)
    resultado = evaluate(
        dataset=crear_dataset(dataset_name="transcripciones-proaco-inbound-jueces", items=items),
        task=tarea,
        scoring_metrics=metricas,
        experiment_name=f"{PREFIX}-reglas-proaco-juez-{modelo}",
        verbose=1,
        task_threads=threads,
    )
    imprimir_resultados(f"SUITE 3 - Reglas Proaco con juez {modelo}", resultado)
    return resultado


def crear_dataset(dataset_name, items):
    client = opik.Opik()
    ds = client.get_or_create_dataset(name=dataset_name, project_name=PROJECT_NAME)
    ds.clear()
    ds.insert([
        {"input": p["input"], "output": p["output"], "transcripcion": p["transcripcion"],
         "conversation": p["conversation"],
         "metadata": {"llamada_id": p["llamada_id"], **p["metadata"]}}
        for p in items
    ])
    return ds


def comparar_jueces(base_results, otros_results):
    """Compara promedios entre el juez base y el segundo juez por métrica de Proaco."""
    print("\n=== COMPARACIÓN DE JUECES (qwen2.5:7b vs segundo juez) ===")
    solo_base = {k: v for k, v in base_results.items() if k in otros_results}
    for nombre in sorted(solo_base):
        a = sum(solo_base[nombre]) / len(solo_base[nombre])
        b = sum(otros_results[nombre]) / len(otros_results[nombre])
        dif = b - a
        print(f"  {nombre:<32} base={a:.3f}  juez2={b:.3f}  Δ={dif:+.3f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo", choices=["suite1", "suite2", "suite3"], help="correr solo una suite")
    parser.add_argument("--juez", default=os.environ.get("JUEZ_MODELO", JUEZ1),
                        help=f"modelo juez (suite 2). Default: {JUEZ1}. Con '/' = proveedor cloud.")
    parser.add_argument("--juez2", default=os.environ.get("JUEZ2_MODELO", JUEZ2),
                        help=f"segundo juez para suite 3. Default: {JUEZ2}")
    parser.add_argument("--threads", type=int, default=None,
                        help="task_threads. Default: 8 en nube, 1 en Ollama")
    args = parser.parse_args()

    items = cargar_items(FUENTE)
    payloads = construir_payloads(items)
    print(f"Cargadas {len(payloads)} llamadas desde {FUENTE}")

    threads2 = args.threads if args.threads is not None else hilos_defecto(args.juez)
    threads3 = args.threads if args.threads is not None else hilos_defecto(args.juez2)
    print(f"Juez 1: {args.juez} (threads={threads2}) | Juez 2: {args.juez2} (threads={threads3})")

    opik.configure(project_name=PROJECT_NAME, use_local=True)

    if args.solo == "suite1":
        suite_heuristicas(payloads)
        return
    if args.solo == "suite2":
        suite_llm_judges(payloads, args.juez, threads2)
        return
    if args.solo == "suite3":
        suite_reglas_proaco(payloads, args.juez2, threads3)
        return

    # Todas las suites
    suite_heuristicas(payloads)
    suite_llm_judges(payloads, args.juez, threads2)
    suite_reglas_proaco(payloads, args.juez2, threads3)


if __name__ == "__main__":
    main()
