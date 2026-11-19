---
name: postular
description: Pasos 1 a 3 del subflujo de postulación de Agente0 (postular a una vacante por el navegador). Con el CV adaptado aprobado y una oportunidad registrada, valida la sesión del portal, prepara el formulario con respuestas confirmadas, pide aprobación en cada paso, congela la instantánea antes de enviar y pasa a POSTULADO solo con la confirmación visible del sitio. Probada al 0 % en Get on Board (B8). Usar cuando el usuario invoque /postular <id de oportunidad>, pida postular a una vacante o cuando el subflujo llegue al paso 1.
---

# postular

Diseño: D4 (navegador y pausas), D9 (respuestas tipo), D12 (autonomía), D13 (inicio) y D14 (estados y reintentos) en `docs/decisiones.md`; flujo en `docs/contexto_completo.md` §5.3 a §5.5. Esta skill es genérica: no lleva datos de ningún usuario.

Alcance: postular a **una** vacante. Probada solo al 0 % de autonomía y en un portal de riesgo bajo; los niveles superiores llegan con B11. Al 0 % cada texto se muestra literal y se aprueba antes de escribirlo, y el envío final se confirma aparte.

## Reglas que no se negocian

- Nada se envía sin la confirmación del usuario en el chat para ese envío. Una aprobación anterior (de un texto, de un paso) no la reemplaza.
- No se ingresan contraseñas, no se crean cuentas ni se aceptan términos o cookies por el usuario; ante login, CAPTCHA, 2FA o un campo sin respuesta con evidencia, pausar y pedir intervención (D4).
- Los textos salen de la biblioteca (`respuestas ver`) o se arman solo con datos confirmados del perfil (D9). Un texto guardado en el portal **no** es evidencia: contrastarlo con `perfil.md` y descartar lo que no esté respaldado (por ejemplo, años de experiencia que el perfil no confirma).
- Lo que el sitio guarda "para futuras postulaciones" modifica el perfil del usuario en el portal: avisarlo antes de escribir.
- `POSTULADO` exige la confirmación visible del sitio (D14). Sin ella queda `ENVIO_INTENTADO`: verificar en el portal o el correo antes de cualquier reintento, y no reenviar sin verificar.

## 0. Preparación

1. Leer `oportunidades/<id>/oportunidad.json`, `publicacion.txt` y el último `cv/<fecha>/resumen.md` con su aprobación. Sin CV adaptado aprobado, ofrecer `adaptar_cv` y parar. Si ya hay una postulación con ese ID (`postulacion ver <id>`), parar (antiduplicación, regla 4).
2. Comprobar el límite diario del portal (D12) contra las postulaciones de hoy en `postulaciones/`.
3. Cargar `perfil/perfil.md` (E6 a E13) y `respuestas listar`. Si el portal es nuevo para el usuario, pedir consentimiento antes de la primera acción externa (D3).

## 1. Navegador y sesión

Cargar las herramientas de Chrome en una sola búsqueda, abrir una pestaña nueva y ir a la URL oficial de la vacante.

1. Revalidar la vigencia (botón de postular visible, sin aviso de cierre). Si cerró: `oportunidad estado` a `CERRADO` y parar.
2. Validar la sesión (el encabezado muestra al usuario, no "Sign in"). Si no hay, dejar la pestaña abierta en la vacante, pedir que inicie sesión a mano y esperar. Nunca entrar por él.
3. No tocar el banner de cookies salvo que bloquee el formulario; si hace falta, elegir lo mínimo con su permiso.

## 2. Preparar el formulario

Avanzar paso a paso. En cada uno: leer los campos, proponer el texto literal con su fuente (ID y versión de la biblioteca, o el dato del perfil), esperar la aprobación y recién escribir. Después de cada escritura, verificar con captura que el texto quedó en el campo correcto, con el contador de caracteres.

