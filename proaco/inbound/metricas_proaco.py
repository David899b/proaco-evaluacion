"""
Métricas LLM-as-judge para el voicebot Grupo Proaco (Camila Mendoza CNX),
basadas en la documentación de Proaco Inbound.

Cada métrica evalúa una regla de interacción sobre la transcripción de la llamada.
El juez responde JSON estricto: {"score": <0.0 a 1.0>, "reason": "..."}

Hay dos tipos de reglas:
  - obligatorias: aplican en TODA llamada (saludo, despedida, pedido de contacto).
  - condicionales: solo aplican si la situación se presenta (deriva a web,
    listado de propiedades, detección de intent).
"""

from typing import List

from opik.evaluation.metrics import base_metric, score_result
from opik.evaluation.metrics.llm_judges import parsing_helpers

SALUDO_OFICIAL = "Hola, se contactó con el Grupo Proaco ¿En qué le puedo ayudar?"
DESPEDIDA_OFICIAL = "Gracias por contactarse con el Grupo Proaco"
WEB_DERIVACION = "https://grupoproaco.com/unidades"


class JuezReglaProaco(base_metric.BaseMetric):
    """Juez LLM genérico: puntúa 0-1 una regla de interacción sobre la transcripción."""

    def __init__(self, name: str, regla: str, ejemplos_bien: str, ejemplos_mal: str,
                 model=None, condicional: bool = False):
        self.name = name
        self.regla = regla
        self.ejemplos_bien = ejemplos_bien
        self.ejemplos_mal = ejemplos_mal
        self.condicional = condicional
        self._model = model
        self._sys_prompt = (
            "Eres un evaluador estricto y detallista de voicebots inmobiliarios. "
            "Analizás la TRANSCRIPCIÓN de una llamada del Grupo Proaco y puntuás el "
            "cumplimiento de UNA regla de interacción. Leés la transcripción con "
            "atención, sin inventar contenido que no esté en el texto. Respondé "
            "SOLO con JSON estricto (sin texto adicional):\n"
            '{"score": <número entre 0.0 y 1.0>, "reason": "<explicación breve>"}\n'
            "- score 1.0: la regla se cumplió.\n"
            "- score 0.0: la regla se violó.\n"
            "- Usá valores intermedios solo para cumplimiento parcial."
        )

    def score(self, transcripcion: str, **ignored_kwargs):
        if self._model is None:
            raise ValueError("No hay modelo juez configurado")
        nota_no_aplica = (
            "IMPORTANTE: esta regla es condicional. Si la situación de la regla "
            "no se presenta en la llamada, puntuá 1.0 (no hubo violación posible).\n"
            if self.condicional
            else ""
        )
        messages = [
            {"role": "system", "content": self._sys_prompt},
            {
                "role": "user",
                "content": (
                    f"REGLA A EVALUAR:\n{self.regla}\n\n"
                    f"{nota_no_aplica}"
                    f"EJEMPLO DE BUEN CUMPLIMIENTO:\n{self.ejemplos_bien}\n\n"
                    f"EJEMPLO DE MAL CUMPLIMIENTO:\n{self.ejemplos_mal}\n\n"
                    f"TRANSCRIPCIÓN A EVALUAR (turnos etiquetados [BOT]/[CLIENTE]):\n"
                    f"{transcripcion}"
                ),
            },
        ]
        respuesta = self._model.generate_provider_response(messages)
        contenido = parsing_helpers.extract_json_content_or_raise(
            respuesta.choices[0].message.content
        )
        score = float(contenido["score"])
        return score_result.ScoreResult(
            name=self.name,
            value=max(0.0, min(1.0, score)),
            reason=str(contenido.get("reason", "")),
        )


