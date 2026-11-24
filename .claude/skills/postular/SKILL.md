---
name: postular
description: Pasos 1 a 3 del subflujo de postulación de Agente0 (postular a una vacante por el navegador). Con el CV adaptado y una oportunidad registrada, calcula la compuerta de autonomía (qué se hace solo y qué se aprueba, con límites diarios y pausa), valida la sesión del portal, prepara el formulario con respuestas confirmadas, congela la instantánea antes de enviar y pasa a POSTULADO solo con la confirmación visible del sitio. Probada con datos reales al 0 % (B8) y al 25 y 75 % (B11) en Get on Board; los niveles 50 y 100 % están implementados y probados solo con pruebas de integración. Usar cuando el usuario invoque /postular <id de oportunidad>, pida postular a una vacante o cuando el subflujo llegue al paso 1.
---

# postular

Diseño: D4 (navegador y pausas), D9 (respuestas tipo), D12 (autonomía), D13 (inicio) y D14 (estados y reintentos) en `docs/decisiones.md`; flujo en `docs/contexto_completo.md` §5.3 a §5.5. Esta skill es genérica: no lleva datos de ningún usuario.

Alcance: postular a **una** vacante (para varias, un subagente por vacante y de a uno por portal, ver §6). El nivel de autonomía decide qué pasos se hacen solos y cuáles se aprueban; lo calcula el código (`autonomia evaluar`), no tú de memoria. Al 0 % cada texto se muestra literal y se aprueba antes de escribirlo, y el envío final se confirma aparte.

## Reglas que no se negocian

- Nada se envía si la compuerta no lo permite: o el usuario aprobó **ese** envío en el chat, o `autonomia evaluar` lo marca `automatico` y `postulacion intentar` lo acepta. Una aprobación anterior (de un texto, de un paso, de otra vacante) no reemplaza la del envío.
- No se ingresan contraseñas, no se crean cuentas ni se aceptan términos o cookies por el usuario; ante login, CAPTCHA, 2FA o un campo sin respuesta con evidencia, pausar y pedir intervención (D4), en todo nivel, también al 100 %.
- Los textos salen de la biblioteca (`respuestas ver`) o se arman solo con datos confirmados del perfil (D9). Un texto guardado en el portal **no** es evidencia: contrastarlo con `perfil.md` y descartar lo que no esté respaldado (por ejemplo, años de experiencia que el perfil no confirma).
- Lo que el sitio guarda "para futuras postulaciones" modifica el perfil del usuario en el portal: avisarlo antes de escribir.
- `POSTULADO` exige la confirmación visible del sitio (D14). Sin ella queda `ENVIO_INTENTADO`: verificar en el portal o el correo antes de cualquier reintento, y no reenviar sin verificar.
- **Toda postulación confirmada queda en `$AGENTE0_DATOS/postulaciones.csv` con el status «Postulado sin validar»** (`postulacion confirmar` lo agrega solo; ver §5). El status es del usuario: lo cambia él cuando le llega el correo del portal que confirma la postulación, pide completar datos o pide una prueba. Nunca lo cambies tú ni lo marques como validado por haber visto la confirmación del sitio.

## 0. Preparación

