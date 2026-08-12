"""Reglas del voicebot OUTBOUND de Proaco (llamadas salientes a leads).

FLUJO PROPIO: el bot inicia la llamada, se presenta, explica el motivo (campaña /
emprendimiento / interés previo), pide consentimiento para continuar, califica,
ofrece agendar cita (CalDotCom) y cierra cortésmente ante "no me interesa".

NOTA: conjunto en DRAFT, a validar contra transcripciones outbound reales
(salen del pgAdmin). Las reglas del inbound NO aplican tal cual:
- acá NO hay "saludo oficial de bienvenida" (el bot habla primero).
- "pide_contacto" no aplica (el bot ya tiene el contacto del lead).
"""

from opik.evaluation.metrics import base_metric
from opik.evaluation.metrics.score_result import ScoreResult


def a_texto(transcripcion):
    """Normaliza una transcripción (string o lista de turnos) a texto [BOT]/[CLIENTE]."""
    if isinstance(transcripcion, str):
        return transcripcion
    lineas = []
    for turno in transcripcion:
        speaker = str(turno.get("speaker", "")).upper()
        etiqueta = "BOT" if speaker in ("BOT", "AGENTE", "AGENT", "ASISTENTE") else "CLIENTE"
        lineas.append(f"[{etiqueta}] {turno.get('text', '')}")
    return "\n".join(lineas)


class MetricaOutbound(base_metric.BaseMetric):
    """Base: recibe la transcripción completa (input/output/transcripcion/conversation)."""

    def __init__(self, name, track=True):
        super().__init__(name=name, track=track)

    def score(self, transcripcion, **ignored_kwargs):
        if isinstance(transcripcion, dict):
            transcripcion = a_texto(transcripcion.get("conversation", [])) or a_texto(transcripcion)
        cumple, razon = self._evaluar(str(transcripcion))
        return ScoreResult(name=self.name, value=1.0 if cumple else 0.0, reason=razon)

    def _evaluar(self, transcripcion):
        raise NotImplementedError


class SePresenta(MetricaOutbound):
    """El bot se identifica como Grupo Proaco al inicio de la llamada."""

    def _evaluar(self, transcripcion):
        texto = transcripcion.lower()
        marcadores = ["grupo proaco", "proaco", "te hablo de", "te llamo de", "le hablo de"]
        ok = any(m in texto for m in marcadores)
        return ok, "bot identificado" if ok else "bot no se presentó como Proaco"


class MencionaProposito(MetricaOutbound):
    """El bot explica el motivo de la llamada (campaña / emprendimiento / interés previo)."""

    def _evaluar(self, transcripcion):
        texto = transcripcion.lower()
        proposito = ["le llamo", "te llamo", "lo contacto", "te contacto", "comunicamos con usted",
                     "su interés", "tu interés", "emprendimiento", "campaña", "consultó", "consulto",
                     "unidad", "inversión", "inversion"]
        ok = any(p in texto for p in proposito)
        return ok, "motivo mencionado" if ok else "no se menciona el motivo de la llamada"


class PideConsentimiento(MetricaOutbound):
    """El bot pregunta si puede continuar / es buen momento (regla típica de outbound)."""

    def _evaluar(self, transcripcion):
        texto = transcripcion.lower()
        marcas = ["¿le molesta", "le molesta", "¿puede hablar", "puede hablar", "¿es buen momento",
                  "es buen momento", "tiene unos minutos", "¿tiene un momento", "tiene un momento",
                  "¿puedo continuar", "puedo continuar", "lo puedo atender", "la puedo atender"]
        ok = any(m in texto for m in marcas)
        return ok, "consentimiento solicitado" if ok else "no se pidió consentimiento para continuar"


class ManejaNoInteres(MetricaOutbound):
    """Ante 'no me interesa', el bot cierra cortésmente sin insistir ni entrar en loop."""

    def _evaluar(self, transcripcion):
        texto = transcripcion.lower()
        hay_no_interes = any(f in texto for f in ["no me interesa", "no estoy interesado", "no estoy interesada",
                                                  "no quiero", "no me llame", "no me moleste", "ya tengo",
                                                  "no gracias"])
        if not hay_no_interes:
            return True, "no hubo manifestación de no-interés"
        loop = texto.count("no puedo transferir") + texto.count("insistir") + texto.count("¿está seguro")
        cierre_cortes = any(c in texto for c in ["gracias", "que tenga un buen día", "buen día", "hasta luego",
                                                 "no lo molestamos", "no le molesto", "lo dejo"])
        ok = cierre_cortes and loop == 0
        return ok, "cierre cortés sin insistir" if ok else "insistió o no cerró cortésmente"


