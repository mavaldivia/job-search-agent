# Agente0 — Agente de búsqueda laboral (multiusuario)

Agente que apoya y automatiza la búsqueda laboral de **cualquier persona** que quiera usarlo. Mantiene el perfil del usuario, gestiona oportunidades, adapta el CV por vacante, asiste o ejecuta las postulaciones, registra el estado de cada proceso y aprende de los resultados reales. El usuario decide cuánto delega.

Estado: especificación funcional y decisiones de diseño cerradas (D1 a D18). Construcción en curso: B1 (estructura base), B2 (onboarding del usuario 1), U6 (biblioteca de respuestas tipo aprobada), B15 (Actualizar perfil, skill `actualizar_perfil`) y B4 (registro de postulaciones, sin carga del historial previo) y B5 (biblioteca de respuestas tipo operativa, skill `editar_respuestas`) hechas; B6 (oportunidades, ranking y skill `actualizar_postulaciones_potenciales`; primer ranking real corrido el 2026-11-19 solo con fuentes de riesgo bajo) y B7 (adaptación de CV por vacante, skill `adaptar_cv`, probada con tres vacantes reales) y B8 (primera postulación asistida al 0 %, skill `postular`, probada con una postulación real) y B9 (actualizar estado y recompensa, skill `actualizar_estado`) y B10 (recordatorios al abrir el menú) hechas; B11 (autonomía configurable, skill `actualizar_configuracion`, probada con datos reales al 25 y al 75 %) hecha; B16 (simulación de configuración, `python -m agente0 simulacion`) hecha y B17 (conversión de renta: factor líquido a bruto guardado por país y tasa de cambio buscada cada vez, `python -m agente0 renta`) hechas y B18 (buscador de vacantes: registro de búsquedas por fuente, búsqueda incremental, topes por riesgo y vacantes fuera del Top, `python -m agente0 busqueda`; primer ranking completo validado el 2026-11-20 con Top diario de 15) y B21 (términos de búsqueda ampliados, corridos en 7 portales; Indeed y el resto de LinkedIn quedan en B23 al final del plan) hechas; el resto de la Fase 3 sigue en `docs/tracking/todos.md`.

Arquitectura (D1): agente sobre Claude Code, a demanda. Cada operación del menú es una skill, los datos viven en archivos locales por usuario y el navegador es la extensión de Chrome. No hay ejecución programada; los recordatorios se revisan al abrir el menú.

Datos (D2): un archivo por entidad y por usuario (`md` para lo narrativo, JSON o CSV para lo estructurado), ID estable por postulación, instantáneas inmutables y CV base y respuestas tipo versionados en carpetas con fecha. Sin base de datos.

Aislamiento (D3): una instalación por persona. Este repo guarda solo skills y reglas; los datos de cada usuario viven en un directorio propio fuera del repo, indicado por la variable de entorno `AGENTE0_DATOS` (una carpeta = una persona; sugerida `Agente0_datos/<usuario>/`, una carpeta por persona junto al repo, no dentro; sin variable o dentro del repo, el agente no parte). Estructura y su creación: `python -m agente0 init` (ver `docs/contexto_completo.md` §9). El perfil del usuario 1 de partida está en `$AGENTE0_DATOS/origen/`. El agente no guarda credenciales en archivos: usa la sesión abierta del usuario en el navegador y, si un portal pide login, pausa. Se pide consentimiento antes de la primera acción externa en cada portal.

Navegador (D4): la extensión de Chrome sobre el Chrome real y la sesión del usuario. Ante CAPTCHA, login, 2FA, términos o campos imposibles, el agente pausa y pide intervención. Cada portal tiene un riesgo de bloqueo; los envíos van sin ráfagas y con límite diario por portal.

## Documentos

| Archivo | Para qué |
|---|---|
| `solo_lectura/flujo_agente_busqueda_laboral.md` | Requisitos: flujo v1.1 (diagrama, aprendizaje, autonomía). Fuente de verdad del comportamiento del agente |
| `docs/contexto_completo.md` | Diseño extenso del agente: operaciones, subflujo, aprendizaje, autonomía, entidades, pendientes, riesgos |
| `agente0/`, `tests/` | Código de apoyo para las skills (ruta de datos, estructura, ID de postulación, esquema de configuración, límites de tamaño de CV, registro de postulaciones, recordatorios, biblioteca de respuestas tipo, oportunidades, ranking, fuentes de búsqueda, compuerta de autonomía, edición de la configuración, simulación de configuración, conversión de renta y registro de búsquedas) y sus pruebas de integración. Entorno: conda `revenAI`; `python -m pytest` |
| `$AGENTE0_DATOS/` (fuera del repo) | Datos de cada usuario (perfil, intereses, configuración, respuestas tipo, historial). Si el usuario trae material previo, queda en `$AGENTE0_DATOS/origen/` |
| `docs/onboarding.md` | Banco de preguntas del onboarding y operación "Actualizar perfil" |
| `docs/decisiones.md` | Decisiones tomadas y descartadas |
| `docs/tracking/todos.md`, `docs/tracking/done.md` | Plan secuencial (skill `/todos`) y registro de lo completado |
| `solo_lectura/` (local, no versionado) | Material previo del primer usuario (trabajo en ChatGPT, CV original). Insumo de diseño y de su perfil, no requisitos |

