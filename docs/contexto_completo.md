# Contexto completo — Agente0 (agente de búsqueda laboral)

Última consolidación: 2026-11-15.
Complementa a `CLAUDE.md` (reglas operativas cortas). Aquí está el detalle del diseño del agente, que es para **cualquier persona** que quiera usarlo. Los datos de cada usuario viven aparte, en el directorio de datos de cada persona (`$AGENTE0_DATOS`, fuera del repo); el del usuario 1 parte de `$AGENTE0_DATOS/origen/` (material de partida).

Fuente de requisitos: `solo_lectura/flujo_agente_busqueda_laboral.md` v1.1 (diagrama manuscrito del 14-nov-2026 más dos requisitos del 15-nov-2026). Es la especificación funcional; no es una arquitectura técnica ni un sistema implementado. Antecedentes: `solo_lectura/agente.md`, `buscador.md`, `cv.md`, `about_me.md` (trabajo previo del usuario 1 en ChatGPT); sirven como insumo de diseño, no como requisitos.

Etiquetas de certeza: **esquema** (está en el manuscrito), **confirmado** (lo pidió el usuario después), **propuesta** (idea de especificación, no aprobada), **pendiente**.

---

## 1. Qué es el agente

Un agente que apoya y automatiza el proceso de búsqueda laboral de un usuario: mantiene su perfil al día, gestiona oportunidades de empleo, personaliza el CV para cada vacante, asiste o ejecuta las postulaciones y conserva el estado y el detalle de cada proceso. Además aprende de los resultados reales y el usuario decide cuánto delega.

Principios:

1. **Multiusuario**: ningún dato personal queda en reglas, prompts o código. Todo dato de un usuario vive en su perfil y no se mezcla con el de otro.
2. **Veracidad**: no se inventa experiencia, renta, certificaciones ni resultados, en ningún nivel de autonomía.
3. **Delegación controlada**: el usuario fija cuánto hace el agente solo.
4. **Trazabilidad**: se guarda exactamente qué se envió, con qué CV, con qué respuestas y bajo qué política.
5. **Aprendizaje sin causalidad**: los resultados informan recomendaciones, no prueban qué respuesta funcionó.
6. **Preguntar antes de modificar** el perfil o las preferencias del usuario.

---

## 2. Flujo general

El diagrama completo (Mermaid) está en `solo_lectura/flujo_agente_busqueda_laboral.md` §2. Resumen:

1. **Inicio**: ¿primera vez? Sí: onboarding. No: menú de operaciones habituales.
2. **Onboarding** (esquema): registrar experiencia, intereses y configuración inicial (incluye el nivel de autonomía). Continuar al menú es una propuesta; el manuscrito no lo detalla. Banco de preguntas y reglas en `docs/onboarding.md` (D6).
3. **Operaciones habituales** (esquema, seis):
   1. Actualizar perfil `(*)` (en el esquema, "Actualizar experiencia"; ampliada en D6).
   2. Actualizar postulaciones potenciales, que lleva al subflujo de postulación.
   3. Actualizar el estado de una postulación.
   4. Investigar mejores formas de crear el CV para ATS y éxito, y actualizar el CV base `(*)`.
   5. Actualizar configuración `(*)`, incluida la autonomía.
   6. Editar respuestas tipo `(**)`.
4. **Subflujo de postulación**: para cada empleo potencial, de mayor a menor prioridad: adaptar el CV base, aplicar la política de autonomía, postular por navegación web con respuestas tipo, actualizar el estado a "postulado", guardar el detalle.

Marcas del manuscrito:

- `(*)`: preguntar cada **X días** si se desea actualizar (recomendado). `X` no está definido.
- `(**)`: usar las respuestas tipo (base).

No está definido si las operaciones se ejecutan a demanda, programadas o de ambas formas.

---

## 3. Onboarding

Datos propuestos (el manuscrito solo nombra los tres bloques):

| Bloque | Datos posibles | Uso posterior |
|---|---|---|
| Experiencia | Cargos, empresas, períodos, logros comprobables, formación, capacidades, herramientas | Construir y adaptar el CV sin inventar |
| Intereses | Roles objetivo, sectores, funciones, nivel de responsabilidad, modalidad | Identificar y priorizar empleos |
| Configuración inicial | Expectativa de sueldo, ubicación, restricciones, frecuencia `X` de recordatorios, preferencias de postulación, nivel de autonomía | Filtrar oportunidades, decidir aprobaciones, controlar al agente |

Detección de primera vez (propuesta): si no existe un perfil base suficientemente inicializado, se inicia el onboarding. Resultado: perfil base disponible para las demás operaciones.

