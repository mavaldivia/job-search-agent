---
name: revision_semanal
description: Revisión semanal de lo enviado por Agente0 (B12) y medición del aprendizaje (B13). Muestra qué se envió desde la última revisión, bajo qué nivel de autonomía y con qué aprobación, qué espera aprobación o verificación y qué contactos hubo; registra las horas de esfuerzo que el usuario declara y reporta las ventanas de D17 y la tasa por versión de respuesta de D16. Usar cuando el usuario invoque /revision_semanal, pida "el resumen de la semana" o "cómo vamos", o cuando al abrir el menú hayan pasado 7 días desde la última revisión.
---

# revision_semanal

Diseño: B12 (revisión semanal de lo enviado), D16 (recompensa y recomendación de respuestas), D17 (medición) y B25 (carriles) en `docs/decisiones.md`. Esta skill es genérica: no lleva datos de ningún usuario. Solo lee y reporta; no cambia el nivel de autonomía, la configuración ni las respuestas.

## Pasos

1. `python -m agente0 resumen semanal` (sin fechas: desde el día siguiente a la última revisión hasta hoy; con `desde hasta` para otro período). Mostrar en este orden, breve:
   - Nivel de autonomía actual y los cambios del período (`cambios_de_autonomia`).
   - Lo enviado: cuántas y por portal; cuántas salieron `automatico` y cuántas con aprobación del usuario (`aprobado`). Una tabla con empresa, cargo, portal, fecha, nivel efectivo y resolución.
   - Lo que pide acción: `por_verificar` (ENVIO_INTENTADO sin confirmación: verificar en el portal o el correo, sin reenviar) y `en_cola` (PREPARADA: esperan su OK o un reintento).
   - Primeros contactos y otros hitos del período, y las oportunidades nuevas.
2. Preguntar cuántas horas dedicó el usuario a la búsqueda en el período (con una pregunta de `AskUserQuestion` autocontenida, o en el chat) y registrarlas: `python -m agente0 resumen revisado` con `{"horas_esfuerzo": <horas>, "nota": "<opcional>"}`; el período sale solo de la revisión anterior (`desde` y `hasta` solo para otro). Si no sabe, no inventar: dejar la revisión sin registrar. Las horas son lo que él declara (D17).
3. `python -m agente0 medicion ventanas` y mostrar cada ventana con su número de envíos y de contactos, la tasa de contacto, las horas y los contactos por hora, y la comparación contra la línea base. Con menos contactos que `minimo_contactos` el código marca `sin_conclusion`: decirlo así y no interpretar. Nunca afirmar que una respuesta o un cambio causó un resultado: es asociación (D17).
4. `python -m agente0 medicion respuestas`: mostrar las versiones con sus usos y su marca. `recomendar: true` solo cuando hay `usos_para_recomendar` usos comparables y la tasa suavizada supera la base; en cualquier otro caso, mostrar los datos con la marca `pocos_datos`. Sugerir la versión o proponer una edición, nunca cambiar la respuesta base: eso pasa por `editar_respuestas`.
5. Cerrar con una pregunta sobre el nivel de autonomía solo si el resumen la hace relevante (por ejemplo, todo lo enviado fue aprobado sin cambios). Subir el nivel es del usuario: `actualizar_configuracion`.

## Notas

- Los envíos enviados antes de B11 no traen portal ni nivel efectivo (aparecen como «sin portal»).
- Los contactos de una ventana siguen llegando después de que cierra: `madura` es `false` hasta que pasan `dias_para_resolver` días desde su último envío.
