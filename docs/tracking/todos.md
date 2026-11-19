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

- [ ] **B7 · Adaptación de CV por vacante (paso 0)** [dep: B3, B6]: Adaptar el CV base a una vacante con control de veracidad y un resumen de cambios y brechas. Probar con tres vacantes reales. (I:9 C:4 H:8 → 2.12)
  - Claude: adaptar dentro de los límites por bloque de B3, compilar, revisar el render y auditar las afirmaciones; subagente revisor solo si la autonomía es 75 % o más.
  - Usuario: aprobar las tres adaptaciones.
- [ ] **B8 · Primera postulación asistida (autonomía 0 %)** [dep: B5, B7, D4, D12, D14, U5]: Postular por navegación web a una vacante real con confirmación en cada paso, en un portal de bajo riesgo. Guardar la instantánea y pasar a postulado solo con confirmación del sitio. (I:10 C:5 H:9 → 1.90)
  - Claude: validar la sesión del portal antes de partir (si no hay, pausar y avisar), operar el navegador, pedir confirmación en cada paso y registrar el resultado.
  - Usuario: elegir el portal de la prueba (bajo riesgo, ver `$AGENTE0_DATOS/origen/` (material de partida) §8.4), iniciar sesión a mano en él y aprobar cada paso.
- [ ] **B9 · Actualizar estado y recompensa** [dep: B8, D16]: Cambio de estado con historial y un solo evento de recompensa por hito, ligado a las respuestas realmente enviadas. Probar con un contacto simulado y comprobar que repetir el aviso no duplica el premio. (I:8 C:4 H:7 → 1.87)
  - Claude: implementar y probar.
  - Usuario: informar el primer resultado real cuando ocurra.
- [ ] **B10 · Recordatorios periódicos** [dep: B2, D15]: Preguntar cada `X` días si se actualiza experiencia, CV base o configuración, con opción de aceptar, posponer o descartar. (I:5 C:2 H:5 → 2.50)
  - Claude: implementar los recordatorios.
- [ ] **B11 · Autonomía configurable** [dep: B8, D12, U4]: Implementar el nivel 0 a 100 %, la compuerta de aprobación y el registro de qué fue automático y qué aprobado. Probar al 25 % y al 75 % antes de ofrecer 100 %. Antes de cualquier envío automático, correr el primer ranking real y calibrar con él los umbrales (U4). Todos los parámetros (nivel, condiciones, umbrales por eje, renta mínima, límites por portal) viven en la configuración del usuario y se editan desde "Actualizar configuración", sin tocar código. (I:10 C:5 H:9 → 1.90)
  - Claude: implementar y probar cada nivel.
  - Usuario: probar los niveles.
- [ ] **B16 · Simulación de configuración** [dep: B6, B11]: Función "¿y si...?" sobre el último ranking: al cambiar umbrales, renta mínima, pesos o nivel, mostrar qué vacantes pasarían a cumplir o dejarían de cumplir las condiciones de auto-envío y cuáles irían a la cola de aprobación, sin modificar la configuración vigente. Pedido por el usuario 1 en U4. (I:6 C:3 H:7 → 2.16)
  - Claude: implementar la simulación sobre las evidencias guardadas de cada puntaje y probarla con el primer ranking real.
  - Usuario: probarla y ajustar los umbrales con ella antes de subir el nivel.
- [ ] **B12 · Postulaciones con autonomía alta del usuario 1** [dep: B11, B9]: Subir su nivel de forma gradual hasta el que confirmó en U4, con revisión semanal de lo enviado. (I:9 C:3 H:7 → 2.65)
  - Claude: operar según el nivel y preparar el resumen semanal.
  - Usuario: revisar lo enviado cada semana.
- [ ] **B13 · Medición y revisión del aprendizaje** [dep: B12, D17]: Medir entrevistas por hora de esfuerzo y tasa de contacto en ventanas de 4 a 6 semanas; revisar si las recomendaciones de respuestas aportan. (I:8 C:3 H:6 → 2.31)
  - Claude: calcular las métricas y presentar el reporte.
  - Usuario: informar los resultados de cada proceso.
- [ ] **B14 · Segundo usuario** [dep: B13, D3, D18]: Incorporar a una segunda persona con su propio perfil y verificar el aislamiento de datos y del aprendizaje. (I:8 C:4 H:7 → 1.87)
  - Claude: ejecutar el onboarding del segundo usuario y probar el aislamiento.
  - Usuario: elegir a la persona.