Para un usuario con material previo (como el usuario 1), el onboarding puede partir de sus documentos, pero cada dato se confirma antes de entrar al perfil.

**D6 (2026-11-15)**: el modo general es por preguntas (banco en `docs/onboarding.md`, una a la vez); el usuario 1 usa el modo con documentos, con una hoja pre-llenada (`$AGENTE0_DATOS/origen/` (hoja de onboarding)). La primera vez se detecta con la marca `onboarding_completo`; el onboarding se retoma si se interrumpe; la autonomía por defecto es 0 %.

---

## 4. Operaciones habituales

### 4.1. Actualizar perfil `(*)`

Recuperar la experiencia guardada; preguntar qué cambió; incorporar solo cambios confirmados (cargos, responsabilidades, logros, proyectos, formación, herramientas); guardar con fecha de revisión. Un cambio relevante puede alimentar una revisión del CV base (inferencia, no flecha del dibujo).

Ampliada en D6 (2026-11-15; en el esquema se llama "Actualizar experiencia"): dos caminos, "Cuéntame" (relato libre del usuario, el agente extrae datos y se confirman uno a uno) y "Pregúntame" (preguntas de profundización sobre la experiencia reciente), más detección de vacíos del perfil. Detalle y banco de preguntas en `docs/onboarding.md` §3.

### 4.2. Actualizar postulaciones potenciales

Recuperar la lista vigente; incorporar oportunidades nuevas y actualizar las existentes; revisar cuáles siguen vigentes; ordenar por prioridad; preparar el conjunto que entra al subflujo de postulación.

**Fuentes (D10, 2026-11-15)**: búsqueda web primero y navegador solo donde hace falta; lista de fuentes por usuario y país con método, riesgo y estado; a demanda (con sugerencia si pasaron más de 3 días); ventana de 30 a 45 días; vigencia verificada en la fuente oficial; duplicados unidos en un solo empleo potencial. Detalle en `decisiones.md`.

**Priorización (D11, 2026-11-15)**: puntaje ponderado con dos ejes visibles, "lo que quiero" (45 %) y "lo que tengo" (55 %), más el total que ordena la lista; filtros excluyentes antes de puntuar; estabilidad entre actualizaciones (cada puntaje guarda su evidencia y no cambia sin evidencia nueva); tabla con desglose por criterio y cambios respecto de la lista anterior. Detalle en `decisiones.md`.

**Inicio de postulaciones (D13, 2026-11-15)**: al terminar de mostrar el ranking, el subflujo parte solo con las vacantes del Top 10 en estado `POTENCIAL`, de mayor a menor puntaje y hasta el límite diario del portal, de a una. Al 0 % se confirma el inicio de cada vacante; desde el 25 % el agente prepara solo y el nivel (D12) decide qué se aprueba. El usuario puede saltar o descartar una vacante. Detalle en `decisiones.md`.

### 4.3. Actualizar el estado de una postulación

Esquema: actualizar el estado cuando algo cambia (ejemplo: "pasé a la siguiente entrevista"). Confirmado: un hito positivo produce **dos efectos**, uno operativo y uno de aprendizaje (§6).

Pasos propuestos:

1. Identificar sin ambigüedad la postulación afectada (pedir solo lo necesario si hay duda).
2. Obtener su estado actual y el registro original: CV enviado, preguntas, respuestas efectivamente enviadas, fechas.
3. Registrar el evento con fecha, descripción y evidencia (ejemplo: `PRIMER_CONTACTO_ENTREVISTA`).
4. Actualizar el estado y guardar el historial de transiciones.
5. Si es un hito positivo definido y no fue recompensado antes, crear el evento de recompensa (§6).

Catálogo (D5, 2026-11-15; detalle en `decisiones.md`):

- Empleo potencial: `POTENCIAL`, `EN_POSTULACION`, `CERRADO`, `DESCARTADO` (con motivo).
- Postulación: `PREPARADA` → `ENVIO_INTENTADO` → `POSTULADO` → `EN_PROCESO` (campo `etapa`) → `FINALIZADA` (campo `resultado`).
- Eventos tipados: `PRIMER_CONTACTO_ENTREVISTA`, `ENTREVISTA_REALIZADA`, `NUEVA_ETAPA`, `OFERTA_RECIBIDA`, `RECHAZO`, `RETIRO`, `CIERRE_POR_SILENCIO`.
- Sin retrocesos, salvo corrección registrada por el usuario; `ENVIO_INTENTADO` → `PREPARADA` solo si el envío falló sin enviarse.
- Una oportunidad termina cuando el empleo pasa a `CERRADO` o `DESCARTADO`, o la postulación llega a `FINALIZADA`. El agente puede proponer cerrar por silencio, nunca cierra solo.

