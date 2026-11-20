---
name: actualizar_configuracion
description: Operación 5 del menú de Agente0 (Actualizar configuración). Muestra la configuración vigente del usuario y aplica los cambios que pida (nivel de autonomía, condiciones de auto-envío, umbrales de match, renta mínima, límites y topes por portal, excepciones, recordatorios, pesos, vigencia del factor de conversión de renta) sin tocar código, con simulación de qué vacantes cambiarían de destino (B16), vista previa de qué pasa a requerir aprobación y el aviso de D12 antes de activar 100 %. Usar cuando el usuario invoque /actualizar_configuracion, elija "Actualizar configuración" en el menú o acepte el recordatorio de configuración.
---

# actualizar_configuracion

Diseño: D12 (niveles, condiciones, excepciones, límites y aviso de 100 %), U4 (parámetros editables) y D15 (recordatorio de configuración) en `docs/decisiones.md`; `docs/contexto_completo.md` §4.5 y §7. Esta skill es genérica: no lleva datos de ningún usuario; todo sale de `$AGENTE0_DATOS/configuracion/configuracion.json`.

Alcance: cambiar parámetros de la configuración del usuario. Sin navegador ni acciones externas. Nunca cambia nada que el usuario no haya pedido ni elige valores por él. Un cambio de autonomía aplica a lo pendiente y futuro; no autoriza envíos pasados (regla 8).

## 0. Preparación

1. Comprobar que `AGENTE0_DATOS` existe. Si falta, decirlo y terminar.
2. `python -m agente0 configuracion ver` y, para la autonomía, `python -m agente0 autonomia matriz <nivel vigente>`.

## 1. Mostrar lo vigente

Resumir en pocas líneas, agrupado, sin volcar el JSON:

- **Autonomía**: el nivel y qué se hace solo y qué se aprueba en él.
- **Compuerta** (`compuerta`): condiciones de preferencia activas, `seniority_permitido` y `ubicaciones_permitidas`, límites diarios por riesgo, pausa entre envíos, topes de nivel por riesgo y por portal, excepciones «siempre aprobar» por portal y empresa.
- **Priorización** (`priorizacion`): umbrales de match por eje, renta mínima, empresas excluidas, pesos de los criterios, tamaño del Top y ventana de vigencia.
- **Búsqueda** (`busqueda`): topes por corrida y por fuente según el riesgo (`topes_por_riesgo`: páginas de resultados y publicaciones leídas); un riesgo que no figura no tiene tope, y el primer día de búsqueda en una fuente tampoco.
- **Recordatorios**: los tres `X` de días y la repetición en horas.

Si una condición activa tiene la lista vacía (`seniority_permitido`, `ubicaciones_permitidas`), decirlo: al 75 % nada se envía solo hasta definirla.

Preguntar qué quiere cambiar con `AskUserQuestion` (una pregunta a la vez, autocontenida). Si no quiere cambiar nada, registrar la revisión (§4) y terminar.

## 2. Armar el cambio

Cada cambio es un JSON parcial para `configuracion editar`; los bloques se fusionan clave a clave y los mapas (`criterios`, `tope_por_riesgo`, `topes_por_portal`) se reemplazan completos, así que enviar el mapa entero.

Antes de aplicar, mostrar el antes y el después de cada valor.

- **Valores con números** (umbrales, renta mínima, límites): pedirlos al usuario. La renta mínima va en el mismo monto, moneda y período que la renta publicada de las vacantes (así la compara el código).
- **Simulación (B16)**: antes de aplicar un cambio de umbrales, pesos, renta mínima, filtros, listas, topes, excepciones o nivel, correr `python -m agente0 simulacion` con `{"cambios": {...}}` por stdin, el mismo JSON de `configuracion editar`; no escribe nada. Devuelve una fila por vacante evaluada con su resultado vigente y el hipotético (`destino`: `fuera`, `sin_evaluacion`, `cola`, `auto_condicionado` o `auto`; puntajes; puesto en el Top) y los `cambios`.
  - Mostrar solo las filas con `cambios` y, de cada una, empresa, cargo, qué cambia y, si el destino nuevo es `cola`, sus `motivos`. Si ninguna cambia, decirlo.
  - Las filas `referencial` (ya en postulación o descartadas) son evidencia para calibrar, no candidatas.
  - Decir siempre que `auto_condicionado` es automático solo si el agente califica seniority y ubicación dentro de las listas al enviar, y lo que lista `no_simulado`. Mostrar las `advertencias`.
  - Si las vacantes no traen `renta_publicada`, cambiar la renta mínima no mueve nada: decirlo.
  - Con pocas vacantes la simulación no calibra por sí sola: decirlo si son menos de diez.
- **Reglas siempre vigentes** (vigencia del día, no postulada antes, empresa no excluida, CV auditado, respuestas documentadas) y las pausas de D4: no son configurables; si el usuario pide quitarlas, decir que no se pueden desactivar.
- **Condiciones de preferencia**: quitar una de `condiciones_preferencia` la desactiva; es una decisión del usuario, nombrar qué deja de exigirse.

## 3. Cambiar el nivel de autonomía

1. Mostrar `autonomia matriz <nivel nuevo>` como vista previa de qué pasará a requerir aprobación y la simulación con `{"autonomia": <nivel nuevo>}` (§2), y decir que aplica a lo pendiente y futuro.
2. Subir de a un escalón y probar cada nivel antes del siguiente (U4, B11). Si el usuario pide saltar más de uno, decir qué se saltaría y dejarlo decidir.
3. Del 75 % hacia arriba, revisar antes que las listas de condiciones estén definidas y que los umbrales se hayan calibrado con un ranking real.
4. **Activar 100 %**: no ofrecerlo por iniciativa propia; solo si el usuario lo pide. Mostrar el aviso completo de `python -m agente0 autonomia aviso 100` (acciones externas, portales, límites, qué deja de regir) y pedir confirmación explícita con `AskUserQuestion`. Pasar sus palabras como `confirmacion`; el código la registra con fecha en `configuracion/autonomia.jsonl` y rechaza el cambio sin ella.
5. Bajar el nivel no pide confirmación.

## 4. Aplicar y registrar

1. `python -m agente0 configuracion editar` con `{"cambios": {...}, "confirmacion": "..."}` por stdin. Si el código rechaza el valor, mostrar el error tal cual y corregir con el usuario; el archivo no se toca.
2. Mostrar las `advertencias` que devuelve (nivel redondeado, listas vacías).
3. Reiniciar el reloj del recordatorio: `python -m agente0 recordatorio operacion configuracion`.
4. Decir en una línea qué quedó cambiado. Si cambió algo que afecta lo ya preparado (por ejemplo, el nivel con postulaciones en la cola), decir que las pendientes se reevalúan con la configuración nueva al retomarlas con `/postular <id>`.

## Formato de las preguntas

- Cada pregunta de `AskUserQuestion` es autocontenida: lleva el parámetro, su valor vigente, el valor propuesto y qué pasa con cada opción, sin depender del texto anterior.
- Pedir al usuario solo lo que es suyo (cuánto delega, qué riesgo asume, qué cifras exige). Lo que resuelven las decisiones registradas se informa con su fuente, no se pregunta.