class OfreceAgendarCita(MetricaOutbound):
    """Si hay interés, el bot ofrece agendar cita/visita (CalDotCom)."""

    def _evaluar(self, transcripcion):
        texto = transcripcion.lower()
        marcas = ["agendar", "agenda una", "una cita", "un turno", "reservar", "visita", "calendario",
                  "caldotcom", "schedule", "turno con un asesor", "reunión", "reunion"]
        ok = any(m in texto for m in marcas)
        return ok, "ofrece agendar cita" if ok else "no se ofreció agendar cita"


class ListadoMax3(MetricaOutbound):
    """Si lista propiedades, de a máximo 3 y solo lo que pidió el lead."""

    def _evaluar(self, transcripcion):
        import re
        if "listado" not in transcripcion.lower() and "opciones" not in transcripcion.lower():
            if any(p in transcripcion.lower() for p in ["departamento", "lote", "casa", "oficina", "local"]):
                pass
            else:
                return True, "no hubo listado"
        lista = re.findall(r"[\d]+[º°]?\s*(?:piso|depto|departamento|lote|unidad|torre|dormitorio|ambientes)", transcripcion, re.I)
        return len(lista) <= 3, f"{len(lista)} ítems listados (máx 3)"


class TonoRespetuoso(MetricaOutbound):
    """Heurística: sin insultos ni gritos (mayúsculas sostenidas)."""

    def _evaluar(self, transcripcion):
        prohibidas = ["callate", "cállate", "estúpido", "estupido", "idiota", "hdp", "boludo", "tarado"]
        texto = transcripcion.lower()
        if any(p in texto for p in prohibidas):
            return False, "frase prohibida detectada"
        mayus = [p.strip(".,;:()¿?¡!\"'") for p in transcripcion.split()
                 if p.strip(".,;:()¿?¡!\"'").isupper() and len(p.strip(".,;:()¿?¡!\"'")) > 3
                 and "[" not in p and "]" not in p]
        if len(mayus) > 3:
            return False, f"demasiadas palabras en mayúsculas: {mayus[:3]}"
        return True, "tono respetuoso"


def crear_metricas_proaco_outbound(model):
    """Metricas LLM-judge para el flow outbound (reglas de negocio)."""
    from opik.evaluation.metrics import GEval

    reglas = [
        ("cliente_no_interesado", "El bot de Grupo Proaco llama a un lead (llamada saliente). "
         "Si el lead dice que no le interesa, el bot debe cerrar la llamada cortésmente, sin insistir "
         "ni repetir la oferta. La transcripción está en formato [BOT]/[CLIENTE]."),
        ("agendamiento_cita", "El bot de Grupo Proaco llama a un lead (llamada saliente). Si el lead "
         "muestra interés, el bot debe ofrecer agendar una cita o derivarlo a un asesor. "
         "La transcripción está en formato [BOT]/[CLIENTE]."),
    ]
    return [
        GEval(
            name=name,
            model=model,
            task_introduction=(
                "Eres un evaluador estricto del voicebot de llamadas salientes de Grupo Proaco. "
                "La transcripción a evaluar está en formato [BOT]/[CLIENTE]. "
                "Puntuás el cumplimiento de UN criterio con un score de 0 a 1."
            ),
            evaluation_criteria=criteria,
        )
        for name, criteria in reglas
    ]


HEURISTICAS_OUTBOUND = [
    SePresenta(name="se_presenta"),
    MencionaProposito(name="menciona_proposito"),
    PideConsentimiento(name="pide_consentimiento"),
    ManejaNoInteres(name="maneja_no_interes"),
    OfreceAgendarCita(name="ofrece_agendar_cita"),
    ListadoMax3(name="listado_max_3"),
    TonoRespetuoso(name="tono_respetuoso"),
]
