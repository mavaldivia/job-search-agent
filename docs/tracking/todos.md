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

- [ ] **B16 · Simulación de configuración** [dep: B6, B11]: Función "¿y si...?" sobre el último ranking: al cambiar umbrales, renta mínima, pesos o nivel, mostrar qué vacantes pasarían a cumplir o dejarían de cumplir las condiciones de auto-envío y cuáles irían a la cola de aprobación, sin modificar la configuración vigente. Pedido por el usuario 1 en U4. (I:6 C:3 H:7 → 2.16)
  - Claude: implementar la simulación sobre las evidencias guardadas de cada puntaje y probarla con el primer ranking real.
  - Usuario: probarla y ajustar los umbrales con ella antes de subir el nivel.
- [ ] **B17 · Conversión automática de renta en formularios** [dep: B8]: Cuando un formulario pida la renta en otra moneda o base (por ejemplo bruto en USD) y la biblioteca no tenga esa cifra, que el sistema la calcule solo con el dólar del día y los descuentos legales vigentes, y deje el monto para aprobación según el nivel de autonomía. Pedido por el usuario 1 en B8, donde se hizo a mano. Es una decisión de diseño: presentar 2 opciones (módulo de código con tablas actualizables vs. procedimiento de la skill con consulta a fuentes oficiales) antes de construir. (I:6 C:3 H:7 → 2.16)
  - Claude: presentar las dos opciones con tradeoffs, recomendar y, con la confirmación del usuario, implementar y probar.
  - Usuario: elegir la opción y confirmar los supuestos de descuentos (AFP y plan de salud).
- [ ] **B18 · Mejora del buscador de vacantes (operación 2)** [dep: B6]: El primer ranking real salió con 5 vacantes, todas de Get on Board, y no queda registro por fuente de qué se buscó ni cuándo. Mejorarlo en cuatro frentes: (a) cobertura: recorrer todas las fuentes activas de `fuentes.json`, no solo las de riesgo bajo (LinkedIn Jobs, Indeed, Computrabajo, Laborum, Trabajando y portales corporativos por navegador), con el consentimiento por portal de D3 y los límites y pausas de D4; (b) búsqueda incremental por fuente: guardar la fecha de la última búsqueda de cada fuente y pedir solo lo publicado desde entonces (por ejemplo en LinkedIn, los cargos publicados después de la última búsqueda); lo anterior se da por revisado y ya está en las bases de oportunidades; (c) exhaustividad inteligente: más variantes y sinónimos de cargo según `intereses.md`, paginación completa de cada búsqueda, deduplicación entre fuentes y registro de las consultas hechas; (d) conservar las vacantes de puntaje bajo en vez de descartarlas a simple vista, con su puntaje y evidencia, para que reaparezcan sin volver a buscarlas si el usuario baja los umbrales (conecta con B16). Pedido por el usuario 1 durante la prueba de B11. (I:8 C:5 H:8 → 1.60)
  - Claude: revisar la skill y el código para ver qué se pierde hoy (descartes a simple vista, vacantes fuera del Top, fuentes sin registro); presentar 2 opciones donde cambie el diseño (por ejemplo, dónde guardar la fecha de la última búsqueda por fuente) y esperar confirmación; implementar y probar con una corrida real.
  - Usuario: aprobar el consentimiento por portal, fijar hasta dónde llega la exhaustividad en los portales de riesgo medio y alto (lecturas por corrida) y revisar los resultados.
- [ ] **B19 · Renta observada en el formulario** [dep: B11]: En la prueba al 75 % el portal avisó que la renta declarada superaba la oferta del cargo y, probando valores sin avanzar de paso, el tope quedó acotado entre dos cifras; la compuerta no lo vio, porque la publicación no traía renta y la condición de renta mínima se da por cumplida. Registrar ese tope acotado como dato de la oportunidad y hacer que la condición de renta mínima lo use (si el tope queda bajo la mínima del usuario, el envío va a la cola). Es una decisión de diseño: presentar 2 opciones (campo nuevo en la oportunidad con el rango observado vs. juicio del agente con evidencia, como los de seniority y ubicación) antes de construir. (I:6 C:3 H:7 → 2.16)
  - Claude: presentar las dos opciones con tradeoffs, recomendar y, con la confirmación del usuario, implementar y probar.
  - Usuario: elegir la opción.
- [ ] **B12 · Postulaciones con autonomía alta del usuario 1** [dep: B11, B9]: Subir su nivel de forma gradual hasta el que confirmó en U4, con revisión semanal de lo enviado. (I:9 C:3 H:7 → 2.65)
  - Claude: operar según el nivel y preparar el resumen semanal.
  - Usuario: revisar lo enviado cada semana.
- [ ] **B13 · Medición y revisión del aprendizaje** [dep: B12, D17]: Medir entrevistas por hora de esfuerzo y tasa de contacto en ventanas de 4 a 6 semanas; revisar si las recomendaciones de respuestas aportan. (I:8 C:3 H:6 → 2.31)
  - Claude: calcular las métricas y presentar el reporte.
  - Usuario: informar los resultados de cada proceso.
- [ ] **B14 · Segundo usuario** [dep: B13, D3, D18]: Incorporar a una segunda persona con su propio perfil y verificar el aislamiento de datos y del aprendizaje. (I:8 C:4 H:7 → 1.87)
  - Claude: ejecutar el onboarding del segundo usuario y probar el aislamiento.
  - Usuario: elegir a la persona.
