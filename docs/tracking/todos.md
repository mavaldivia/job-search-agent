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

- [ ] **B21 · Ampliar los términos de búsqueda con los cargos del perfil** [dep: B18]: El usuario 1 pidió ampliar la búsqueda a una lista de términos de analítica avanzada, inteligencia de decisión, optimización y planificación, analítica de operaciones y de cadena de suministro, y producto de datos; quedó confirmada en `intereses.md` (I8, en su carpeta de datos, no versionada). Cada término nuevo es una consulta distinta en cada fuente (una variante no hereda lo cubierto por las otras), así que hay que repasar todas las fuentes activas con la ventana completa, incluidas Indeed (la primera pasada quedó cortada por una verificación anti-bot que debe resolver el usuario en su Chrome) y LinkedIn Jobs (sin buscar todavía, con sus topes de riesgo alto); desde el segundo día de una fuente rigen los topes por riesgo y puede tomar varias corridas. Además, el agente propone términos extra a partir del perfil (variantes en español y de las familias secundarias) y el usuario confirma cuáles entran. (I:8 C:2 H:8 → 4.00)
  - Claude: proponer los términos extra con su razón, correr cada término nuevo en todas las fuentes activas respetando cupo y registro de B18, y presentar lo nuevo que aparezca en el ranking.
  - Usuario: confirmar qué términos extra entran y revisar lo que aparezca.
- [ ] **B20 · Investigar fuentes nuevas según el perfil** [dep: B18]: Además de las fuentes ya declaradas en `fuentes.json`, investigar en la web portales, bolsas especializadas, agregadores y headhunters afines al perfil y a `intereses.md` (cargos de prioridad alta, geografía, sectores) y dejarlos en la lista de fuentes. Cada candidata se valida con una ventana de 30 días (`ventana_dias`): sirve solo si tiene vacantes afines publicadas en ese período. Entra con tipo, país, enlace, método y riesgo. Si exige cuenta y el usuario no la tiene, el agente avisa y el usuario la crea (D4: el agente nunca crea cuentas); mientras tanto la fuente queda `activa: false`. La primera búsqueda en cada fuente nueva usa la primera pasada completa de B18. Pedido por el usuario 1 durante B18. (I:6 C:4 H:7 → 1.62)
  - Claude: investigar y validar cada candidata con la ventana de 30 días, presentar la lista con su evidencia (vacantes afines vistas, riesgo estimado, si pide cuenta) y agregarla con `fuentes agregar`; ajustar la skill `actualizar_postulaciones_potenciales` (§5, portales sugeridos) con este paso.
  - Usuario: aprobar qué fuentes quedan y crear las cuentas que hagan falta cuando el agente avise.
- [ ] **B19 · Renta observada en el formulario** [dep: B11]: En la prueba al 75 % el portal avisó que la renta declarada superaba la oferta del cargo y, probando valores sin avanzar de paso, el tope quedó acotado entre dos cifras; la compuerta no lo vio, porque la publicación no traía renta y la condición de renta mínima se da por cumplida. Registrar ese tope acotado como dato de la oportunidad y hacer que la condición de renta mínima lo use (si el tope queda bajo la mínima del usuario, el envío va a la cola). Es una decisión de diseño: presentar 2 opciones (campo nuevo en la oportunidad con el rango observado vs. juicio del agente con evidencia, como los de seniority y ubicación) antes de construir. (I:6 C:3 H:7 → 2.16)
  - Claude: presentar las dos opciones con tradeoffs, recomendar y, con la confirmación del usuario, implementar y probar.
  - Usuario: elegir la opción.
- [ ] **B12 · Postulaciones con autonomía alta del usuario 1** [dep: B11, B9]: Subir su nivel de forma gradual hasta el que confirmó en U4, con revisión semanal de lo enviado. Desde el 2026-11-20 el Top diario es de 15 y el umbral de match ya no es condición de auto-envío (decisión del usuario 1 al cerrar B18): a 50 % todo sigue yendo a aprobación, y desde 75 % las vacantes del Top salen solas dentro de los límites diarios por portal. (I:9 C:3 H:7 → 2.65)
  - Claude: operar según el nivel y preparar el resumen semanal.
  - Usuario: revisar lo enviado cada semana.
- [ ] **B13 · Medición y revisión del aprendizaje** [dep: B12, D17]: Medir entrevistas por hora de esfuerzo y tasa de contacto en ventanas de 4 a 6 semanas; revisar si las recomendaciones de respuestas aportan. (I:8 C:3 H:6 → 2.31)
  - Claude: calcular las métricas y presentar el reporte.
  - Usuario: informar los resultados de cada proceso.
- [ ] **B14 · Segundo usuario** [dep: B13, D3, D18]: Incorporar a una segunda persona con su propio perfil y verificar el aislamiento de datos y del aprendizaje. (I:8 C:4 H:7 → 1.87)
  - Claude: ejecutar el onboarding del segundo usuario y probar el aislamiento.
  - Usuario: elegir a la persona.