1. Leer `oportunidades/<id>/oportunidad.json`, `publicacion.txt` y el último `cv/<fecha>/resumen.md` con su aprobación (o su nota «automático»). Sin CV adaptado, ofrecer `adaptar_cv` y parar. Si ya hay una postulación con ese ID (`postulacion ver <id>`) en un estado distinto de `PREPARADA`, parar (antiduplicación, regla 4).
2. Cargar `perfil/perfil.md` (E6 a E13) y `respuestas listar`. Si el portal es nuevo para el usuario, pedir consentimiento antes de la primera acción externa (D3). El portal tiene que estar en `fuentes listar`; si no, proponer agregarlo y esperar la aprobación del usuario.
3. **Renta de mercado y cuadre (B24)**: `python -m agente0 mercado evaluar <id>` con `{"rol", "seniority", "mercado", "presencialidad", "lejos_de_casa", "evidencia", "aplicar": true}` (`remota`, `hibrida`, `alta` o `total`; `seniority` es `Lead`, `Manager` o `Head`; `lejos_de_casa` según el domicilio de `perfil/perfil.md`). La propuesta depende del escalón del cargo: **general** (percentil 75 con `mercado.renta_tope_general`) o **exigente** (nivel Manager o Head, con presencialidad alta o total o lejos de casa: percentil 90 con `mercado.renta_maxima`); con mucho fit (eje «tengo» desde `mercado.fit_desde`) sube de su base hacia ese tope. Sin rango de mercado en Chile no se investiga por vacante: propone la renta estándar `mercado.renta_estandar` (general) o `mercado.renta_maxima` (exigente) y lo dice en `nota`; `investigar_mercado` corre solo si el usuario lo pide o `mercado listar` muestra el rango vencido. Si responde que el rango venció, o que no hay rango fuera de Chile o sin renta estándar configurada, correr `investigar_mercado` solo para esa combinación y repetir. Si el rango está en otra unidad que la renta mínima, pasar `minima_equivalente` y el tope del cargo (`tope_general_equivalente` en el escalón general con `mercado.renta_tope_general`, o `maxima_equivalente` en el resto), ambos con `renta convertir`. Si `cuadre.resultado` es `omitir`, la vacante queda `DESCARTADO` con el motivo y se avisa al usuario en una línea: no se adapta el CV ni se postula. Si no, `sugerida` es la renta que se propone declarar (a lo más el tope de la oferta y nunca bajo la mínima): pasa por la aprobación del usuario como todo monto (B17). Los montos en pesos salen en números cerrados, múltiplos de 100.000 o, si no cabe uno, de 50.000 (`mercado evaluar` y `renta convertir` lo hacen; no redondees a mano ni declares una cifra sin cerrar). En un lote, correrlo antes de adaptar el CV de cada vacante.

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

1. Revalidar la vigencia (botón de postular visible, sin aviso de cierre), con `find` o `get_page_text`. Si cerró: `oportunidad estado` a `CERRADO` y parar.
2. Validar la sesión (el encabezado muestra al usuario, no "Sign in"), con `find` o `get_page_text`. Si no hay, dejar la pestaña abierta en la vacante, pedir que inicie sesión a mano y esperar. Nunca entrar por él.
3. No tocar el banner de cookies salvo que bloquee el formulario; si hace falta, elegir lo mínimo con su permiso.

### Lectura económica del navegador

La navegación es lo que más tokens gasta, y casi todo es evitable: una captura completa o un `read_page` de la página entera cuestan mucho más que leer un campo. Orden de herramientas, de menor a mayor costo; usar la primera que alcance:

1. `get_page_text`: leer la vacante, el texto de las preguntas, la vista previa y el mensaje de confirmación. No muestra el valor de los campos.
2. `find`: ubicar un botón, un campo o un aviso concreto (devuelve hasta 20 referencias) en vez de leer la página. Devuelve también elementos ocultos (Computrabajo trae un «Postulado» con clase `hide` junto a «Postularme»): para vigencia, sesión o antiduplicación, confirmar con `javascript_tool` que el elemento está visible (`offsetParent` o `getClientRects().length`) antes de concluir.
3. `read_page` con `ref_id` del formulario o diálogo y `filter: interactive`. `filter: all` solo para ver preguntas ocultas o modales, y acotado con `ref_id`, `depth` o `max_chars`; nunca de la página entera.
4. Escribir con `form_input` por `ref`; leer el resultado con `javascript_tool` (`value`, largo, `checked`, texto del contador o del aviso de error). Esa lectura es la verificación de cada campo: no tomar captura para "ver cómo quedó" lo que se puede leer.
5. Clic con `ref` (o `scroll_to` con `ref`) en vez de coordenadas.
6. Captura, solo si lo visual es lo que importa: la evidencia de la confirmación (§4.5), la vista previa con el CV adjunto, un control personalizado cuyo estado no se refleja en el DOM (por ejemplo los de Aira) o decidir si hay CAPTCHA o login. Con `scale: 0.5` (cuesta un cuarto) o `zoom` sobre la `region` del campo, no a pantalla completa.

