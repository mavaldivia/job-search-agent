---
name: editar_respuestas
description: Operación 6 del menú de Agente0 (Editar respuestas tipo). Revisa, edita y amplía la biblioteca de respuestas tipo del usuario (hechos y narrativas, con variantes por familia de cargo) y fija las reglas para recuperarlas al postular. Usar cuando el usuario invoque /editar_respuestas, elija "Editar respuestas tipo" en el menú o cuando una postulación necesite una respuesta de la biblioteca.
---

# editar_respuestas

Diseño: D9 y su enmienda del 2026-11-19 en `docs/decisiones.md`. Esta skill es genérica: no lleva datos de ningún usuario; todo sale de su biblioteca en `$AGENTE0_DATOS/respuestas/`.

Alcance: la biblioteca de respuestas tipo. Sin acciones externas ni navegador. Nunca modifica una versión existente: editar es guardar la siguiente.

## Cómo está guardada

- `respuestas/<categoria>/v001_<fecha>.md` es la versión general; `respuestas/<categoria>/<variante>/v001_<fecha>.md`, la variante de una familia de cargo. ID estable: `<categoria>` o `<categoria>.<variante>`. La vigente es la versión más alta no rechazada.
- Cada archivo lleva `tipo` (`hecho`: se reutiliza literal y sale del perfil; `narrativa`: se ajusta a la vacante), `aprobada_por` (`usuario` o `agente`), `fuente` y `notas`. Una versión `agente` exige fuente.
- Las variantes se nombran `familia-<letra>` según las familias de CV de `perfil/intereses.md` (I1). Al recuperar: variante de la familia de la vacante; si no existe, la general; si no hay ninguna, no hay respuesta confirmada.
- Todo pasa por el CLI, que valida y no deja pisar versiones:

```bash
python -m agente0 respuestas listar | pendientes
python -m agente0 respuestas ver <categoria> [<variante>]
python -m agente0 respuestas versiones <categoria> [<variante>]
python -m agente0 respuestas guardar <<'EOF'
{"categoria": "motivacion", "texto": "...", "tipo": "narrativa", "aprobada_por": "usuario", "variante": "familia-a", "fuente": "I7", "notas": ""}
EOF
python -m agente0 respuestas revisar <<'EOF'
{"categoria": "idiomas", "version": 1, "resultado": "aprobada"}
EOF
```

## 0. Preparación

1. Comprobar que `AGENTE0_DATOS` existe y que `respuestas/` tiene contenido. Si está vacía, decirlo y ofrecer crear la primera categoría (§4).
2. Correr `respuestas listar` y `respuestas pendientes`. Leer `perfil/perfil.md` e `intereses.md` (I1) para contrastar y para conocer las familias.

## 1. Entrada

Mostrar cuántas categorías y variantes hay y cuántas versiones están pendientes de revisión. Ofrecer con `AskUserQuestion`: revisar pendientes (solo si hay), ver o editar una respuesta, agregar una categoría, agregar una variante por familia.

## 2. Revisar pendientes

Son versiones que guardó el agente con datos del perfil y el usuario aún no ve. De a una, mostrar: ID, texto y fuente. Opciones: aprobar (`revisar`, `aprobada`), editar (§3: al guardar la versión del usuario, la del agente queda `editada` sola) o rechazar (`revisar`, `rechazada`: deja de ser vigente; la próxima vez que haga falta, se pregunta al usuario).

## 3. Editar una respuesta

1. Mostrar la vigente y su historial (`versiones`).
2. Pedir el texto nuevo y esperar. Contrastarlo con `perfil.md`: si agrega una afirmación que el perfil no respalda (cifra, cargo, certificación, años, resultado), no guardar hasta que el usuario dé evidencia o la quite (regla de veracidad). Una palabra clave de una vacante no es una habilidad demostrada.
3. Mostrar antes y después, y guardar con `aprobada_por: usuario` solo tras su confirmación. Informar la versión creada. El texto anterior queda archivado en su versión.
4. Una respuesta `hecho` cambia solo si cambió el perfil: si el dato nuevo no está en `perfil.md`, derivar a "Actualizar perfil" primero.

## 4. Agregar categoría o variante

- Categoría nueva: acordar nombre (minúsculas con guiones), tipo y texto. Un `hecho` sale de datos confirmados del perfil; una `narrativa` se redacta con el usuario sin agregar nada que el perfil no diga.
- Variante por familia: solo cuando el texto general no calza con esa familia de cargo. Redactarla con el usuario y guardarla con `variante`. No crear variantes que solo reformulan la general.
- Nunca guardar como respuesta tipo las preguntas que exigen respuesta nueva cada vez: declaraciones legales o de consentimiento, conflictos de interés o parentescos, haber trabajado antes en la empresa, pruebas o casos y juicios sin evidencia en el perfil.

## 5. Recuperar una respuesta al postular

Reglas para el subflujo de postulación (la skill de postulación las aplica):

1. Clasificar la pregunta del formulario en una categoría y tomar la familia de CV de la vacante. Pedir `ver <categoria> <variante>`.
2. `hecho`: usar el dato literal, solo la parte que la pregunta pide. `narrativa`: ajustar el énfasis a la vacante sin agregar afirmaciones. Si el ajuste agrega una afirmación nueva, es una respuesta nueva y se trata como en el punto 4. Respetar las `notas` de la versión: son límites de veracidad.
3. Sin respuesta vigente (el CLI falla con "sin respuesta confirmada"):
   - Si la pregunta es de las que exigen respuesta nueva (§4, último punto) o no hay datos confirmados del perfil que la respalden: pausar esa pregunta, mostrar un borrador marcado y esperar. Si el usuario lo aprueba, guardarlo con `aprobada_por: usuario`. La postulación no se envía con la pregunta en blanco, ni siquiera al 100 %.
   - Si se puede armar solo con datos ya confirmados del perfil: guardarla con `aprobada_por: agente` y `fuente` (las secciones del perfil usadas), usarla sin pausar y avisar en la vista previa o el resumen que quedó pendiente de revisión. El agente solo crea la primera versión de un ID; nunca edita uno existente.
4. Registrar en la postulación el texto literal enviado junto con `respuesta_id` (el ID, con su variante si la hay) y `version`. Editar la biblioteca después no cambia lo ya enviado.
5. El aprendizaje (D16) puede sugerir una versión o proponer una edición; nunca la aplica solo.

## Formato de las preguntas

- Cada pregunta de `AskUserQuestion` es autocontenida: lleva el ID, el texto o la propuesta y qué se guarda con cada opción, sin depender del texto anterior.
- En una tanda de varias respuestas, anteponer `[van X de Y preguntas]`. Una pregunta a la vez.
