# Varias vacantes a la vez: carriles por portal (B25, B29)

Lo lee el agente principal cuando va a postular a más de una vacante del Top. El subagente de cada vacante lee `subagente.md`, no este archivo.

`python -m agente0 carriles` reparte el Top en **carriles**, uno por portal, con el nivel efectivo, cómo se resuelve el envío (`envio` y `envio_condicionado`), el cupo del día, la espera por pausa, las `vacantes` de hoy (ya acotadas al cupo), las `en_espera` (quedan `POTENCIAL` para mañana, D13) y las `en_cola` (ya `PREPARADA`). Un carril es la **cola de un portal**: la pausa entre envíos y el cupo se miden por portal (B25).

## Cómo se reparte el trabajo (B29)

- **Un subagente por vacante, de a uno por portal.** Lanzas el subagente de la primera vacante de cada carril, hasta `en_paralelo` a la vez (`compuerta.carriles_en_paralelo`: cuenta subagentes simultáneos, y hay a lo más uno por portal). Cuando un subagente reporta, lanzas el de la siguiente vacante de ese portal; si hay más portales que cupo, los demás esperan su turno. Nunca dos subagentes a la vez en el mismo portal: la pausa y el cupo son del portal, y así el ciclo de cada vacante (`postulacion intentar`, clic de enviar y `postulacion confirmar`) termina antes de que empiece la siguiente, sin congelar varias a la vez.
- **Por qué uno por vacante**: cada vacante parte con el contexto limpio en vez de arrastrar las páginas, los formularios y los textos de las anteriores del carril. Un subagente por portal acumulaba contexto en cada vacante (en una corrida su contexto llegó a ~294k tokens). Lo que se pierde es lo aprendido dentro del portal; lo cubren el archivo del portal en `portales/` y las líneas que le pasas en el prompt.
- **Qué le pasas a cada subagente**: el ID de la oportunidad, el portal, la ruta de los datos, el `tabId` de su pestaña y la instrucción de leer `SKILL.md`, `subagente.md` y `portales/<portal>.md` si existe (carpeta de esta skill). Si la vacante anterior de ese portal dejó algo que sirve a la siguiente (por ejemplo «el envío exige que el usuario escriba el RUT»), una a tres líneas con eso. No le pegas reportes completos ni la conversación.
- **Si un subagente se detiene por pausa** (CAPTCHA, login, 2FA, términos, bloqueo): no lanzas más vacantes de ese portal hasta que el usuario lo resuelva, y los demás portales siguen. En portales de riesgo alto con señal de bloqueo no se reintenta.

## Antes de lanzar

- **Procesos en curso**: buscar en `perfil/perfil.md` (C12) las empresas del lote; la compuerta no carga ese historial. Si hay un proceso o una restricción, preguntar al usuario antes de crear la pestaña de esa empresa.
- **Sesión**: abres y validas la sesión de cada portal una sola vez y lanzas solo los portales con sesión; a los demás les informas al usuario qué debe abrir. Así no se gasta un subagente en un portal al que no se puede entrar.
- **Pestañas**: creas tú la pestaña de cada vacante justo antes de lanzar su subagente y se la entregas por `tabId`: con `tabs_context_mcp createIfEmpty` los subagentes se disputan la pestaña en blanco. Una pestaña que quedó en la vista previa esperando aprobación sigue abierta; la siguiente vacante del portal usa una nueva.
- **Sin carril**: las vacantes de `sin_carril` (por ejemplo un portal corporativo sin fuente activa) se informan al usuario y no se postulan.
- **Varias vacantes de una misma empresa**: `autonomia evaluar` cuenta las `PREPARADA` como proceso activo, así que solo la primera de la empresa pasa la condición `sin_proceso_activo`. Avisa al usuario cuando el lote tenga más de una vacante de la misma empresa.

## Al recibir los reportes

- **Aceptaciones pendientes**: las vacantes que se detuvieron antes de adaptar el CV se las muestras juntas al usuario (qué tiene que hacer, fit y brecha). Para las que haga, lanzas de nuevo su subagente en la pestaña que quedó; las que suelte no gastan CV.
- **Planilla**: cada `postulacion confirmar` agrega su fila a `postulaciones.csv`; con subagentes a la vez puede perderse una fila por carrera, así que corres `python -m agente0 planilla sync` una vez al juntar los reportes y confirmas que cada `POSTULADO` del lote esté en el archivo. Nadie edita el `status` salvo el usuario.
- **Archivos compartidos**: guardas tú los textos nuevos (`respuestas guardar`), la renta propuesta, la tabla de mercado y los factores de renta que vengan en los reportes, y anotas en `portales/<portal>.md` las lecciones nuevas de cada portal (sin datos del usuario: el repo es público). `ranking generar`, `fuentes` y la configuración también son solo tuyos.
- **Cola de aprobación**: muestras al usuario la cola por portal, cada ítem con su resumen y `motivos`, y con el OK de cada envío lo completas tú en la pestaña dejada, o repites §2 a §4 de `SKILL.md` si la pestaña ya no existe. Portales sin vista previa o que envían el CV del perfil: ver su archivo en `portales/` (por ejemplo `laborum_trabajando.md`).