Antes de `file_upload`, comprobar con `javascript_tool` el `id`, `name` y `accept` del `input[type=file]` y la página donde está (la descripción de `find` no basta: en Computrabajo describió como «documentos» el campo de la foto). Si el archivo está en la carpeta de datos y `file_upload` lo rechaza, pedir `/add-dir` de esa carpeta o copiar el PDF (mismo hash) a la carpeta temporal de la sesión.

Además: encadenar con `browser_batch` los pasos que se pueden prever (llenar varios campos y leer sus valores en una sola ida), no repetir una lectura de una página que no cambió y recordar que las `ref` se pierden al navegar o al reacomodarse el formulario.

### Archivo por portal

Las lecciones de cada portal viven en `portales/` (en esta carpeta). Antes de leer el formulario, leer el de tu portal con `Read`: no cargarlos todos.

| Portal o plataforma del formulario | Archivo |
|---|---|
| Get on Board | `portales/getonboard.md` |
| Computrabajo | `portales/computrabajo.md` |
| Laborum, Trabajando.com | `portales/laborum_trabajando.md` |
| Himalayas (y el ATS de empresa al que lleva, por ejemplo Greenhouse) | `portales/himalayas.md` |
| Teamtailor | `portales/teamtailor.md` |
| Aira | `portales/aira.md` |
| Buk | `portales/buk.md` |

Un portal sin archivo se trabaja con las reglas de esta skill; al terminar, dejar la lección nueva en el reporte para que el agente principal cree su archivo.

## 3. Preparar el formulario

Avanzar paso a paso. En cada uno: leer los campos y proponer el texto literal con su fuente (ID y versión de la biblioteca, o el dato del perfil). Si `formulario` o `respuestas` son `aprobar`, esperar la aprobación antes de escribir; si son `aprobar_nuevas` o `automatico`, aplicar lo que dice §1.5. Después de cada escritura, verificar leyendo el campo (`javascript_tool`, ver «Lectura económica del navegador» en §2) que el texto quedó en el campo correcto y que su largo coincide con el aprobado; la captura solo si el campo no se puede leer.

