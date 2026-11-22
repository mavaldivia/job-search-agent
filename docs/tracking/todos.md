## TO DO

**Convención de priorización**: cada ítem pendiente lleva `(I:x C:y H:z → score)` — Impacto, Complejidad de desarrollo, Habilitación, escala 1–10. `score = √(I × H) / C`. **Todas las secciones son secuenciales**: el orden de los ítems es el orden de ejecución y se respeta con `[dep: ...]`; el score es solo referencia y no se reordena.

**Convención de labores** (en todo el archivo): cada ítem lleva, cuando corresponde, sub-líneas `Claude:` (lo que hago yo) y `Usuario:` (lo que decide o ejecuta él: decisiones, accesos, confirmaciones). Si uno de los dos no tiene labor en ese ítem, no se escribe esa línea.

**Convención de dependencias**: `[dep: D1, D2]` indica ítems que deben estar `[x]` en `done.md` antes de empezar. Los IDs `D#`, `U#` y `B#` se conservan al mover el ítem a `done.md`, bajo la subsección de su fase (mismo nombre).

**Regla de decisiones**: cada ítem `D#` se resuelve presentando 2 opciones con tradeoffs y una recomendación, y esperando la confirmación del usuario 1. Al cerrarlo se registra en `docs/decisiones.md`, se actualiza `docs/contexto_completo.md` §11 y, si cambia una regla, `CLAUDE.md`.

**Orden general**: Fase 1 (decisiones de diseño) → Fase 2 (datos del usuario 1, que puede avanzar en paralelo a Fase 1 mientras no tenga `[dep: ...]`) → Fase 3 (construcción mínima con el usuario 1 como primer usuario). Los `D#` cubren las 18 decisiones pendientes de `docs/contexto_completo.md` §11, más forma de ejecución, onboarding y carta.

> Contexto: requisitos en [`solo_lectura/flujo_agente_busqueda_laboral.md`](../../solo_lectura/flujo_agente_busqueda_laboral.md); diseño en [`docs/contexto_completo.md`](../contexto_completo.md); datos del usuario 1 en `$AGENTE0_DATOS/origen/` (material de partida); decisiones en [`docs/decisiones.md`](../decisiones.md).

### Fase 1 — Decisiones de diseño

> Cerrada (2026-11-15): D1 a D18 resueltas, ver `done.md` y `decisiones.md`.

### Fase 2 — Datos del usuario 1

> Cerrada (2026-11-16): U4 a U6 resueltas, ver `done.md` y `decisiones.md`. Los datos de perfil (antes U1 a U3) se confirmaron en el onboarding (B2); los IDs U1 a U3 no se reutilizan.

### Fase 3 — Construcción mínima con el usuario 1

> Objetivo: la versión mínima que haga el flujo completo con un usuario, subiendo la autonomía de forma gradual, antes de abrir el agente a más personas. Cada ítem espera a las decisiones y confirmaciones de las que depende.

- [ ] **B26 · Historial previo de postulaciones fuera del sistema** [dep: B4]: la corrida del 2026-11-21 mostró que la antiduplicación del código no ve las postulaciones que el usuario 1 hizo a mano: cuatro vacantes figuraban sin postular y solo los subagentes las detectaron al leer LinkedIn («Solicitud enviada»); además el material de partida (§9) lista 27 postulaciones previas. B4 decidió no cargar el historial (2026-11-19); con autonomía alta (B12) el riesgo de reenviar sube. Es decisión de diseño: presentar 2 opciones (por ejemplo cargarlo como postulaciones `POSTULADO` importadas, sin instantánea y con fecha aproximada, vs. mantener la revisión manual del material de partida que hacen los subagentes) antes de construir. (I:7 C:3 H:7 → 2.33)
  - Claude: presentar las opciones con tradeoffs, recomendar y, con la confirmación del usuario, implementar y registrar la decisión.
  - Usuario: elegir la opción y confirmar las fechas aproximadas si se carga.
