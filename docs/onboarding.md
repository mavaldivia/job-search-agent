# Onboarding y Actualizar perfil

Diseño de D6 (2026-11-15). Genérico: no lleva datos de ningún usuario. Las respuestas de cada persona viven en su perfil (el del usuario 1 parte de `$AGENTE0_DATOS/origen/` (material de partida); la hoja de su onboarding está en `$AGENTE0_DATOS/origen/` (hoja de onboarding)).

---

## 1. Cómo funciona

- **Modo general (A)**: el agente hace las preguntas del banco (§2), una a la vez, y guarda cada respuesta al confirmarla.
- **Modo con documentos (B)**: solo para el usuario 1 por ahora. El agente parte de una hoja pre-llenada desde sus documentos, presenta cada dato para confirmar, corregir o descartar, y hace la pregunta del banco solo donde la hoja dice `falta`. Ofrecer B a otros usuarios queda para iterar.
- **Una pregunta a la vez.** Sin tandas de preguntas.
- **Solo entra al perfil lo confirmado.** Cada dato guarda su fuente (`dicho por el usuario` o el documento) y la fecha. Lo no confirmado queda como `por_confirmar` y no entra al CV ni a los formularios.
- **No inventar ni completar por inferencia.** Si el usuario no sabe o no quiere responder una pregunta opcional, se registra `sin_respuesta` y se sigue.
- **Primera vez**: el perfil lleva la marca `onboarding_completo` con fecha en el directorio de datos del usuario (D3). Si falta el directorio, el perfil o la marca, se inicia el onboarding. Si se interrumpió, retoma desde la primera pregunta sin confirmar, sin repetir lo ya confirmado.
- **Mínimo para terminar**: todas las preguntas obligatorias (marcadas **Sí** en §2) respondidas y confirmadas. Las opcionales se pueden completar después con "Actualizar perfil" y "Actualizar configuración".
- **Autonomía por defecto**: 0 % si el usuario no elige otra. Con 0 % el agente prepara y no envía nada.
- **Al terminar**: muestra el perfil confirmado y lo que quedó pendiente, y pasa al menú. No ejecuta ninguna acción externa durante el onboarding.

---

## 2. Banco de preguntas

Columnas: ID, pregunta tal como se le hace al usuario, si es obligatoria para terminar el onboarding y para qué se usa.

### 2.1. Experiencia

| ID | Pregunta | Oblig. | Uso |
|---|---|---|---|
| E1 | ¿Cuál es tu nombre completo, como debe aparecer en el CV? | Sí | CV, formularios |
| E2 | ¿Qué datos de contacto van en el CV? (correo, teléfono, LinkedIn, GitHub o portafolio) | Sí (al menos correo) | CV, formularios |
| E3 | ¿Qué estudios formales tienes? (título, institución, mención, años) | Sí | CV, filtros de requisitos |
| E4 | ¿Tienes cursos, certificaciones o distinciones? (nombre, entidad, año, horas, si hay certificado) | No | CV |
| E5 | ¿Qué idiomas hablas y a qué nivel? ¿Está certificado o es autoevaluado? | Sí | CV, formularios |
| E6 | ¿Cuáles son tus cargos, empresas y períodos, del más reciente al más antiguo? (cargo oficial, empresa, fechas, alcance geográfico si aplica) | Sí | CV |
| E7 | Para cada cargo: ¿cuáles fueron tus responsabilidades principales? | Sí | CV |
| E8 | Para cada cargo: ¿qué logros puedes respaldar? Para cada uno: cifra, cómo se midió y si puedes mencionarlo en un CV | No | CV (sin cifra respaldada no se usa cifra) |
| E9 | ¿Qué herramientas y tecnologías usas, y a qué nivel real? (avanzado, intermedio, básico, en exploración) | Sí | CV, requisitos de vacantes |
| E10 | ¿Cuántas personas tienes a cargo? ¿Coordinas equipos sin tener reporte directo? ¿Manejas presupuesto? | Sí | Veracidad en cargos de liderazgo |
| E11 | ¿Tienes proyectos propios o personales relevantes? Para cada uno: qué es, tu rol, estado real (productivo, en desarrollo, experimentación) y si hay usuarios o clientes | No | CV, evidencia |
| E12 | ¿Hay algo de tu trayectoria que no deba afirmarse tal cual (cifras sin respaldo, proyectos aún en desarrollo, títulos informales)? Puede ser "nada" | Sí | Límites de veracidad |
| E13 | ¿Qué brechas reconoces frente a los cargos que buscas? | No | Adaptación de CV, honestidad en formularios |

### 2.2. Intereses

| ID | Pregunta | Oblig. | Uso |
|---|---|---|---|
| I1 | ¿Qué cargos buscas? (títulos o familias de cargos, por prioridad) | Sí (al menos uno) | Búsqueda y priorización |
| I2 | ¿Qué nivel de responsabilidad buscas, y hasta dónde estarías dispuesto a estirarte? | Sí | Filtros, priorización |
| I3 | ¿Dónde y cómo quieres trabajar? (países y ciudades, presencial, híbrido o remoto, tope de viajes, disposición a mudarte) | Sí | Filtros |
| I4 | ¿Qué sectores o tipos de empresa prefieres, y hay empresas objetivo? | No | Priorización |
| I5 | ¿Qué NO quieres? (cargos, sectores, tipos de empresa, condiciones) | No | Filtros excluyentes |
| I6 | ¿Qué señales hacen que una vacante sea un buen fit para ti? ¿Y un fit medio? | No | Priorización |
| I7 | ¿Qué quieres lograr con este cambio y por qué ahora? | No | Respuestas tipo (motivación) |