- **Enfoque del teclado**: escribir con `form_input` por `ref`, que no depende del foco. Si un editor lo ignora y hay que teclear: un clic por referencia (`ref`) puede desplazar la página sin enfocar el campo, y entonces `cmd+a` selecciona la página y el texto no se escribe en ninguna parte. Hacer clic dentro del campo, confirmar el foco leyendo `document.activeElement` con `javascript_tool` y recién escribir. Si aparece un aviso de validación, el diseño se reacomoda: relocalizar el campo con `find` antes de cada clic, y recurrir a una captura a `scale: 0.5` solo si `find` no lo ubica.
- **Editores enriquecidos**: seleccionar todo con `cmd+a` dentro del campo enfocado y escribir encima. Comprobar el contador contra el largo aprobado.
- **Presionar "Next" guarda el paso** en el portal: pedir confirmación antes de cada uno si `formulario` es `aprobar`.
- **CV**: si el formulario deja elegir o subir CV, subir el adaptado aprobado (misma suma de verificación que el de `cv/<fecha>/`), con un nombre no genérico y una etiqueta. Antes de confirmar la subida, **desmarcar "actualizar mi perfil con este CV"** y dejar sin marcar "usar como predeterminado": vienen activados o no pedidos y reescriben el perfil del usuario.
- **Renta**: si el formulario la pide en otra moneda o base (por ejemplo bruto en USD) y la biblioteca no tiene esa cifra, convertir desde la renta líquida en moneda local de la biblioteca con `python -m agente0 renta convertir` (JSON por stdin: `liquido`, `pais`, `a_bruto`, `tasa`). Son dos pasos independientes (B17): (a) **tasa de cambio**: buscar la actual en una fuente oficial cada vez que haga falta, como unidades de moneda local por una de destino, y pasarla en `tasa`; no se guarda. (b) **factor líquido a bruto**: el código lo guarda por país con su fecha (`conversion_renta` en la configuración: vigencia de 30 días y banda de ±10 % sobre el líquido con que se calculó, porque el impuesto es progresivo). Si `convertir` responde que no hay factor, que venció o que el monto está fuera de la banda, investigarlo (en Chile: impuesto único por tramos, AFP, salud, seguro de cesantía y tope imponible vigentes, de fuentes oficiales; supuestos estándar: contrato dependiente indefinido, salud 7 %, AFP 10 % más la comisión promedio del mercado), calcular `factor` = bruto / líquido para ese monto, guardarlo con `renta factor guardar` (JSON por stdin: `pais` y `factor` con `investigado`, `liquido_referencia`, `factor`, `supuestos`, `fuentes`) y repetir `convertir`. Si la base no cambia (solo la moneda), basta la tasa. Mostrar el cálculo con tasa, factor y supuestos y esperar la aprobación del monto, en todo nivel: la renta es dato sensible. Guardarla como respuesta `agente` con fuente (tasa y su fecha, factor y su fecha de investigación). Si el sitio avisa que la cifra supera la oferta del cargo, informarlo al usuario con lo que se sabe del tope (se puede acotar probando valores en el campo, sin avanzar de paso, y se deja el campo en su valor aprobado o vacío al terminar) y dejar que decida; declarar siempre su expectativa real, nunca una menor para parecer barato. Registrar lo observado con `python -m agente0 oportunidad renta <id>` (JSON por stdin: `unidad`, `acepta_hasta` = mayor valor probado sin aviso, `avisa_desde` = menor valor que dispara el aviso, `evidencia` y, si la unidad del portal no es la de `renta_minima`, `minima_equivalente` = la renta mínima convertida a esa unidad con `renta convertir`) y repetir `autonomia evaluar`: la condición `renta_minima` usa ese tope (B19) y, si no hay un valor probado sin aviso que alcance la mínima, el envío pasa a aprobación.
- **Preguntas abiertas sin respuesta en la biblioteca**: armarlas con datos confirmados, reconociendo las brechas del perfil (E13) y sin afirmar nada de E12; mostrarlas todas juntas para aprobación, en todo nivel. Con su aprobación cuentan como documentadas.
- **Sí/No que la biblioteca no responde con certeza** (por ejemplo, disponibilidad en otra ciudad cuando el perfil dice «depende de la compensación»): no se contestan por el usuario; preguntarle. Si su respuesta vale solo para una prueba, dejarlo escrito en la `aprobacion` y no guardarla en la biblioteca.
- **RUT y otros documentos de identidad**: el agente no los escribe en ningún formulario, aunque el usuario lo pida y estén en la biblioteca. Deja el campo con los demás datos y el cursor al final, y el usuario escribe el número. En la instantánea el número se omite (`[escrito por el usuario en el formulario; no se registra aquí]`).
- **Lo que el usuario responde para un formulario** (un tramo de años, el nivel de una herramienta, ajustes para la entrevista): se guarda en `perfil.md` con fecha y «dicho por el usuario», para no volver a preguntarlo.
- **Formulario a medias en otra sesión**: una pestaña de una sesión de Chrome anterior (por ejemplo tras `/clear`) no se puede leer ni controlar. Si el usuario avanzó el formulario ahí, se rehace en una pestaña nueva; conviene terminar cada vacante en la sesión que la prepara.
- **Reintento tras un intento sin confirmar** (`no_postulada_antes` avisa «reintento»): antes de congelar de nuevo, revisar «Mis postulaciones» del portal en otra pestaña y confirmar que la vacante no figura enviada.
- **Portales con particularidades** (Get on Board: aviso «Low match» y subida de un CV nuevo; Computrabajo, Himalayas, Laborum y Trabajando.com, Teamtailor, Aira y Buk): ver «Archivo por portal» en §2.