- **Enfoque del teclado**: un clic por referencia (`ref`) puede desplazar la página sin enfocar el campo, y entonces `cmd+a` selecciona la página y el texto no se escribe en ninguna parte. Hacer clic con coordenadas dentro del campo, confirmar el foco en la captura y recién escribir. Las coordenadas cambian cuando aparece un aviso de validación: tomar captura antes de cada clic.
- **Editores enriquecidos**: seleccionar todo con `cmd+a` dentro del campo enfocado y escribir encima. Comprobar el contador contra el largo aprobado.
- **Presionar "Next" guarda el paso** en el portal: pedir confirmación antes de cada uno.
- **CV**: si el formulario deja elegir o subir CV, subir el adaptado aprobado (misma suma de verificación que el de `cv/<fecha>/`), con un nombre no genérico y una etiqueta. Antes de confirmar la subida, **desmarcar "actualizar mi perfil con este CV"** y dejar sin marcar "usar como predeterminado": vienen activados o no pedidos y reescriben el perfil del usuario.
- **Renta**: si el formulario la pide en otra moneda o base (por ejemplo bruto en USD) y la biblioteca no tiene esa cifra, calcularla con el dólar observado del día y los descuentos legales vigentes de la fuente oficial, mostrar el cálculo con sus supuestos y esperar la aprobación del monto. Guardarla como respuesta `agente` con fuente. Si el sitio avisa que la cifra supera la oferta del cargo, informarlo al usuario con lo que se sabe del tope (se puede acotar probando valores en el campo, sin avanzar de paso, y se deja el campo en su valor aprobado o vacío al terminar) y dejar que decida; declarar siempre su expectativa real, nunca una menor para parecer barato.
- **Preguntas abiertas sin respuesta en la biblioteca**: armarlas con datos confirmados, reconociendo las brechas del perfil (E13) y sin afirmar nada de E12; mostrarlas todas juntas para aprobación.

## 3. Vista previa y envío

1. Abrir la vista previa. Si el sitio la llama "preview" y dice que no se ha enviado, verificar cada texto contra lo aprobado. Si la vista previa no muestra el CV adjunto, dejarlo dicho: la verificación fue la selección del paso del CV.
2. `postulacion crear` (JSON con `empresa`, `cargo`, `url`) y `oportunidad estado <id>` a `EN_POSTULACION`. El ID de la postulación es el de la oportunidad.
3. Pedir la confirmación de envío con el resumen de lo que sale (textos, CV, renta, datos del perfil del portal que se comparten) y de lo irreversible.
4. Con el OK, congelar antes de presionar: `postulacion intentar <id>` con `autonomia`, `aprobacion` (quién aprobó y qué, en el chat), `cv` (ruta del PDF aprobado) y `respuestas` (pregunta del sitio, texto literal, `respuesta_id` y `version` si vienen de la biblioteca).
5. Presionar el botón de enviar, esperar y capturar la pantalla con `save_to_disk`.

## 4. Cierre

- Con el mensaje de éxito del sitio y la fila en el listado de postulaciones del portal: `postulacion confirmar <id>` con `tipo: confirmacion_visible`, el texto visto como `detalle` y la ruta de la captura. Pasa a `POSTULADO`.
- Si no hay confirmación clara: queda `ENVIO_INTENTADO`; verificar en el portal o el correo; si el envío falló sin enviarse, `postulacion fallido <id>`; si no se puede verificar, pedir intervención y no reenviar.
- Guardar como respuestas `agente` (`respuestas guardar`, con fuente) los textos nuevos que sirvan para otras vacantes; quedan pendientes de revisión del usuario.
- Cerrar la pestaña que se abrió, salvo que el usuario quiera conservarla.

## Pendiente de B11

Niveles 25 a 100 %: qué pasos pasan a ser automáticos, la cola de aprobación y las condiciones de auto-envío (renta publicada, umbrales) viven en la configuración del usuario; esta skill no los aplica todavía.
