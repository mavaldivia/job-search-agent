---
name: postular
description: Pasos 1 a 3 del subflujo de postulación de Agente0 (postular a una vacante por el navegador). Con el CV adaptado y una oportunidad registrada, calcula la compuerta de autonomía (qué se hace solo y qué se aprueba, con límites diarios y pausa), valida la sesión del portal, prepara el formulario con respuestas confirmadas, congela la instantánea antes de enviar y pasa a POSTULADO solo con la confirmación visible del sitio. Probada con datos reales al 0 % (B8) y al 25 y 75 % (B11) en Get on Board; los niveles 50 y 100 % están implementados y probados solo con pruebas de integración. Usar cuando el usuario invoque /postular <id de oportunidad>, pida postular a una vacante o cuando el subflujo llegue al paso 1.
---

# postular

Diseño: D4 (navegador y pausas), D9 (respuestas tipo), D12 (autonomía), D13 (inicio) y D14 (estados y reintentos) en `docs/decisiones.md`; flujo en `docs/contexto_completo.md` §5.3 a §5.5. Esta skill es genérica: no lleva datos de ningún usuario.

Alcance: postular a **una** vacante. El nivel de autonomía decide qué pasos se hacen solos y cuáles se aprueban; lo calcula el código (`autonomia evaluar`), no tú de memoria. Al 0 % cada texto se muestra literal y se aprueba antes de escribirlo, y el envío final se confirma aparte.

## Reglas que no se negocian

- Nada se envía si la compuerta no lo permite: o el usuario aprobó **ese** envío en el chat, o `autonomia evaluar` lo marca `automatico` y `postulacion intentar` lo acepta. Una aprobación anterior (de un texto, de un paso, de otra vacante) no reemplaza la del envío.
- No se ingresan contraseñas, no se crean cuentas ni se aceptan términos o cookies por el usuario; ante login, CAPTCHA, 2FA o un campo sin respuesta con evidencia, pausar y pedir intervención (D4), en todo nivel, también al 100 %.
- Los textos salen de la biblioteca (`respuestas ver`) o se arman solo con datos confirmados del perfil (D9). Un texto guardado en el portal **no** es evidencia: contrastarlo con `perfil.md` y descartar lo que no esté respaldado (por ejemplo, años de experiencia que el perfil no confirma).
- Lo que el sitio guarda "para futuras postulaciones" modifica el perfil del usuario en el portal: avisarlo antes de escribir.
- `POSTULADO` exige la confirmación visible del sitio (D14). Sin ella queda `ENVIO_INTENTADO`: verificar en el portal o el correo antes de cualquier reintento, y no reenviar sin verificar.

## 0. Preparación

1. Leer `oportunidades/<id>/oportunidad.json`, `publicacion.txt` y el último `cv/<fecha>/resumen.md` con su aprobación (o su nota «automático»). Sin CV adaptado, ofrecer `adaptar_cv` y parar. Si ya hay una postulación con ese ID (`postulacion ver <id>`) en un estado distinto de `PREPARADA`, parar (antiduplicación, regla 4).
2. Cargar `perfil/perfil.md` (E6 a E13) y `respuestas listar`. Si el portal es nuevo para el usuario, pedir consentimiento antes de la primera acción externa (D3). El portal tiene que estar en `fuentes listar`; si no, proponer agregarlo y esperar la aprobación del usuario.

## 1. Compuerta de autonomía (D12)

1. Armar los juicios que solo tú puedes dar, cada uno con su evidencia:
   - `seniority.valor`: el nivel del cargo tal como lo dice la publicación. Se compara con `compuerta.seniority_permitido` de `configuracion ver`.
   - `ubicacion.valor`: una de las `compuerta.ubicaciones_permitidas`, o la que corresponda si ninguna calza.
   - `cv_auditado.cumple`: la auditoría de veracidad de `cv/<fecha>/auditoria.md` quedó aprobada.
   - `respuestas_documentadas.cumple`: cada pregunta del formulario tiene respuesta en la biblioteca o dato confirmado del perfil. Lo que no esté (renta en otra moneda, preguntas abiertas nuevas) no cuenta como documentado hasta que el usuario apruebe ese texto en el chat.
