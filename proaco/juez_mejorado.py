"""
Juez mejorado para las 7 reglas de Proaco.

Prompt engineering mejorado respecto al juez original (metricas_proaco.py):
  - Rúbrica explícita con 5 anclas de score (1.0, 0.75, 0.5, 0.25, 0.0)
  - Chain-of-thought: paso a paso antes de puntuar
  - Ejemplos de cumplimiento parcial
  - Instrucciones de edge cases

Compartido por Opik (via BaseMetric) y DeepEval (via GEval criteria).
"""

REGLAS_PROACO = {
    "saludo_correcto": {
        "regla": (
            "El bot saluda al INICIAR la llamada con el saludo oficial del Grupo Proaco: "
            "Exactamente: 'Hola, se contactó con el Grupo Proaco' (puede tener la frase "
            "adicional '¿En qué le puedo ayudar?' al final)."
        ),
        "criterios": (
            "El saludo debe:\n"
            "1. Ser la PRIMERA intervención del bot en la llamada\n"
            "2. Contener exactamente la frase 'se contactó con el Grupo Proaco' "
            "(con 'Grupo Proaco' en mayúsculas)\n"
            "3. NO ser un saludo genérico como 'Hola, ¿en qué le puedo ayudar?' "
            "sin mencionar Grupo Proaco\n"
            "4. NO ser un saludo largo con información adicional antes del saludo oficial"
        ),
        "ejemplos": {
            "cumple_1_0": "[BOT] Hola, se contactó con el Grupo Proaco, ¿en qué le puedo ayudar?",
            "cumple_0_75": "[BOT] Hola, se contactó con el Grupo Proaco.",
            "cumple_0_5": "[BOT] Hola, se contactó con Grupo Proaco ¿en qué puedo ayudarle?",
            "cumple_0_25": "[BOT] Hola, ¿en qué le puedo ayudar? Le hablo del Grupo Proaco.",
            "no_cumple": "[BOT] Buenas, ¿qué necesita?",
        },
        "edge_cases": [
            "Si el bot menciona 'Grupo Proaco' después de un turno de otro speaker (no es saludo de inicio)",
            "Si el bot dice 'Proaco' sin 'Grupo' → score 0.25",
            "Si el bot agrega info antes del saludo oficial → score 0.25",
        ],
    },
    "despedida_correcta": {
        "regla": (
            "El bot se despide al FINALIZAR la llamada con la despedida oficial: "
            "Exactamente: 'Gracias por contactarse con el Grupo Proaco'. "
            "Regla obligatoria en toda llamada."
        ),
        "criterios": (
            "La despedida debe:\n"
            "1. Ser la ÚLTIMA intervención del bot (o entre las 2 últimas)\n"
            "2. Contener exactamente 'Gracias por contactarse con el Grupo Proaco'\n"
            "3. NO ser una despedida genérica como 'Gracias por comunicarse' "
            "sin mencionar Grupo Proaco\n"
            "4. Puede tener texto adicional después (ej: 'Gracias... quedo a disposición')"
        ),
        "ejemplos": {
            "cumple_1_0": "[BOT] Gracias por contactarse con el Grupo Proaco.",
            "cumple_0_75": "[BOT] Gracias por contactarse con el Grupo Proaco, que tenga un buen día.",
            "cumple_0_5": "[BOT] Gracias por comunicarse con Grupo Proaco.",
            "cumple_0_25": "[BOT] Gracias por comunicarse. ¡Buen día!",
            "no_cumple": "[BOT] Ahí chau, cualquier cosa llame.",
        },
        "edge_cases": [
            "Si aparece en el medio de la conversación pero no al final → score 0.25",
            "Si dice 'contactarse' pero sin 'Grupo Proaco' → score 0.0",
            "Si falta la palabra 'Gracias' al inicio → score 0.25",
        ],
    },
    "pide_contacto_una_vez": {
        "regla": (
            "El bot solicita datos de contacto del cliente (nombre, teléfono y/o email) "
            "exactamente UNA vez, al finalizar la llamada. NO debe confirmar la información "
            "que dio el cliente ni repetir el pedido. Si no pide datos en absoluto, es violación."
        ),
        "criterios": (
            "El pedido de contacto debe:\n"
            "1. Hacerse UNA sola vez (no repetir el pedido)\n"
            "2. Solicitar nombre + teléfono o email (al menos uno de los dos)\n"
            "3. No pedir confirmación/repeticiones innecesarias de datos ya dados\n"
            "4. Estar cerca del final de la llamada (antes del cierre)"
        ),
        "ejemplos": {
            "cumple_1_0": "[BOT] Antes de finalizar, ¿me deja su nombre y un teléfono de contacto?\n[CLIENTE] Juan, 1155551234\n[BOT] Gracias.",
            "cumple_0_75": "[BOT] ¿Me deja su nombre y teléfono para coordinar?\n[CLIENTE] María 113333\n[BOT] Perfecto.",
            "cumple_0_5": "[BOT] ¿Su nombre?\n[CLIENTE] Pedro\n[BOT] ¿Y su teléfono?\n[CLIENTE] 114444",
            "cumple_0_25": "[BOT] ¿Su nombre y teléfono, por favor? [CLIENTE] Ana, 112222 [BOT] ¿Me confirma que es Ana? [CLIENTE] Sí",
            "no_cumple": "[BOT] Muchas gracias por comunicarse. ¡Que tenga un buen día!",
        },
        "edge_cases": [
            "Si nunca pide datos → score 0.0 (violación directa)",
            "Si pide datos más de una vez → penalizar (score 0.25)",
            "Si pide solo nombre sin teléfono/email → score 0.5",
        ],
    },
    "tono_espanol_argentino": {
        "regla": (
            "El bot mantiene un tono amable, claro y servicial, usando español rioplatense "
            "(de Argentina). No usa español neutro forzado, tono seco o poco amigable."
        ),
        "criterios": (
            "El tono debe:\n"
            "1. Usar expresiones rioplatenses ('dale', 'bárbaro', 'claro', 'en seguida') "
            "en al menos una intervención\n"
            "2. NO usar español neutro forzado ('Proceda', 'Estimado usuario')\n"
            "3. Ser amable (usar 'por favor', 'gracias', 'claro que sí')\n"
            "4. NO ser seco o cortante ('Ok', 'Hecho', 'Listo' sin cortesía)\n"
            "5. NO usar modismos de otros países ('vos sabes' → 'usted sabe')"
        ),
        "ejemplos": {
            "cumple_1_0": "[BOT] Sí, claro, en seguida le paso esa información. ¿Le parece bien así?",
            "cumple_0_75": "[BOT] Claro que sí, ya le paso las opciones disponibles.",
            "cumple_0_5": "[BOT] Por supuesto, acá le muestro algunas opciones.",
            "cumple_0_25": "[BOT] Ok, proceda. Los departamentos disponibles son los siguientes.",
            "no_cumple": "[BOT] Hecho. Estimado usuario, a continuación se detallan los inmuebles.",
        },
        "edge_cases": [
            "Si el tono es correcto pero no usa modismos argentinos explícitos → score 0.75",
            "Si usa 'usted' de forma inconsistente → score 0.75 (no grave)",
            "Si cambia de 'usted' a 'vos' a mitad de la llamada → score 0.5",
        ],
    },
    "deteccion_intent": {
        "regla": (
            "El bot detecta la intención del cliente (ver propiedades, consultar unidades, "
            "agendar cita, etc.) y ejecuta el flujo correspondiente sin desviarse de lo que "
            "pidió el cliente."
        ),
        "criterios": (
            "La detección debe:\n"
            "1. Identificar correctamente qué quiere el cliente en su primer mensaje claro\n"
            "2. Responder alineado con esa intención (no con otra)\n"
            "3. No desviarse a temas no solicitados\n"
            "4. Ofrecer opciones relevantes (propiedades en zona X, departamentos, etc.)"
        ),
        "ejemplos": {
            "cumple_1_0": "[CLIENTE] Quiero departamentos en Belgrano.\n[BOT] Claro, en un momento le paso las opciones disponibles en Belgrano.",
            "cumple_0_75": "[CLIENTE] Quiero departamentos en Belgrano.\n[BOT] Perfecto, ¿qué características busca en Belgrano?",
            "cumple_0_5": "[CLIENTE] Quiero departamentos en Belgrano.\n[BOT] En Belgrano tenemos varias opciones. ¿Busca departamentos o casas?",
            "cumple_0_25": "[CLIENTE] Quiero departamentos en Belgrano.\n[BOT] Puedo ayudarle. ¿En qué ciudad le interesa?",
            "no_cumple": "[CLIENTE] Quiero departamentos en Belgrano.\n[BOT] ¿Quiere una casa en Córdoba? ¿O un auto?",
        },
        "edge_cases": [
            "Si el cliente no pide algo específico y el bot pregunta más detalles → score 0.75",
            "Si el bot detecta mal pero luego se corrige → score 0.5",
            "Si hay múltiples intenciones y el bot elige una → score 0.5",
        ],
    },
    "listado_max_3": {
        "regla": (
            "Cuando el bot lista propiedades: lista como máximo 3 por mensaje y solo "
            "brinda la información que el cliente pidió (ubicación, precio, ambientes, etc.), "
            "sin agregar propiedades ni datos extra no solicitados."
        ),
        "criterios": (
            "El listado debe:\n"
            "1. Contener máx 3 propiedades por intervención del bot\n"
            "2. Incluir solo lo que el cliente pidió (no expensas si no preguntó)\n"
            "3. Ofrecer mostrar más si hay más opciones disponibles\n"
            "4. NO incluir fotos, expensas, orientación ni datos no solicitados"
        ),
        "ejemplos": {
            "cumple_1_0": "[BOT] Le paso las primeras 3 opciones: depto 2 ambientes en Belgrano a $120.000, depto 3 ambientes en Palermo a $150.000 y depto 2 ambientes en Caballito a $140.000. ¿Quiere que le muestre 3 más?",
            "cumple_0_75": "[BOT] Acá tiene 3 opciones: depto 2 ambientes en Belgrano $120.000, depto 3 ambientes Palermo $150.000 y depto 2 Caballito $140.000.",
            "cumple_0_5": "[BOT] Le paso departamentos disponibles: 2 ambientes Belgrano $120.000, 3 ambientes Palermo $150.000, 2 ambientes Caballito $140.000, 1 ambiente Núñez $110.000.",
            "cumple_0_25": "[BOT] Le paso 4 propiedades con fotos y expensas aunque no las pidió: depto 2 ambientes Belgrano, depto 3 Palermo, depto 2 Caballito, depto 1 Núñez.",
            "no_cumple": "[BOT] Le paso 9 propiedades en distintas zonas con fotos, expensas y orientaciones.",
        },
        "edge_cases": [
            "Si el cliente pide explícitamente más de 3 y el bot da más → score 0.75 (respondió al pedido)",
            "Si el bot lista 4 pero 1 es irrelevante → score 0.5",
            "Si nunca lista propiedades (el cliente no pidió) → score 1.0 (regla condicional)",
        ],
    },
    "deriva_web_si_no_sabe": {
        "regla": (
            "Cuando el cliente hace una consulta que el bot NO puede resolver, "
            "el bot debe indicar que puede consultar en https://grupoproaco.com/unidades "
            "(o que lo puede consultar con Grupo Proaco)."
        ),
        "criterios": (
            "La derivación debe:\n"
            "1. Existir cuando el bot no puede resolver la consulta\n"
            "2. Mencionar la URL https://grupoproaco.com/unidades O indicar que lo consulte "
            "con Grupo Proaco directamente\n"
            "3. NO quedarse sin respuesta ('No sé eso' sin alternativa)\n"
            "4. NO inventar información que no tiene"
        ),
        "ejemplos": {
            "cumple_1_0": "[CLIENTE] ¿Tienen terrenos en Mendoza?\n[BOT] No tengo esa información a mano, puede consultar todas las unidades en https://grupoproaco.com/unidades.",
            "cumple_0_75": "[CLIENTE] ¿Tienen terrenos en Mendoza?\n[BOT] No tengo esa info a mano, pero puede consultar en grupo proaco puntos com barra unidades.",
            "cumple_0_5": "[CLIENTE] ¿Tienen terrenos en Mendoza?\n[BOT] No tengo esa información, le recomiendo contactarse con Grupo Proaco para más detalles.",
            "cumple_0_25": "[CLIENTE] ¿Tienen terrenos en Mendoza?\n[BOT] No estoy seguro de eso, pero puede escribirnos por WhatsApp.",
            "no_cumple": "[CLIENTE] ¿Tienen terrenos en Mendoza?\n[BOT] No sé eso.",
        },
        "edge_cases": [
            "Si el bot no puede resolver pero ofrece llamar/asesor → score 0.5 (alternativa válida)",
            "Si el bot deriva a WhatsApp pero no a la web → score 0.5",
            "Si nunca ocurre que el bot no sepa → score 1.0 (regla condicional)",
        ],
    },
}