### 4.4. Investigar mejoras del CV y actualizar el CV base `(*)`

Esquema: investigar cómo preparar el CV para ATS y para elevar el éxito, y luego actualizar el CV base.

Pasos propuestos: revisar prácticas vigentes de legibilidad y compatibilidad ATS; evaluar mejoras al diseño y al contenido; separar mejoras generales del CV base de ajustes por vacante; proponer cambios sin atribuir al usuario nada que no tenga; actualizar el CV base con cambios verificados o aprobados; conservar versiones para comparar y revertir.

Distinción clave: **CV base** (documento maestro con información validada) y **CV adaptado** (derivado del base para una vacante). Formato y estrategia de versiones: pendientes.

### 4.5. Actualizar configuración `(*)`

Esquema: modificar la configuración (ejemplo: expectativas de sueldo). Confirmado: también permite configurar el **nivel de autonomía** (§7).

Pasos propuestos: mostrar parámetros vigentes; preguntar por cambios; actualizar solo lo afectado; aplicar a futuras búsquedas y postulaciones; registrar la fecha; si cambia la autonomía, aplicarla a acciones futuras y pasos pendientes sin autorizar retroactivamente envíos ya hechos; mostrar una vista previa de qué acciones requerirán aprobación.

Parámetros nuevos: `nivel_autonomia` (0–100 %), políticas de aprobación por acción y, opcionalmente, excepciones por sitio o tipo de postulación.

### 4.6. Editar respuestas tipo `(**)`

Biblioteca de respuestas reutilizables (ejemplos: pretensión de renta, disponibilidad, motivación, experiencia con tecnologías, modalidad, nivel de inglés). El manuscrito no enumera cuáles son.

Comportamiento propuesto:

1. Mantener la biblioteca y permitir editarla cuando cambien los antecedentes.
2. Recuperar la respuesta relevante al completar un formulario y ajustarla al contexto sin contradecir el perfil.
3. Si una pregunta no se puede responder con información confirmada, pedir intervención.
4. Versionar la respuesta efectivamente usada (texto exacto, contexto, fecha, vacante). El aprendizaje se refiere a esa versión y no modifica en silencio la respuesta base.
5. Con antecedentes positivos en postulaciones comparables, proponer primero las respuestas con buen historial, respetando la autonomía.

**D9 (2026-11-15)**: una respuesta vigente por categoría, con versiones sucesivas, ID estable y campo `variante` opcional. Categorías de hechos y narrativas, y lista de preguntas que exigen respuesta nueva, en `decisiones.md`. Sin respuesta confirmada, la postulación queda en cola de aprobación, incluso al 100 %.

---

## 5. Subflujo de postulación

Se repite por cada empleo potencial, de mayor a menor prioridad ("de > a <" en el manuscrito; el criterio de prioridad no está definido).

### 5.1. Paso 0: adaptar el CV base

Recuperar el CV base y la descripción del empleo; identificar requisitos y términos relevantes; destacar la experiencia real más pertinente; ajustar orden, resumen, énfasis y redacción; generar una versión identificable; verificar que no haya afirmaciones sin respaldo y que el formato sea legible. Entrada: CV base y vacante. Salida: CV para esa vacante.

**Carta de presentación (D8, 2026-11-15)**: no es parte del paso 0. Se genera solo si el formulario la exige o el usuario la pide para una vacante; si el campo es opcional, no se genera. Pasa por la compuerta de autonomía y las mismas reglas de veracidad que el CV. Reglas de forma y tono en `decisiones.md`.

### 5.2. Compuerta de autonomía

Antes de elegir respuestas, adaptar contenido, cargar documentos o enviar, se aplica la política de autonomía vigente (§7).

### 5.3. Paso 1: postular por navegación web con respuestas tipo

Abrir la página de postulación; completar campos con datos confirmados; usar respuestas tipo como punto de partida; adjuntar el CV adaptado y los archivos requeridos; revisar consistencia; enviar si hay autorización aplicable; obtener la confirmación del sitio si existe.

Regla propuesta: distinguir **formulario preparado**, **envío intentado** y **envío confirmado**. Completar un formulario no es haber postulado.

