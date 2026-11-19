---
name: actualizar_estado
description: Operación 3 del menú de Agente0 (Actualizar el estado de una postulación). Registra lo que el usuario informa de un proceso (contacto para entrevista, nueva etapa, oferta, rechazo, retiro, cierre por silencio), mueve el estado con historial y, solo ante el primer contacto de entrevista, crea un único evento de recompensa ligado a las respuestas realmente enviadas. Usar cuando el usuario invoque /actualizar_estado, elija "Actualizar el estado de una postulación" en el menú o cuente que pasó algo en un proceso (por ejemplo "me contactaron", "pasé a la siguiente entrevista", "me rechazaron").
---

# actualizar_estado

Diseño: D5, D14 y D16 en `docs/decisiones.md`; registro de B9. Esta skill es genérica: no lleva datos de ningún usuario; todo sale de `$AGENTE0_DATOS/postulaciones/`.

Alcance: el registro local de una postulación ya enviada. Sin navegador ni acciones externas. Nunca marca algo que el usuario no informó ni inventa fechas, etapas o motivos.

## Cómo está guardado

- `postulaciones/<id>/postulacion.json` (estado, etapa, resultado) y `eventos.jsonl` (append-only: un evento por cambio, con su estado resultante). La instantánea de lo enviado está en `instantanea/<intento>/` y no se toca.
- Estados: `POSTULADO` → `EN_PROCESO` (campo `etapa`) → `FINALIZADA` (campo `resultado`). Sin retrocesos: el CLI rechaza lo que no corresponde y no hay forma de editar el historial. Si el usuario pide corregir un registro, decirlo y no editar archivos a mano.
- Todo pasa por el CLI:

```bash
python -m agente0 postulacion ver <id>
python -m agente0 postulacion evento <id> <<'EOF'
{"tipo": "PRIMER_CONTACTO_ENTREVISTA", "detalle": "Correo de la reclutadora del 2026-11-20"}
EOF
python -m agente0 postulacion evento <id> <<'EOF'
{"tipo": "NUEVA_ETAPA", "etapa": "entrevista técnica", "detalle": "..."}
EOF
python -m agente0 postulacion finalizar <id> <<'EOF'
{"resultado": "oferta_rechazada_por_usuario", "detalle": "..."}
EOF
python -m agente0 postulacion recompensar <id>
```

## 1. Identificar la postulación

1. Comprobar que `AGENTE0_DATOS` existe. Listar `postulaciones/` y leer cada `postulacion.json` con `ver`.
2. Si el usuario nombró empresa o cargo y solo una coincide, usarla. Si hay duda, preguntar con `AskUserQuestion` mostrando empresa, cargo, estado y fecha de cada candidata. Una postulación `PREPARADA` o `ENVIO_INTENTADO` no se actualiza aquí: el envío se cierra con `postular`.
3. Mostrar su estado actual antes de registrar nada.

## 2. Registrar el evento

Traducir lo que el usuario cuenta, sin interpretar de más:

| Lo que informa | Evento | Condición |
|---|---|---|
| Lo contactaron para una primera entrevista | `PRIMER_CONTACTO_ENTREVISTA` | Solo desde `POSTULADO`. Pasa a `EN_PROCESO`, etapa "primera entrevista" |
| Tuvo una entrevista | `ENTREVISTA_REALIZADA` | Solo en `EN_PROCESO`. No cambia la etapa |
| Pasó a otra etapa | `NUEVA_ETAPA` con `etapa` | Pedir el nombre de la etapa tal como la dijo |
| Recibió una oferta | `OFERTA_RECIBIDA` | Solo en `EN_PROCESO` |
| Lo rechazaron | `RECHAZO` | Finaliza con `rechazada_por_empresa` |
| Se retiró | `RETIRO` | Finaliza con `retirada` |
| Sin noticias | `CIERRE_POR_SILENCIO` | Solo si el usuario lo pide; el agente puede proponerlo pasados 30 días del envío, nunca cierra solo |
| Cierre con oferta aceptada o rechazada por él | `finalizar` con `resultado` | `oferta_aceptada` u `oferta_rechazada_por_usuario` |

1. Mostrar lo que se va a registrar (tipo, detalle y estado resultante) y esperar la confirmación del usuario.
2. `detalle`: lo que el usuario dijo, con la fecha del hecho y la evidencia si la hay (correo, mensaje, llamada). El evento queda con la fecha de hoy, así que una fecha anterior va en el `detalle`.
3. Si el CLI rechaza el evento (por ejemplo un segundo aviso de primer contacto, o un evento que no corresponde al estado), informar el motivo tal cual y no insistir ni buscar otra vía.

## 3. Recompensa

- Solo `PRIMER_CONTACTO_ENTREVISTA` puntúa (D16). El CLI crea el evento de recompensa en la misma operación: uno solo por postulación, con el valor de `recompensa_primer_contacto` de la configuración, el intento confirmado y las respuestas realmente enviadas (ID y versión). Las respuestas sin ID de la biblioteca no se premian.
- Repetir el aviso o reprocesar no duplica el premio. Si la operación se cortó entre el cambio de estado y el premio, `recompensar <id>` lo completa una sola vez.
- Rechazo, retiro y silencio no generan puntaje ni castigo. Segunda entrevista, oferta y contratación se registran, pero no puntúan.
- Informar al usuario, en una línea, qué respuestas quedaron asociadas. Es una asociación, no causalidad: no decir que una respuesta "funcionó". El resultado no modifica el perfil ni cambia solo la respuesta base (regla 7 de `CLAUDE.md`).

## 4. Cierre

Mostrar el estado resultante (`ver`) y preguntar si hay algo más que registrar en esa u otra postulación.

## Formato de las preguntas

- Cada pregunta de `AskUserQuestion` es autocontenida: lleva la postulación (empresa, cargo, estado), lo que se registraría y qué cambia con cada opción, sin depender del texto anterior.
- Una pregunta a la vez.