- [ ] **B12 · Postulaciones con autonomía alta del usuario 1** [dep: B11, B9, B26 (recomendado)]: Subir su nivel de forma gradual hasta el que confirmó en U4, con revisión semanal de lo enviado. El nivel sigue en 50 % (el usuario lo bajó de 75 a 50 % el 2026-11-19), así que todo envío va a aprobación; desde 75 % las vacantes del Top salen solas dentro de los límites diarios por portal y de las condiciones. Desde el 2026-11-20 el Top diario es de 15 y el umbral de match ya no es condición de auto-envío (decisión del usuario 1 al cerrar B18). (I:9 C:3 H:7 → 2.65)
  - Claude: hecho el 2026-11-21: resumen semanal y registro de las horas de esfuerzo (`resumen semanal`, `resumen revisado`, skill `revision_semanal`). Pendiente: operar según el nivel que el usuario fije.
  - Usuario: subir el nivel de forma gradual y correr `/revision_semanal` cada semana (declarando sus horas).
- [ ] **B13 · Medición y revisión del aprendizaje** [dep: B12, D17]: Medir entrevistas por hora de esfuerzo y tasa de contacto en ventanas de 4 a 6 semanas; revisar si las recomendaciones de respuestas aportan. Medición construida el 2026-11-21 (`medicion ventanas | respuestas`, parámetros en el bloque `medicion` de la configuración); hoy hay 3 envíos y 0 contactos: todo sale «sin conclusión» y «pocos datos». (I:8 C:3 H:6 → 2.31)
  - Claude: hecho el código y las pruebas. Pendiente: presentar el reporte cuando haya 4 a 6 semanas de envíos y al menos 5 contactos por ventana.
  - Usuario: informar los resultados de cada proceso y sus horas semanales.
- [ ] **B14 · Segundo usuario** [dep: B13, D3, D18]: Incorporar a una segunda persona con su propio perfil y verificar el aislamiento de datos y del aprendizaje. Aislamiento ya probado con pruebas de integración el 2026-11-21 (`tests/test_aislamiento.py`): ninguna operación de un usuario toca la carpeta de otro, el aprendizaje y la deduplicación no cruzan, y un usuario nuevo parte con autonomía 0. (I:8 C:4 H:7 → 1.87)
  - Claude: hecho el aislamiento. Pendiente: ejecutar el onboarding del segundo usuario con la persona elegida.
  - Usuario: elegir a la persona.
- [ ] **B23 · Indeed y lo que quedó de la ampliación de términos** [dep: B21]: avance del 2026-11-21 (una corrida acotada dentro de los topes): leídas las vistas «no leídas» de LinkedIn, Trabajando.com, Computrabajo y Laborum, y buscados 2 términos nuevos en LinkedIn (2 de 3 páginas y 10 de 10 lecturas del día, sin señal de bloqueo). Quedan: Indeed (verificación de Cloudflare que el agente no salta, la resuelve el usuario), 38 de los 40 términos de LinkedIn sin su primera página (3 páginas por día), las 16 vacantes plausibles que Jooble descubrió y no se pueden abrir sin pasar su verificación de Cloudflare (entre ellas una muy afín de un retailer grande), y las dos vacantes de Himalayas que quedaron descartadas por estar fuera de ventana. (I:3 C:3 H:5 → 1.29)
  - Claude: seguir las corridas de LinkedIn de a 3 páginas por día y repasar lo que el usuario desbloquee.
  - Usuario: resolver la verificación anti-bot de Indeed y de Jooble en su Chrome, y revisar lo que aparezca.
- [ ] **B28 · Carril de BNE con sesión**: la preparación de punta a punta del carril de BNE sigue sin probar: en las dos corridas de B25 no había sesión del usuario en ese portal y el usuario 1 la dejó para después el 2026-11-22. Con sesión, validarla en el Chrome de la extensión, correr `python -m agente0 carriles` y preparar o postular las vacantes de ese carril según la compuerta (a 50 % todo envío va a su aprobación). (I:3 C:2 H:5 → 1.94)
  - Claude: validar la sesión de BNE, lanzar el carril y llevar cada vacante hasta la aprobación o el envío.
  - Usuario: iniciar sesión a mano en BNE en el Chrome que controla la extensión, cuando quiera retomarlo.