**Errores y reintentos (D14, 2026-11-15)**: `POSTULADO` exige una confirmación visible del sitio (mensaje, número o pantalla de gracias), guardada como captura y texto. Sin confirmación clara queda `ENVIO_INTENTADO` y se verifica en el portal o el correo antes de cualquier reintento; si no se puede verificar, se pide intervención y no se reenvía solo. Publicación cerrada → `CERRADO`; formulario incompleto o error de acceso previo al envío → `PREPARADA`. El reintento usa el mismo ID y cada intento queda como evento. Detalle en `decisiones.md`.

### 5.4. Paso 2: estado "postulado"

Solo con evidencia suficiente de que el envío ocurrió. Si hubo error o falta confirmación, conservar un estado intermedio o registrar la incidencia.

### 5.5. Paso 3: guardar el detalle

Campos propuestos: identificador, empresa, cargo, enlace, descripción (requisitos y responsabilidades), prioridad, fecha de postulación, estado, CV utilizado, **respuestas utilizadas** (texto exacto, pregunta, identificador y versión), evidencia (número de confirmación, captura, mensaje), historial, feedback de resultados, observaciones, y el nivel de autonomía y la aprobación bajo los que se ejecutó.

La postulación conserva una **instantánea histórica** de lo enviado, aunque después cambien el CV base o las respuestas tipo.

### 5.6. Repetición

Al terminar una vacante se pasa a la siguiente, con registro de cuáles se procesaron. Una oportunidad ya postulada no se vuelve a postular sin instrucción expresa.

---

## 6. Aprendizaje a partir de resultados (confirmado)

**Objetivo**: responder "¿qué respuestas o estrategias formaron parte de postulaciones con resultado positivo en oportunidades parecidas?".

**Disparador confirmado**: el usuario informa que lo contactaron para una primera entrevista.

Secuencia:

1. Identificar la postulación.
2. Registrar el evento `PRIMER_CONTACTO_ENTREVISTA` y cambiar el estado de `POSTULADO` a `EN_PROCESO` con etapa "primera entrevista"; guardar fecha y notas.
3. Recuperar el registro inmutable de las preguntas y respuestas realmente enviadas.
4. Crear **un solo** evento de recompensa. Un mismo contacto no puede dar el premio dos veces aunque el usuario repita el aviso o el agente reprocese el evento.
5. Asociar la señal positiva al conjunto de respuestas enviadas, y a la estrategia completa si se implementa.
6. Usar la señal en recomendaciones para contextos comparables.

| Elemento | Tratamiento |
|---|---|
| Respuestas enviadas | Reciben feedback positivo ligado a su versión original |
| Biblioteca de respuestas tipo | Sube la preferencia por variantes con señales positivas en contextos parecidos |
| CV adaptado | Se registra como contexto del caso; premiarlo por separado requiere una decisión adicional |
| Habilidad o experiencia del usuario | No cambia por un resultado |
| Respuestas no enviadas | No reciben premio |
| Postulaciones sin respuesta | No se penalizan automáticamente |
| Rechazos | Sin castigo automático (D16) |

**Puntuación inicial (propuesta)**: guardar por respuesta y contexto dos variables, usos confirmados y contactos positivos observados. Ejemplo: `reward = +1` por evento de primera entrevista (valor ilustrativo y configurable). Puede empezar con estadísticas y reglas, sin modelo de ML. Una respuesta con un caso exitoso no debe superar a otra con veinte usos comparables: considerar volumen, fecha, similitud de contexto e incertidumbre.

**Contexto de comparación**: pregunta y categoría, texto literal, empresa, cargo, seniority, industria, requisitos, fecha, portal, versión del CV y resultado con su fecha.

**No atribución causal**: la entrevista puede depender de la trayectoria, la empresa, el CV, el mercado, el reclutador. El agente no afirma que una respuesta aislada "funcionó".

**D16 (2026-11-15)**: solo `PRIMER_CONTACTO_ENTREVISTA` puntúa (+1, configurable); los demás hitos se registran como eventos pero no puntúan. Tasa suavizada por versión de respuesta (ID y versión) y contexto, con la tasa base del usuario como punto de partida (peso de 5 usos virtuales); se recomienda con al menos 8 usos comparables y puntaje sobre la línea base, y si no, solo se muestran los datos con "pocos datos". Rechazos y silencio no generan puntaje negativo; un uso entra a la tasa cuando se resolvió o pasó la ventana de 30 días. Detalle en `decisiones.md`.

**Medición (D17, 2026-11-15)**: comparación antes y después con línea base propia (las primeras ventanas, sin recomendaciones), en ventanas de 4 a 6 semanas desde el envío confirmado. Indicadores: primeros contactos de entrevista por hora de esfuerzo del usuario (horas declaradas en la revisión semanal) y tasa de contacto por postulación confirmada. Se reporta con el número de envíos y de contactos; con menos de 5 contactos, "sin conclusión". Nunca se afirma causalidad. Detalle en `decisiones.md`.