`solo_lectura/` no se edita, no se mueve, no se borra. Si el material previo contradice al flujo v1.1, manda el flujo.

## Multiusuario

- Ningún dato personal va en este archivo, en reglas, prompts ni código. Todo dato de un usuario vive en su perfil, y los perfiles no se mezclan.
- El primer usuario es el dueño del proyecto. Sus cifras, su historial y sus preferencias son de su perfil, no del agente.
- No sacar aprendizajes ni respuestas de un usuario para otro salvo por el opt-in de D18: apagado por defecto y solo conteos agregados y anonimizados por categoría de respuesta y familia de cargo, nunca texto literal ni datos del usuario. El mecanismo no está construido; mientras tanto cada perfil aprende solo con lo suyo.

## Flujo

1. **Inicio**: ¿primera vez? Sí: onboarding (experiencia, intereses, configuración inicial con el nivel de autonomía). No: revisar recordatorios vencidos (`python -m agente0 recordatorio pendientes`, D15) y luego menú.
2. **Operaciones habituales** (seis):
   1. Actualizar perfil `(*)`: relato libre del usuario o preguntas de profundización, ver `docs/onboarding.md` §3.
   2. Actualizar postulaciones potenciales, que lleva al subflujo de postulación.
   3. Actualizar el estado de una postulación (con recompensa si hay un hito positivo).
   4. Investigar mejoras del CV para ATS y actualizar el CV base `(*)`.
   5. Actualizar configuración `(*)`, incluida la autonomía.
   6. Editar respuestas tipo `(**)`.
3. **Subflujo de postulación**, para cada empleo potencial de mayor a menor prioridad: 0) adaptar el CV base (la carta solo si el formulario la exige o el usuario la pide, D8); compuerta de autonomía; 1) postular por navegación web con respuestas tipo; 2) estado "postulado"; 3) guardar el detalle.

`(*)`: preguntar cada `X` días si se quiere actualizar (preguntar, nunca modificar solo). `(**)`: usar las respuestas tipo.

## Reglas que valen en todo nivel de autonomía

1. **Veracidad**: no inventar experiencia, renta, certificaciones, cargos, cifras ni resultados. Una palabra clave de la vacante no es una habilidad demostrada. Si falta evidencia, pedir al usuario.
2. **Autonomía = delegación (0–100 %), no permisos**. Ante CAPTCHA, fallas de login, términos de un sitio, campos imposibles o preguntas sin evidencia, pausar esa acción y pedir intervención, incluso al 100 %.
3. **Tres estados de envío**: formulario preparado, envío intentado, envío confirmado. "Postulado" solo con confirmación.
4. **Antiduplicación**: nunca reenviar una postulación ya completada sin instrucción expresa.
5. **Trazabilidad**: guardar una instantánea inmutable de lo enviado (CV, preguntas, texto literal de respuestas, evidencia) y bajo qué nivel de autonomía y aprobación.
6. **Aprendizaje**: un hito positivo (hoy, contacto para primera entrevista) crea **un solo** evento de recompensa, que se asocia a las versiones exactas de las respuestas enviadas. Es asociación, no causalidad. Sin castigo automático por silencio o rechazo. No cambia el perfil del usuario.
7. **Respuestas tipo versionadas**: el aprendizaje no modifica la respuesta base en silencio.
8. **Cambios de autonomía** aplican a lo pendiente y futuro; no autorizan envíos pasados.
9. **Datos sensibles**: aislar por usuario; credenciales de portales nunca en archivos del repositorio (usar `.env` o un gestor de secretos).

Niveles de autonomía (D12): 0, 25, 50, 75 y 100 %; un valor intermedio se redondea hacia abajo. Las condiciones de auto-envío del usuario aplican al 75 %; al 100 % rigen solo las reglas siempre vigentes. Excepciones y tope de nivel por portal, límites diarios por riesgo de portal y aviso explícito antes de activar 100 %. Detalle en `docs/decisiones.md`.

## Decisiones de diseño

Las 18 de la Fase 1 (`D1` a `D18`) están cerradas y registradas en `docs/decisiones.md`, con su resumen en `docs/contexto_completo.md` §11. Una decisión cerrada se reabre solo por la condición que trae registrada. Las decisiones nuevas siguen la misma regla: presentar 2 opciones con tradeoffs, recomendar y esperar confirmación. No construir nada de la Fase 3 antes de cerrar las confirmaciones de las que depende (`[dep: ...]`).

## TO DO

Ver [`docs/tracking/todos.md`](docs/tracking/todos.md). Completados en [`docs/tracking/done.md`](docs/tracking/done.md).

## Cómo trabajar aquí

- Ir de menos a más: la versión mínima que haga el flujo con un usuario antes de construir para muchos. No construir infraestructura antes de validar que el agente produce entrevistas.
- Registrar decisiones en `docs/decisiones.md`. Datos nuevos de un usuario van a su perfil.
- Al trabajar con un usuario (por ejemplo preparar su CV o sus respuestas), leer antes su material de partida en `$AGENTE0_DATOS/origen/`, si lo hay: sus reglas de veracidad, contradicciones por confirmar y condiciones de auto-envío están ahí.
- Las preferencias personales de trabajo del dueño del proyecto van en `CLAUDE.local.md` (no versionado).