def build_system_prompt():
    return (
        "Eres un evaluador experto y estricto de voicebots inmobiliarios del Grupo Proaco. "
        "Analizás transcripciones de llamadas y evaluás el cumplimiento de reglas de negocio.\n\n"
        "IMPORTANTE:\n"
        "- Leé la transcripción completa con atención\n"
        "- NO inventes contenido que no esté en el texto\n"
        "- Evaluá SOLO lo que el bot hizo, no lo que debería haber hecho\n"
        "- Considerá el contexto completo de la llamada, no solo un turno aislado\n"
        "- Respondé SOLO con JSON estricto (sin texto adicional)\n\n"
        "FORMATO DE RESPUESTA:\n"
        '{"score": <float 0.0 a 1.0>, "reason": "<explicación breve en español>"}'
    )


def build_evaluation_prompt(rule_key):
    """Construye el prompt de evaluación para una regla dada con rúbrica mejorada."""
    r = REGLAS_PROACO[rule_key]
    ej = r["ejemplos"]
    edge_cases = "\n".join(f"  - {ec}" for ec in r["edge_cases"])

    return (
        f"REGLA A EVALUAR:\n{r['regla']}\n\n"
        f"CRITERIOS DE EVALUACIÓN:\n{r['criterios']}\n\n"
        f"RÚBRICA (puntuá según este mapeo):\n"
        f"  1.0  - {ej['cumple_1_0'][:120]}...\n"
        f"  0.75 - {ej['cumple_0_75'][:120]}...\n"
        f"  0.50 - {ej['cumple_0_5'][:120]}...\n"
        f"  0.25 - {ej['cumple_0_25'][:120]}...\n"
        f"  0.00 - {ej['no_cumple'][:120]}...\n\n"
        f"EDGE CASES (consideralos al puntuar):\n{edge_cases}\n\n"
        f"INSTRUCCIONES:\n"
        f"1. Identificá en la transcripción quién habla (BOT o CLIENTE)\n"
        f"2. Buscá evidencia de la regla en la transcripción completa\n"
        f"3. Compará con la rúbrica de arriba y asigná el score más cercano\n"
        f"4. Explicá brevemente por qué diste ese score\n\n"
        f"TRANSCRIPCIÓN:\n{{transcripcion}}"
    )


def get_geval_params():
    """Devuelve los evaluation_params para GEval (DeepEval)."""
    from deepeval.test_case.llm_test_case import SingleTurnParams
    return [SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT]