**Criterios de aceptación**:

- El estado cambia correctamente al informar el contacto.
- Se crea un solo evento de recompensa por hito.
- Se premian exactamente las respuestas enviadas, no las de otros procesos ni las no enviadas.
- El agente puede explicar qué evidencia respalda una recomendación.
- La puntuación no modifica el perfil profesional ni introduce datos falsos.

---

## 7. Autonomía configurable (confirmado)

El parámetro `nivel_autonomia` va de 0 a 100 %. Mide cuánto delega el usuario, no la probabilidad de éxito ni la capacidad de saltarse restricciones de una plataforma.

| Nivel (orientativo, pendiente de validar) | Comportamiento |
|---|---|
| 0 % manual | Confirmar cada acción y cada respuesta |
| 25 % asistido | Investigar y preparar solo; aprobar CV, respuestas y envíos |
| 50 % supervisado | Buscar y adaptar solo; revisar respuestas sensibles y el envío final |
| 75 % delegado | Hacer la mayor parte; intervención solo ante excepciones definidas |
| 100 % autónomo | Flujo íntegro dentro de permisos y límites, sin aprobaciones rutinarias |

No hay fórmula para los niveles intermedios; se recomienda acompañar el porcentaje con permisos explícitos por acción.

| Acción | Autonomía baja | Autonomía alta |
|---|---|---|
| Encontrar vacantes | Propone fuentes y búsquedas para aprobar | Busca según los intereses |
| Priorizar | Muestra ranking y espera selección | Ordena con criterios definidos |
| CV adaptado | Muestra la versión para aprobar | Genera y usa una versión coherente con el perfil |
| Responder preguntas | Valida cada respuesta | Elige y adapta con evidencia suficiente |
| Completar formulario | Confirma campos y documentos | Completa con datos verificados |
| Enviar | Confirmación explícita | Envía dentro de la delegación otorgada |
| Guardar estado y detalle | Muestra cambios para revisión | Registra eventos confirmados |
| Reforzar respuestas | Muestra la señal de aprendizaje | La registra con trazabilidad |

Reglas transversales:

1. El usuario consulta y cambia la autonomía cuando quiera.
2. Antes de activar autonomía total, se le comunica exactamente qué acciones externas podrá hacer el agente, incluido enviar postulaciones.
3. Ningún nivel autoriza inventar experiencia, renta, certificaciones u otros antecedentes.
4. Ante CAPTCHA, fallas de autenticación, términos de un sitio, campos imposibles o preguntas sin evidencia suficiente, el agente **pausa esa acción y pide intervención, incluso al 100 %**.
5. Cambiar la autonomía afecta lo pendiente y lo futuro; no revierte envíos ya hechos.
6. Se registra qué se ejecutó, con qué nivel, qué información se usó y si hubo aprobación humana.
7. La autonomía no habilita reenviar una postulación ya completada.
8. La autonomía es una preferencia de producto: no sustituye permisos de acceso a portales, cuentas ni herramientas.

**D12 (2026-11-15)**: se elige el modelo de niveles fijos (0, 25, 50, 75 y 100 %), con condiciones de auto-envío al 75 %, reglas siempre vigentes en todo nivel, excepciones por portal o empresa, tope de nivel por portal, límites diarios por riesgo de portal (alto 3, medio 5, bajo 8; pausa mínima de 2 minutos), vista previa, aviso antes de activar 100 % y registro de lo automático y lo aprobado. Los valores intermedios se redondean hacia abajo. Las tablas de arriba son el punto de partida; el detalle vigente está en `decisiones.md`.

Criterios de aceptación: configurable desde el onboarding y desde "Actualizar configuración"; con el mínimo, el agente espera confirmación de cada respuesta y acción relevante; al 100 %, no pide aprobaciones rutinarias y notifica incidencias; los cambios se aplican a lo aún no ejecutado; el registro de cada postulación muestra qué fue automático y qué aprobado.

---

## 8. Recordatorios

- `(*)`: cada `X` días preguntar si se quiere actualizar experiencia, CV base y configuración. Aceptar, posponer o descartar. Se recomienda **preguntar, no modificar** por cuenta propia.
- **D15 (2026-11-15)**: un `X` por caso, medido desde la última vez que se realizó la operación: experiencia 15 días, CV base 30, configuración 60. Se revisa al abrir el menú, con una pregunta por caso vencido. Posponer reaparece a los 7 días; descartar reinicia el reloj con el `X` completo; nunca bloquea el menú ni modifica nada solo. Configurables por el usuario. Detalle en `decisiones.md`.
- `(**)`: las respuestas tipo son una base reutilizable; no reemplazan verificar que cada una aplica a la pregunta concreta.