2. `python -m agente0 autonomia evaluar <id>` con `{"portal": "<nombre en fuentes>", "juicios": {...}}`. Devuelve `nivel_efectivo` (con el tope del portal), `acciones` (`cv`, `respuestas`, `formulario`, `envio`), `condiciones`, `bloqueos` y `motivos`. Mostrarle al usuario el nivel efectivo y, si es menor al configurado, por qué.
3. Repetirlo cuando cambie un juicio (por ejemplo, al leer el formulario y saber si hay preguntas sin respuesta). Antes de conocer el formulario, `cv_auditado` y `respuestas_documentadas` pueden ir sin juicio: el resultado `no_evaluada` sirve solo para ver el nivel y los límites.
4. **Bloqueos**: no se continúa con esta vacante hasta resolverlos. Vigencia no verificada hoy: revalidar en el portal. CV sin auditoría o respuesta sin documentar: pedir la decisión al usuario. Empresa excluida o ya postulada: parar. Límite diario: dejar la vacante pendiente hasta mañana. Pausa entre envíos (`espera_segundos`): esperar o dejar la vacante en la cola; no saltarse la pausa.
5. **Qué hacer según `acciones`**:
   - `aprobar`: mostrar lo que se hará y esperar el OK del usuario.
   - `aprobar_nuevas` (respuestas al 50 %): usar sin preguntar las respuestas aprobadas de la biblioteca; mostrar para aprobación las armadas por ti, las nuevas y las sensibles (renta, datos personales).
   - `automatico`: hacerlo sin preguntar, siempre dentro de las pausas de D4.
6. **Cola de aprobación**: si `acciones.envio` es `aprobar` (por nivel, tope del portal, excepción o condición de preferencia incumplida al 75 %), dejar todo preparado, mostrar el resumen con los `motivos` y esperar el OK explícito. Si el usuario no aprueba ahora, la postulación queda `PREPARADA` y se retoma con `/postular <id>`. No hay segundo plano (D1).

## 2. Navegador y sesión

Cargar las herramientas de Chrome en una sola búsqueda, abrir una pestaña nueva y ir a la URL oficial de la vacante.

1. Revalidar la vigencia (botón de postular visible, sin aviso de cierre). Si cerró: `oportunidad estado` a `CERRADO` y parar.
2. Validar la sesión (el encabezado muestra al usuario, no "Sign in"). Si no hay, dejar la pestaña abierta en la vacante, pedir que inicie sesión a mano y esperar. Nunca entrar por él.
3. No tocar el banner de cookies salvo que bloquee el formulario; si hace falta, elegir lo mínimo con su permiso.

## 3. Preparar el formulario

Avanzar paso a paso. En cada uno: leer los campos y proponer el texto literal con su fuente (ID y versión de la biblioteca, o el dato del perfil). Si `formulario` o `respuestas` son `aprobar`, esperar la aprobación antes de escribir; si son `aprobar_nuevas` o `automatico`, aplicar lo que dice §1.5. Después de cada escritura, verificar con captura que el texto quedó en el campo correcto, con el contador de caracteres.