### 2.3. Configuración inicial

| ID | Pregunta | Oblig. | Uso |
|---|---|---|---|
| C1 | ¿En qué país buscas trabajo principalmente? | Sí | Fuentes de empleos (D10) |
| C2 | ¿Qué correo y teléfono usamos en los formularios de postulación? | Sí | Formularios |
| C3 | ¿Cuál es tu expectativa de renta? (monto, moneda, bruto o líquido, mínimo aceptable, rango si un formulario lo exige) | No | Filtros, respuesta de renta. Si queda sin responder, el agente no declara renta y pide intervención |
| C4 | ¿Desde cuándo podrías empezar? ¿Cuánto aviso previo debes dar? | No | Formularios |
| C5 | ¿En qué países puedes trabajar sin necesidad de visa o permiso? | No | Filtros, formularios |
| C6 | ¿Hay empresas que quieras excluir? ¿Y empresas donde siempre quieras aprobar a mano? | No | Filtros, compuerta de autonomía |
| C7 | ¿Qué nivel de autonomía quieres darle al agente (0 a 100 %)? | Sí (por defecto 0 %) | Compuerta de aprobación. Los niveles y condiciones se fijan en D12 |
| C8 | ¿Cuánto tiempo semanal puedes dedicar a la búsqueda y cuántas postulaciones o procesos activos quieres sostener? | No | Ritmo y priorización |
| C9 | ¿Cada cuántos días quieres que te pregunte si hay cambios en tu experiencia, CV o configuración? | No (por defecto 15, 30 y 60 días, D15) | Recordatorios |
| C10 | ¿En qué portales tienes cuenta y en cuáles autorizas que el agente postule? | No | Navegación (D4). El consentimiento por portal se pide igual antes de la primera acción |
| C11 | ¿Dónde están tu CV actual y tu foto, si la usas? | No | CV base |
| C12 | ¿Ya postulaste a algo o tienes procesos en curso? (empresa, cargo, fecha, estado) | No | Antiduplicación, historial |

---

## 3. Actualizar perfil

Amplía la operación 1 "Actualizar experiencia" del flujo: pasa a llamarse **Actualizar perfil** y mantiene el recordatorio `(*)` cada `X` días (preguntar, nunca modificar solo). Se enfoca en la experiencia reciente; intereses y configuración siguen en "Actualizar configuración".

**Entrada**: el agente muestra la fecha de la última revisión y ofrece dos caminos.

- **Cuéntame (relato libre)**: el usuario cuenta lo que ha hecho desde la última revisión, con sus propias palabras. El agente extrae datos candidatos (cargo, responsabilidad, logro, cifra, herramienta, proyecto, certificación), los presenta uno a uno y el usuario confirma, corrige o descarta.
- **Pregúntame (guiado)**: el agente hace preguntas de profundización, una a la vez, empezando por lo que más ha cambiado.

**Banco de profundización** (se usa sobre todo en "Pregúntame"; el agente elige según lo que el perfil tiene débil):

| ID | Pregunta |
|---|---|
| P1 | ¿Qué cambió en tu trabajo desde la última revisión? ¿Nuevo cargo, equipo, alcance o responsabilidad? |
| P2 | ¿Qué lograste que puedas respaldar? ¿Con qué cifra, cómo se midió y de dónde sale? |
| P3 | ¿Qué herramientas o técnicas usaste por primera vez, y a qué nivel? |
| P4 | ¿Algún proyecto cambió de estado (de desarrollo a productivo, o se descontinuó)? ¿Hay proyectos nuevos? |
| P5 | ¿Cambió el número de personas que coordinas o a cargo, o tu responsabilidad sobre presupuesto? |
| P6 | ¿Hiciste cursos o certificaciones nuevos? |
| P7 | ¿Hay algo en tu perfil que ya no es cierto o que quieras matizar? |
| P8 | ¿Quieres corregir algo que haya salido en un CV o respuesta enviada? |

**Detección de vacíos**: el agente también pregunta por lo que el perfil tiene débil sin que el usuario lo pida: logros sin cifra o sin fuente, proyectos sin estado, cifras sin método, datos `por_confirmar` abiertos, contradicciones sin resolver y datos más antiguos que el plazo de revisión.

**Reglas**:

- Solo se guarda lo confirmado, con fecha y fuente. No se infieren cifras ni se completan datos.
- Si un dato nuevo contradice uno existente, el agente muestra ambos y el usuario decide cuál queda; no se pisa en silencio.
- Un cambio relevante puede sugerir revisar el CV base (operación 4): el agente pregunta, no modifica el CV por su cuenta.
- Lo que el usuario dice que es contexto de su trabajo y no material de CV va al diario (`diario.md`), no a `perfil.md`; solo entra al perfil si el usuario lo marca como hito.
- Un md previo es insumo, no verdad: se confirma dato por dato, y lo que el usuario niega (por ejemplo, un idioma) se registra para no reutilizarlo.
- Al terminar, guarda la fecha de revisión y un resumen de lo que cambió.