---

## 9. Entidades de datos (propuesta de modelado)

| Entidad | Propósito |
|---|---|
| Usuario y perfil profesional | Experiencia verificada; alimenta el CV base y los formularios |
| Intereses | Qué empleos se buscan |
| Configuración | Parámetros y preferencias, incluida la `X` de recordatorios |
| Política de autonomía | Nivel 0–100 %, permisos y excepciones |
| CV base | Documento maestro versionado |
| CV adaptado | Derivado del base para una vacante |
| Respuestas tipo | Biblioteca versionada |
| Empleo potencial | Oportunidad identificada y priorizada |
| Postulación | Intento o envío confirmado; tiene estado, detalle e historial |
| Evento de estado | Cambio documentado de una postulación |
| Instantánea de respuesta enviada | Pregunta y texto literal, contexto y versión |
| Evento de recompensa | Señal positiva deduplicada, ligada a un evento de estado |
| Estadísticas por respuesta y contexto | Usos, señales positivas, similitud |
| Recordatorio | Revisión periódica pendiente |

Son nombres sugeridos; no son tablas ni componentes definidos por el autor del esquema.

**Estructura en disco (B1, 2026-11-15)**: una carpeta por persona, indicada por `AGENTE0_DATOS` (sugerida `Agente0_datos/<usuario>/`, junto al repo), fuera del repo. `python -m agente0 init` crea las carpetas y `configuracion.json` con valores por defecto, sin pisar lo existente. El resto de los archivos lo crea la operación que los usa.

```
$AGENTE0_DATOS/
  perfil/
    perfil.md, intereses.md        (B2: solo lo confirmado; perfil.md incluye también las respuestas de configuración inicial C1 a C12 hasta que B6 y B11 definan su esquema)
    diario.md                      (B15: diario de vida laboral; contexto fechado que no entra al CV ni a formularios salvo que el usuario lo promueva a perfil.md)
    revisiones_perfil.jsonl        (B15: append-only, una línea por revisión de "Actualizar perfil"; su última fecha es el reloj del recordatorio de experiencia)
  configuracion/
    configuracion.json             (autonomía, X de recordatorios, posponer; después umbrales y límites por portal)
    recordatorios.json             (B10)
  empleos/empleos.csv              (B6: potenciales; columna postulacion_id)
  cv/base/<fecha>/                 (B3: .tex, PDF ATS y visual, limites.json, auditoría de veracidad)
  respuestas/<categoria>/v001_<fecha>.md
  postulaciones/<id>/              (B4)
    postulacion.json               (estado actual)
    eventos.jsonl                  (append-only, incluye recompensas)
    cv/                            (CV adaptado)
    instantanea/                   (inmutable: CV, preguntas, respuestas literales, evidencia)
    estadisticas.json              (derivable, recalculable)
  origen/                          (material de partida del onboarding, no confirmado)
  respaldos/                       (copias de seguridad que el usuario quiera guardar)
```

ID de postulación: `<empresa>-<cargo>-<hash de 6 caracteres de la URL canónica>`. La misma vacante da el mismo ID aunque se detecte otro día o con parámetros de seguimiento; la URL se normaliza (minúsculas, sin barra final ni fragmento, sin `utm_*`).

---

## 10. Reglas de negocio consolidadas

Del esquema y de las ampliaciones confirmadas: onboarding en la primera vez; seis operaciones habituales; mantener oportunidades, estados y respuestas tipo; investigar mejoras de CV para ATS; recorrer empleos de mayor a menor prioridad; adaptar el CV antes de postular; postular por navegación web con respuestas tipo; actualizar a "postulado" y guardar el detalle; preguntar cada `X` días; **[confirmado]** al informar el primer contacto de entrevista, actualizar el estado y premiar las respuestas enviadas; **[confirmado]** autonomía configurable de 0 a 100 %.

Recomendadas (no están en el esquema): veracidad; trazabilidad de CV y evidencia; no marcar "postulado" sin confirmación; antiduplicación; definir cuándo el agente puede enviar; separar publicaciones cerradas, formularios incompletos, errores de acceso y envíos exitosos; persistencia para reanudar; protección de datos personales y credenciales; recompensas ligadas a un resultado real y a la instantánea enviada; idempotencia del aprendizaje; delegación explícita.

---

## 11. Decisiones de diseño