- **Enfoque del teclado**: un clic por referencia (`ref`) puede desplazar la página sin enfocar el campo, y entonces `cmd+a` selecciona la página y el texto no se escribe en ninguna parte. Hacer clic con coordenadas dentro del campo, confirmar el foco en la captura y recién escribir. Las coordenadas cambian cuando aparece un aviso de validación: tomar captura antes de cada clic.
- **Editores enriquecidos**: seleccionar todo con `cmd+a` dentro del campo enfocado y escribir encima. Comprobar el contador contra el largo aprobado.
- **Presionar "Next" guarda el paso** en el portal: pedir confirmación antes de cada uno si `formulario` es `aprobar`.
- **CV**: si el formulario deja elegir o subir CV, subir el adaptado aprobado (misma suma de verificación que el de `cv/<fecha>/`), con un nombre no genérico y una etiqueta. Antes de confirmar la subida, **desmarcar "actualizar mi perfil con este CV"** y dejar sin marcar "usar como predeterminado": vienen activados o no pedidos y reescriben el perfil del usuario.
- **Renta**: si el formulario la pide en otra moneda o base (por ejemplo bruto en USD) y la biblioteca no tiene esa cifra, convertir desde la renta líquida en moneda local de la biblioteca con `python -m agente0 renta convertir` (JSON por stdin: `liquido`, `pais`, `a_bruto`, `tasa`). Son dos pasos independientes (B17): (a) **tasa de cambio**: buscar la actual en una fuente oficial cada vez que haga falta, como unidades de moneda local por una de destino, y pasarla en `tasa`; no se guarda. (b) **factor líquido a bruto**: el código lo guarda por país con su fecha (`conversion_renta` en la configuración: vigencia de 30 días y banda de ±10 % sobre el líquido con que se calculó, porque el impuesto es progresivo). Si `convertir` responde que no hay factor, que venció o que el monto está fuera de la banda, investigarlo (en Chile: impuesto único por tramos, AFP, salud, seguro de cesantía y tope imponible vigentes, de fuentes oficiales; supuestos estándar: contrato dependiente indefinido, salud 7 %, AFP 10 % más la comisión promedio del mercado), calcular `factor` = bruto / líquido para ese monto, guardarlo con `renta factor guardar` (JSON por stdin: `pais` y `factor` con `investigado`, `liquido_referencia`, `factor`, `supuestos`, `fuentes`) y repetir `convertir`. Si la base no cambia (solo la moneda), basta la tasa. Mostrar el cálculo con tasa, factor y supuestos y esperar la aprobación del monto, en todo nivel: la renta es dato sensible. Guardarla como respuesta `agente` con fuente (tasa y su fecha, factor y su fecha de investigación). Si el sitio avisa que la cifra supera la oferta del cargo, informarlo al usuario con lo que se sabe del tope (se puede acotar probando valores en el campo, sin avanzar de paso, y se deja el campo en su valor aprobado o vacío al terminar) y dejar que decida; declarar siempre su expectativa real, nunca una menor para parecer barato. Desde el 75 %, si el tope acotado queda en o bajo la renta mínima del usuario, preguntar antes de enviar aunque la compuerta marque el envío como automático: ella no ve ese aviso (B19).
- **Preguntas abiertas sin respuesta en la biblioteca**: armarlas con datos confirmados, reconociendo las brechas del perfil (E13) y sin afirmar nada de E12; mostrarlas todas juntas para aprobación, en todo nivel. Con su aprobación cuentan como documentadas.
- **Sí/No que la biblioteca no responde con certeza** (por ejemplo, disponibilidad en otra ciudad cuando el perfil dice «depende de la compensación»): no se contestan por el usuario; preguntarle. Si su respuesta vale solo para una prueba, dejarlo escrito en la `aprobacion` y no guardarla en la biblioteca.
- **Aviso de coincidencia baja** (Get on Board muestra «Low match» con «Apply anyway» antes del formulario): es una advertencia del sitio, no un bloqueo. El enlace abre el formulario sin enviar; incluir el aviso en el resumen de la confirmación de envío.
- **Subir un CV nuevo**: el campo de archivo solo recibe el PDF con el modal «Upload a new resume» abierto; subirlo antes no lo adjunta. Después de cada «Next» la página se reacomoda: tomar captura antes del siguiente clic para no caer en otro campo.

## 4. Vista previa y envío

1. Abrir la vista previa. Si el sitio la llama "preview" y dice que no se ha enviado, verificar cada texto contra lo aprobado. Si la vista previa no muestra el CV adjunto, dejarlo dicho: la verificación fue la selección del paso del CV.
2. `postulacion crear` (JSON con `empresa`, `cargo`, `url`) y `oportunidad estado <id>` a `EN_POSTULACION`. El ID de la postulación es el de la oportunidad. Si ya existe en `PREPARADA` (cola o reintento), saltar este paso.
3. Repetir `autonomia evaluar` con los juicios finales. Si `acciones.envio` es `aprobar`, pedir la confirmación de envío con el resumen de lo que sale (textos, CV, renta, datos del perfil del portal que se comparten, `motivos`) y de lo irreversible. Si es `automatico`, mostrar igual el resumen en el chat, sin esperar.
4. Congelar antes de presionar: `postulacion intentar <id>` con `portal`, `cv` (ruta del PDF adaptado), `juicios`, `respuestas` (pregunta del sitio, texto literal, `respuesta_id` y `version` si vienen de la biblioteca) y `aprobacion` (quién aprobó y qué, en el chat; obligatoria si `acciones.envio` es `aprobar`). El código vuelve a calcular la compuerta y guarda en la instantánea el nivel, las acciones y cada condición con su resultado; tú no declaras el nivel. Si responde con un bloqueo o pide la aprobación, no se presiona nada.
5. Presionar el botón de enviar, esperar y capturar la pantalla con `save_to_disk`.

## 5. Cierre

- Con el mensaje de éxito del sitio y la fila en el listado de postulaciones del portal: `postulacion confirmar <id>` con `tipo: confirmacion_visible`, el texto visto como `detalle` y la ruta de la captura. Pasa a `POSTULADO`.
- Si no hay confirmación clara: queda `ENVIO_INTENTADO`; verificar en el portal o el correo; si el envío falló sin enviarse, `postulacion fallido <id>`; si no se puede verificar, pedir intervención y no reenviar.
- Guardar como respuestas `agente` (`respuestas guardar`, con fuente) los textos nuevos que sirvan para otras vacantes; quedan pendientes de revisión del usuario.
- Cerrar la pestaña que se abrió, salvo que el usuario quiera conservarla.