## 4. Vista previa y envío

1. Abrir la vista previa. Si el sitio la llama "preview" y dice que no se ha enviado, verificar cada texto contra lo aprobado, leyéndola con `get_page_text`. Si la vista previa no muestra el CV adjunto, dejarlo dicho: la verificación fue la selección del paso del CV.
2. `postulacion crear` (JSON con `empresa`, `cargo`, `url`) y `oportunidad estado <id>` a `EN_POSTULACION`. El ID de la postulación es el de la oportunidad. Si ya existe en `PREPARADA` (cola o reintento), saltar este paso.
3. Repetir `autonomia evaluar` con los juicios finales. Si `acciones.envio` es `aprobar`, pedir la confirmación de envío con el resumen de lo que sale (textos, CV, renta, datos del perfil del portal que se comparten, `motivos`) y de lo irreversible. Si es `automatico`, mostrar igual el resumen en el chat, sin esperar.
4. Congelar antes de presionar: `postulacion intentar <id>` con `portal`, `cv` (ruta del PDF adaptado), `juicios`, `respuestas` (pregunta del sitio, texto literal, `respuesta_id` y `version` si vienen de la biblioteca), `renta_declarada` (la renta tal como salió en el formulario, con su moneda y base: «CLP 2.500.000 líquidos mensuales», «USD 3.100 brutos mensuales»; omitirla si el formulario no pide renta) y `renta_clp_liquida` (entero: lo declarado si ya es CLP líquido o, si el formulario pidió otra base o moneda, el líquido en CLP del que salió; omitirlo si no hay equivalente en CLP) y `aprobacion` (quién aprobó y qué, en el chat; obligatoria si `acciones.envio` es `aprobar`). El código vuelve a calcular la compuerta y guarda en la instantánea el nivel, las acciones y cada condición con su resultado; tú no declaras el nivel. Si responde con un bloqueo o pide la aprobación, no se presiona nada.
5. Presionar el botón de enviar y esperar. Leer el mensaje de éxito con `get_page_text` (es el `detalle` de §5) y tomar **una sola** captura con `save_to_disk`: es la evidencia de la instantánea y la única captura obligatoria por postulación.

## 5. Cierre

- Con el mensaje de éxito del sitio y la fila en el listado de postulaciones del portal: `postulacion confirmar <id>` con `tipo: confirmacion_visible`, el texto visto como `detalle` y la ruta de la captura. Pasa a `POSTULADO`. El mismo comando agrega la fila a `postulaciones.csv` (rol, empresa, portal, renta, fit «tengo» y «quiero», brecha, autonomía, enlace) con `status` = «Postulado sin validar», y no toca las filas que el usuario ya editó. Si el sitio o el correo de confirmación indican un paso siguiente (prueba, evaluación, formulario de datos), anotarlo en la columna `accionables` con `python -m agente0 planilla accionables <id>` (texto por stdin: qué falta, fecha límite si la hay y el enlace tal como lo mostró el sitio). Si el comando avisa un error de la planilla, la postulación ya quedó confirmada: no reintentar el envío, solo correr `python -m agente0 planilla sync`, que repone lo que falte y es idempotente.
- Si no hay confirmación clara: queda `ENVIO_INTENTADO`; verificar en el portal o el correo; si el envío falló sin enviarse, `postulacion fallido <id>`; si no se puede verificar, pedir intervención y no reenviar.
- Guardar como respuestas `agente` (`respuestas guardar`, con fuente) los textos nuevos que sirvan para otras vacantes; quedan pendientes de revisión del usuario.
- Cerrar la pestaña que se abrió, salvo que el usuario quiera conservarla.

## 6. Varias vacantes y subagentes (B25, B29)

- Para postular a más de una vacante del Top (agente principal): leer `carriles.md`. Se lanza un subagente por vacante, de a uno por portal.
- Si te lanzó el agente principal para una vacante (subagente): leer `subagente.md` antes de empezar. Trabajas una sola vacante de §0 a §5 y devuelves un reporte breve.