Las 18 decisiones de la Fase 1 están cerradas (2026-11-15). Cada una se presentó con 2 opciones y tradeoffs y se cerró con la confirmación del usuario 1. Una decisión cerrada se reabre solo por la condición que trae registrada en `decisiones.md`.

**Cerradas** (detalle en `decisiones.md`):
- Forma de ejecución (D1, 2026-11-15): agente sobre Claude Code, a demanda, con una skill por operación, archivos locales por usuario y la extensión de Chrome.
- Persistencia (D2, 2026-11-15): archivos locales por usuario, un archivo por entidad, ID estable por postulación, instantáneas inmutables y versiones en carpetas con fecha.
- Aislamiento entre usuarios (D3, 2026-11-15): una instalación por persona, datos fuera del repo, sin credenciales en archivos y consentimiento antes de la primera acción externa por portal. Ruta fijada en B1: variable `AGENTE0_DATOS`, una carpeta por persona (§9). El aprendizaje entre usuarios (D18) solo puede ser opt-in.
- Plataforma de navegación (D4, 2026-11-15): extensión de Chrome sobre el Chrome real y la sesión del usuario. Ante CAPTCHA, login, 2FA, términos o campos imposibles el agente pausa y pide intervención, incluso al 100 %. Portales clasificados por riesgo de bloqueo, envíos sin ráfagas y con límite diario por portal (valores en D12; clasificación del usuario 1 en `$AGENTE0_DATOS/origen/` (material de partida) §8.4, U5). El agente puede sugerir portales nuevos según el perfil e invitar al usuario a crear la cuenta; nunca la crea él.
- Aprendizaje entre usuarios (D18, 2026-11-15): opt-in apagado por defecto, con señales agregadas y anonimizadas (solo conteos por categoría de respuesta y familia de cargo, nunca texto literal ni datos del usuario). Exige un almacén central que hoy no existe: su mecanismo queda pendiente y reabre D1 y D3 al construirlo.
- Medición del aprendizaje (D17, 2026-11-15): antes y después con línea base propia en ventanas de 4 a 6 semanas; contactos por hora de esfuerzo y tasa de contacto; "sin conclusión" con menos de 5 contactos; sin afirmar causalidad.
- Recompensa (D16, 2026-11-15): solo la primera entrevista puntúa (+1); tasa suavizada desde la tasa base del usuario, umbral de 8 usos comparables para recomendar y sin castigo por rechazo ni silencio. Los demás hitos se registran como eventos y no puntúan.
- Recordatorios (D15, 2026-11-15): un `X` por caso medido desde la última vez que se hizo la operación (experiencia 15, CV base 30, configuración 60 días); posponer a 7 días, descartar reinicia el reloj; nunca bloquea ni modifica solo.
- Errores y reintentos (D14, 2026-11-15): la confirmación visible del sitio basta para `POSTULADO`; sin ella, `ENVIO_INTENTADO` y verificación en el portal o el correo antes de reintentar; mismo ID por reintento y nunca reenviar sin verificar.
- Inicio de postulaciones (D13, 2026-11-15): el subflujo parte solo tras el ranking según el nivel de autonomía, con el Top 10 en orden de puntaje y hasta el límite diario; el usuario puede saltar o descartar vacantes. Sin selección previa obligatoria.
- Autonomía (D12, 2026-11-15): niveles fijos 0, 25, 50, 75 y 100 %, con condiciones de auto-envío al 75 %, reglas siempre vigentes, excepciones y tope de nivel por portal, límites diarios por riesgo, vista previa y aviso antes de activar 100 %.
- Priorización (D11, 2026-11-15): puntaje ponderado con los ejes "quiero" y "tengo" siempre visibles por separado, filtros excluyentes antes de puntuar y estabilidad por evidencia; el umbral de match de autonomía se define por eje.
- Fuentes de empleos y periodicidad (D10, 2026-11-15): búsqueda web primero y navegador solo para portales que lo exigen y para verificar vigencia; lista por usuario y país; a demanda; vigencia en la fuente oficial.
- Respuestas tipo (D9, 2026-11-15): una respuesta vigente por categoría con versiones sucesivas; categorías de hechos y narrativas; preguntas que exigen respuesta nueva; sin respuesta confirmada, cola de aprobación incluso al 100 %.
- Carta de presentación (D8, 2026-11-15): solo cuando el formulario la exige o el usuario la pide; no es parte del paso 0. Mismas reglas de veracidad y compuerta de autonomía que el CV.
- Formato de CV (D7, 2026-11-15): LaTeX como maestro con dos salidas a PDF (visual y ATS de una columna), variantes por vacante con render revisado, versiones en carpetas con fecha y auditoría de veracidad antes de cada envío. DOCX solo si un canal lo exige. Requiere instalar XeLaTeX (B3).
- Onboarding (D6, 2026-11-15): modo general por preguntas (banco en `docs/onboarding.md`), modo con documentos para el usuario 1, solo entra al perfil lo confirmado, autonomía 0 % por defecto. La operación 1 pasa a "Actualizar perfil", con "Cuéntame" y "Pregúntame".
- Estados y cierre (D5, 2026-11-15): pocos estados y el detalle en eventos tipados (catálogo en §4.3). `CONTACTADO_PRIMERA_ENTREVISTA` es el evento `PRIMER_CONTACTO_ENTREVISTA`; hoy es el único elegible para recompensa (D16 decide el resto). El silencio no se castiga ni cierra solo.