def crear_metricas_proaco(model) -> List[JuezReglaProaco]:
    """Devuelve las métricas de las reglas de Proaco listas para evaluate()."""
    return [
        JuezReglaProaco(
            name="saludo_correcto",
            regla=(
                "El bot saluda al iniciar la llamada con el saludo oficial del Grupo "
                f"Proaco ({SALUDO_OFICIAL}). Regla obligatoria en toda llamada."
            ),
            ejemplos_bien="[BOT] Hola, se contactó con el Grupo Proaco, ¿en qué le puedo ayudar?",
            ejemplos_mal="[BOT] Buenas, ¿qué necesita?",
            model=model,
        ),
        JuezReglaProaco(
            name="despedida_correcta",
            regla=(
                "El bot se despide al finalizar la llamada con la despedida oficial "
                f"del Grupo Proaco ({DESPEDIDA_OFICIAL}). Regla obligatoria en toda "
                "llamada."
            ),
            ejemplos_bien="[BOT] Gracias por contactarse con el Grupo Proaco.",
            ejemplos_mal="[BOT] Ahí chau.",
            model=model,
        ),
        JuezReglaProaco(
            name="deteccion_intent",
            regla=(
                "El bot detecta la intención del cliente (p. ej. ver propiedades, "
                "consultar unidades) a partir de un trigger en la conversación y "
                "ejecuta el flujo correspondiente sin desviarse de lo que pidió el cliente."
            ),
            ejemplos_bien=(
                "[CLIENTE] Hola, quería saber qué departamentos en venta tienen en Belgrano.\n"
                "[BOT] Claro, en un momento le paso las opciones disponibles."
            ),
            ejemplos_mal=(
                "[CLIENTE] Hola, quería saber qué departamentos tienen en Belgrano.\n"
                "[BOT] ¿Quiere una casa en Córdoba? ¿O un auto?"
            ),
            condicional=True,
            model=model,
        ),
        JuezReglaProaco(
            name="pide_contacto_una_vez",
            regla=(
                "El bot solicita los datos de contacto del cliente (nombre, teléfono, "
                "mail) exactamente UNA vez, al finalizar la llamada y antes del mensaje "
                "de despedida. NO debe confirmar la información que dio el cliente "
                "ni repetir el pedido. Regla obligatoria en toda llamada: si no pide "
                "los datos, es una violación."
            ),
            ejemplos_bien=(
                "[BOT] Antes de finalizar, ¿me deja su nombre y un teléfono de contacto?\n"
                "[CLIENTE] Juan, 1155551234\n[BOT] Gracias."
            ),
            ejemplos_mal=(
                "[BOT] ¿Su nombre? [CLIENTE] Juan [BOT] ¿Y su teléfono? [CLIENTE] 115555 "
                "[BOT] ¿Me confirma que es 115555? ¿Me repite el nombre? ¿Tiene mail?"
            ),
            model=model,
        ),
        JuezReglaProaco(
            name="listado_max_3",
            regla=(
                "Cuando el bot lista propiedades al cliente: lista como máximo 3 por "
                "mensaje y solo brinda la información que el cliente pidió (ubicación, "
                "precio, ambientes, etc.), sin agregar propiedades ni datos extra."
            ),
            ejemplos_bien=(
                "[BOT] Le paso las primeras 3 opciones: depto 2 ambientes en Belgrano "
                "a $120.000, depto 3 ambientes en Belgrano a $150.000 y depto 2 "
                "ambientes en Palermo a $140.000. ¿Quiere que le muestre 3 más?\n"
                "[CLIENTE] Sí, dale.\n"
                "[BOT] Perfecto, las siguientes 3 son: depto 2 ambientes en Caballito "
                "a $110.000, depto 2 en Nuñez a $150.000 y depto 3 en Palermo a "
                "$160.000."
            ),
            ejemplos_mal=(
                "[BOT] Le paso 9 propiedades en distintas zonas y de distintos precios, "
                "con fotos, expensas y orientaciones aunque no las pidió."
            ),
            condicional=True,
            model=model,
        ),
        JuezReglaProaco(
            name="tono_espanol_argentino",
            regla=(
                "El bot mantiene un tono amable, claro y servicial, usando español "
                "rioplatense (de Argentina). No usa español neutro forzado ni tono "
                "seco o poco amigable."
            ),
            ejemplos_bien="[BOT] Sí, claro, en seguida le paso esa información.",
            ejemplos_mal="[BOT] Ok. Proceda. El dato requerido es el siguiente.",
            model=model,
        ),
        JuezReglaProaco(
            name="deriva_web_si_no_sabe",
            regla=(
                "Cuando el cliente hace una consulta que el bot NO puede resolver, "
                "el bot debe indicar que puede consultar con Grupo Proaco en "
                f"{WEB_DERIVACION} (o que lo puede consultar con Grupo Proaco)."
            ),
            ejemplos_bien=(
                "[CLIENTE] ¿Tienen terrenos en Mendoza?\n"
                "[BOT] No tengo esa información a mano, puede consultar todas las "
                f"unidades en {WEB_DERIVACION}."
            ),
            ejemplos_mal=(
                "[CLIENTE] ¿Tienen terrenos en Mendoza?\n"
                "[BOT] No sé eso."
            ),
            condicional=True,
            model=model,
        ),
    ]