---

## 12. Casos de uso de extremo a extremo

- **A. Usuario nuevo**: inicia, el sistema detecta la primera vez, hace el onboarding y habilita las operaciones habituales.
- **B. Actualizar oportunidades y postular**: se actualiza la lista, se ordena, y por cada empleo se adapta el CV, se postula por navegación web con respuestas tipo, se confirma el envío, se pasa a "postulado" y se guarda el detalle.
- **C. Avance de entrevista**: el usuario informa un avance; se localiza la postulación, se actualiza el estado con historial, se recuperan las respuestas efectivamente enviadas y, si es un hito elegible, se premian de forma deduplicada para usarlas en postulaciones comparables.
- **D. Revisión periódica**: pasan `X` días; el agente pregunta si se actualiza el elemento; el usuario confirma o declina.
- **E. Autonomía mínima vs total**: con mínima el agente muestra cada respuesta y acción y espera aprobación; con 100 % ejecuta lo permitido y registra. En ambos, una respuesta desconocida, un bloqueo del sitio o falta de autorización puede requerir al usuario.

---

## 13. Antecedente: proyecto Career Agent (ChatGPT)

Trabajo previo del usuario 1, solo como insumo. Definió cinco módulos que se corresponden con el flujo actual:

| Módulo previo | Equivalente en el flujo v1.1 |
|---|---|
| M1 Career Knowledge Base | Perfil profesional y "Actualizar experiencia" |
| M2 Job Radar | "Actualizar postulaciones potenciales" |
| M3 CV Engine | "Paso 0" del subflujo y "Investigar mejoras del CV" |
| M4 Application Manager | "Actualizar estado" y "Guardar detalle" |
| M5 Learning Engine | Aprendizaje por resultados (§6) |

Diferencias a tener presentes: el proyecto previo dejaba al usuario 1 como quien valida y postula; el flujo v1.1 lo vuelve un parámetro. El previo era de un solo usuario; el actual es multiusuario. El previo medía como KPI las entrevistas relevantes por hora de esfuerzo del usuario (2–3 h semanales), un buen indicador de producto a conservar. Su cronograma de seis semanas y su avance de 64 % son históricos y no aplican a este proyecto.

Filosofía heredada (consistente con las preferencias del usuario 1): ir de menos a más. Una versión mínima que haga el flujo con un usuario antes de construir infraestructura para muchos.

---

## 14. Riesgos

- **Plataformas**: muchos portales prohíben o restringen la automatización y usan CAPTCHA. El envío automático puede ser bloqueado y poner en riesgo la cuenta del usuario.
- **Datos personales**: CV, documentos y credenciales de varios usuarios. Hay que aislarlos y no guardar credenciales en archivos del repositorio.
- **Veracidad a escala**: sin revisión humana, un error de respuesta se repite en muchas postulaciones.
- **Duplicación**: reintentos tras fallas pueden generar postulaciones repetidas.
- **Aprendizaje con pocos datos**: las señales por respuesta y contexto serán escasas al principio; no sobreinterpretar.
- **Causalidad**: confundir asociación con efecto lleva a recomendar respuestas que no aportan.

---

## 15. Glosario

- **ATS**: sistema de seguimiento de candidatos que lee y filtra CV.
- **CV base / CV adaptado**: documento maestro y su derivado por vacante.
- **Respuestas tipo**: biblioteca de respuestas reutilizables para formularios.
- **Hito positivo**: resultado que dispara una recompensa (hoy, contacto para primera entrevista).
- **Instantánea**: copia inmutable de lo que se envió en una postulación.
- **Autonomía**: grado de delegación del usuario, de 0 a 100 %.
- **`X`**: tiempo transcurrido desde la última vez que se hizo una operación `(*)` a partir del cual se sugiere repetirla; 15, 30 y 60 días según el caso (D15).
