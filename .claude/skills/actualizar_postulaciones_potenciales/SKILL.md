---
name: actualizar_postulaciones_potenciales
description: Operación 2 del menú de Agente0 (Actualizar postulaciones potenciales). Busca vacantes en las fuentes del usuario, verifica su vigencia en la fuente oficial, las puntúa con los ejes "quiero" y "tengo" de D11 y entrega el ranking con los cambios respecto del anterior. Termina en el ranking: el subflujo de postulación llega con B7 y B8. Usar cuando el usuario invoque /actualizar_postulaciones_potenciales, elija "Actualizar postulaciones potenciales" en el menú o pida actualizar el ranking de vacantes.
---

# actualizar_postulaciones_potenciales

Diseño: D10 (fuentes y vigencia), D11 (priorización), D13 y la decisión de B6 en `docs/decisiones.md`. Esta skill es genérica: no lleva datos de ningún usuario; todo sale de su perfil, su configuración y su lista de fuentes en `$AGENTE0_DATOS`.

Alcance: descubrir, verificar, puntuar y mostrar. No postula, no crea cuentas, no adapta CV. Aunque el usuario esté en un nivel de autonomía alto, aquí no se dispara el subflujo de D13 todavía.

## Cómo está guardado

El código decide estados, filtros, pesos, estabilidad y cambios; el agente descubre, verifica y puntúa con evidencia. Todo pasa por el CLI:

```bash
python -m agente0 configuracion ver
python -m agente0 fuentes listar | fuentes guardar | fuentes agregar      # JSON por stdin salvo listar
python -m agente0 oportunidad listar [POTENCIAL|EN_POSTULACION|CERRADO|DESCARTADO]
python -m agente0 oportunidad ver <id>
python -m agente0 oportunidad registrar <<'EOF'
{"empresa": "...", "cargo": "...", "url": "<enlace oficial>", "vigencia": {"verificada_el": "AAAA-MM-DD", "fuente": "<dónde se verificó>", "evidencia": "botón Solicitar visible, sin aviso de cierre"}, "fuentes": [{"nombre": "...", "url": "..."}], "publicada": "AAAA-MM-DD", "cierra_el": "AAAA-MM-DD", "renta_publicada": 0}
EOF
python -m agente0 oportunidad evaluar <id> <<'EOF'
{"publicacion": "<texto literal de la vacante>", "criterios": {"<criterio>": {"puntaje": 0, "evidencia": "..."}}, "filtros": {"<filtro>": {"excluye": false, "motivo": ""}}, "brecha_principal": "..."}
EOF
python -m agente0 oportunidad estado <id> <<'EOF'
{"nuevo": "DESCARTADO", "motivo": "decisión del usuario"}
EOF
python -m agente0 ranking generar | ranking ultimo
python -m agente0 busqueda resumen | busqueda vistas                                   # última búsqueda por fuente; vistas descartadas
python -m agente0 busqueda cupo | pendiente | conocida | consulta | vista              # JSON por stdin, ver §1
```

- `registrar` es idempotente: repetirlo actualiza la vigencia y suma fuentes, y no resucita una vacante cerrada o descartada. La `url` oficial fija el ID, el mismo que usará la postulación: registrar solo cuando ya se conoce el enlace oficial.
- `evaluar` exige todos los criterios de `priorizacion.criterios` y los filtros activos que califica el agente (`modalidad_ubicacion`, `seniority`, `requisitos_obligatorios`, `cargo_mal_fit`). `renta` y `empresa_excluida` los decide el código. Si el texto de la publicación no cambió, el CLI conserva el puntaje guardado (estabilidad de D11); `"forzar": true` solo cuando cambió el perfil y el usuario acepta repuntuar.
- `busquedas/registro.jsonl` (solo se agrega) guarda cada consulta hecha en cada fuente y cada vacante descartada a simple vista. De ahí salen la fecha de la última búsqueda por fuente, los tramos de fechas aún por revisar y el tope por corrida (`busqueda` en la configuración).
- `ranking generar` descarta con motivo las que incumplen un filtro, pasa a `EN_POSTULACION` las que ya tienen postulación, y deja en `pendientes` las que aún no tienen evaluación vigente.

## 0. Preparación

1. Comprobar que `AGENTE0_DATOS` existe. Correr `configuracion ver` (parámetros vigentes: criterios, pesos, umbrales, Top, `ventana_dias`, filtros, renta mínima, empresas excluidas) y `ranking ultimo`.
2. Leer `perfil/perfil.md` e `intereses.md` (cargos, seniority, geografía, mal fit, familias de CV) y, si existe, el material de `origen/`.
3. `fuentes listar` y `busqueda resumen` (qué fuentes nunca se han buscado y cuándo fue la última búsqueda de cada una). Si la lista está vacía: proponer una lista inicial según el país del usuario (tipo, método `web` o `navegador`, riesgo) y guardarla con `fuentes guardar` solo tras su aprobación. El repo no trae catálogo por país.
4. Antes de la primera acción externa en un portal, pedir consentimiento (D3). Los portales por navegador usan la sesión abierta del usuario: si piden login, 2FA o CAPTCHA, pausar esa fuente y avisar; no pedir ni escribir credenciales.

## 1. Descubrir

Reloj de términos (B22): si `python -m agente0 recordatorio ultima terminos` responde `sin_registro`, esta es la primera búsqueda con términos: al cerrar la corrida, `recordatorio operacion terminos` parte el reloj de 15 días. La renovación de los términos es de la skill `investigar_terminos`, no de esta.

Se recorren **todas** las fuentes activas, también las de riesgo medio y alto, con el consentimiento por portal de D3 y los límites de D4. Para cada fuente activa y cada variante de consulta:

1. **Variantes**: salen de `intereses.md` (cargos de prioridad alta y secundarios) con sinónimos y traducciones (Lead, Manager, Jefe, Head; español e inglés). Cada variante es una consulta distinta y se guarda con su texto exacto.
2. **Cupo**: `busqueda cupo` con `{"fuente": "..."}`. Si `primera_pasada` es `true` (primer día de búsqueda en esa fuente), se recorre completa, sin tope, con lectura espaciada y pausa ante login, CAPTCHA o aviso de bloqueo. Si no, se respetan `paginas_restantes` y `lecturas_restantes` (`null` es sin tope); al agotarse, se corta y se registra.
3. **Qué fechas faltan**: `busqueda pendiente` con `{"fuente": "...", "consulta": "..."}` devuelve los tramos de fechas de publicación aún no revisados dentro de `ventana_dias`. Ordenar el listado por fecha, de lo más nuevo a lo más antiguo, y filtrar por fecha en el portal cuando se pueda; lo anterior al tramo ya está revisado y en las bases.
4. **Recorrer**: paginación completa hasta cubrir el tramo más antiguo, el fin de los resultados o el tope. Por cada resultado, `busqueda conocida` con `{"url": "...", "empresa": "...", "cargo": "..."}`: si ya es una oportunidad o una vista, se salta sin leerla (si es la misma vacante venida de otra fuente, sumar esa fuente con `oportunidad registrar`). Una misma vacante en varias fuentes es un solo empleo: la pista de `conocida` por empresa y cargo la compara el agente antes de decidir.
5. **Resultado nuevo**: descartar a simple vista solo cuando el título o el resumen del listado muestran un mal fit declarado en `intereses.md`; se guarda con `busqueda vista` (`{"fuente", "empresa", "cargo", "url", "motivo"}`) y no se lee. Un portal difuso trae cientos de avisos ajenos o de nivel analista: esos solo suman al `vistas` de la consulta, y `busqueda vista` se reserva para los plausibles (jefaturas, familias secundarias) y para los leídos pero no registrados. Todo lo demás se lee, se verifica (§2) y se puntúa (§3), y se conserva aunque el puntaje salga bajo.
   - **Fuera de ventana**: si el aviso trae una fecha de publicación anterior a `ventana_dias`, no se registra como oportunidad; queda como vista con su motivo y la fecha, y se informa al usuario si sigue vigente y encaja, para que decida si la quiere. Si la quiere, se verifica de nuevo hoy y se registra con su `publicada` (y `cierra_el` si lo trae): el código no filtra por ventana, así que entra al ranking como cualquier otra, con la brecha «fuera de ventana» anotada. La decisión vale para esa vacante, no cambia `ventana_dias`.
   - **Aviso leído a medias**: si no se leyó completo, `publicacion` lo declara entre corchetes y la evidencia lo dice; no se completa de memoria.
6. **Cierre de la consulta**: `busqueda consulta` con `{"fuente", "consulta", "paginas", "lecturas", "vistas", "nuevas", "cubre_desde", "motivo_corte"}`. `lecturas` son las publicaciones leídas completas; `vistas`, los resultados del listado; `nuevas`, las vacantes que pasaron al registro como oportunidad o vista. `cubre_desde` es el inicio del tramo más antiguo si se recorrió todo, o la fecha de la publicación más antigua a la que se llegó si se cortó (`motivo_corte`: tope, login, CAPTCHA o bloqueo). Si el portal no deja ordenar por fecha, `cubre_desde` es hoy: esa búsqueda no da por revisado nada.

Un portal con búsqueda difusa (miles de resultados para un término genérico) se recorre con consultas más específicas y, si aun así no cabe, se corta con `motivo_corte` explícito. Si el portal no ordena por fecha pero la consulta se leyó entera, `cubre_desde` es el inicio de la ventana: lo revisado es el conjunto, no el orden. Al leer páginas con scripts en el navegador, espaciar las cargas (al menos 1 s) y no pasar de 40 s por llamada.

Ante login, 2FA, CAPTCHA o aviso de bloqueo, pausar esa fuente, registrar el corte y avisar al usuario; no pedir ni escribir credenciales.

## 2. Verificar vigencia

Cada candidata se verifica en la fuente oficial: portal corporativo, LinkedIn oficial, portal confiable, agregador, en ese orden. Entra como activa solo con botón Solicitar o Apply y sin aviso de cierre; si la fuente oficial dice cerrada, es cerrada aunque el agregador diga abierta.

- Verificada: `registrar` con la `url` oficial y la `vigencia` de hoy.
- Cerrada y ya registrada: `oportunidad estado` a `CERRADO` con el motivo. Cerrada y nueva: no se registra.
- No se pudo verificar (login, CAPTCHA, sitio caído): no se registra; va en el informe como "sin verificar". Las ya registradas se muestran con la fecha de su última verificación y se revalidan las del Top en cada corrida.

## 3. Puntuar

Para cada vacante registrada sin evaluación vigente (o con la publicación cambiada), leer la publicación completa y correr `evaluar`:

- Criterios: los de `priorizacion.criterios`, cada uno de 0 a 100 con su evidencia (cita de la vacante y del perfil). Referencia: 0–30 débil, 40–60 medio, 70–85 sólido, 90 o más excepcional. Los iniciales de D11: eje tengo (`ajuste_experiencia`, `compatibilidad_tecnica`, `factibilidad`) y eje quiero (`liderazgo_crecimiento`, `remuneracion`, `industria_empresa`).
- Veracidad: el puntaje de "tengo" sale de evidencia del perfil, no de que la vacante repita palabras clave. Sin evidencia, el puntaje baja y la `brecha_principal` lo dice. Sin renta publicada, no inventarla: `remuneracion` se puntúa con el nivel del cargo y de la empresa, y se declara en la evidencia. `renta_publicada` solo si la vacante la publica, en la misma unidad que `renta_minima`.
- Filtros: `excluye: true` con motivo solo si la vacante lo incumple de forma clara (requisito obligatorio que falta, modalidad incompatible, seniority desalineado, cargo de mal fit).
- No repuntuar una vacante cuyo texto no cambió: el CLI conserva el puntaje.

## 4. Ranking y presentación

1. Si todo está evaluado, `ranking generar` una sola vez. Si `pendientes` trae IDs, evaluarlos y generar de nuevo.
2. Mostrar la tabla del Top: posición, cargo y empresa, quiero, tengo, total, cumple umbrales, vigencia (fecha de verificación), fuente y enlace, brecha principal. Los dos ejes siempre por separado. Contribución por criterio si el usuario la pide.
3. Fuera del Top (`fuera_del_top`): las evaluadas y vigentes que no entraron, con sus dos ejes y si cumplen los umbrales. Si el usuario sube el Top o baja los umbrales, reaparecen sin volver a buscarlas. Luego, por fuente: la última búsqueda y las consultas distintas (`busqueda resumen`) y lo de esta corrida (vacantes nuevas, descartadas a simple vista y dónde se cortó).
4. Después: cambios respecto de la lista anterior (`NUEVA`, `SUBE`, `BAJA`, `SIN_CAMBIOS`, y las `salidas` con su motivo), las `descartadas` con su motivo (el usuario puede rescatarlas), cierres próximos (`cierra_el`), orden de ataque y las "sin verificar". El puntaje no es una probabilidad de entrevista.
5. Calibración de U4: mostrar cuáles cumplen los umbrales y cuáles no, e invitar al usuario a revisarlos con este primer ranking, antes de cualquier envío automático. Los umbrales y pesos se cambian en `configuracion.json`, nunca en código.

## 5. Portales sugeridos y búsqueda de fuentes nuevas (B20)

Si el perfil sugiere una fuente que no está en la lista y vale la pena, proponerla con una línea de por qué e invitar al usuario a crear la cuenta si hace falta. El agente nunca crea la cuenta (D4). Sin la instrucción del usuario de avanzar sin su aprobación, la fuente entra con `fuentes agregar` solo cuando él la aprueba.

Para investigar fuentes nuevas a pedido del usuario: un subagente por categoría (headhunters, portales corporativos, bolsas especializadas y agregadores, remoto internacional), solo con `WebSearch` y `WebFetch`, sin Chrome, sin login y sin datos personales: reciben el país, el nivel y las palabras de los cargos, y la lista de fuentes que ya existen. Cada candidata se valida con la ventana de 30 días (`ventana_dias`): sirve solo si tiene al menos una vacante afín publicada en ese período, con su enlace y su fecha; una fuente que no publica fechas (por ejemplo un ATS) se valida por vigencia y se dice así. Cada una entra con tipo, país, enlace, método (`web` si el listado se lee sin JavaScript, `navegador` si no) y riesgo, y con `activa: false` si exige cuenta que el usuario no tiene. En la primera búsqueda de la fuente nueva, una que no aporta nada afín se desactiva (`fuentes guardar` con `activa: false`) y queda anotada la razón en `docs/decisiones.md`. Un agregador sirve para descubrir: una vacante entra al registro solo con su enlace oficial resuelto.

## 6. Acciones del usuario sobre el ranking

- Descartar una vacante: `oportunidad estado` a `DESCARTADO` con motivo "decisión del usuario".
- Rescatar una descartada: `oportunidad estado` a `POTENCIAL`; el código no la vuelve a descartar por filtros.
- Si el usuario pide postular, decir que el subflujo todavía no está construido.

## 7. Búsqueda en paralelo por fuente (B25)

Las fuentes son independientes entre sí: en vez de recorrerlas una tras otra, el agente principal lanza **un subagente por fuente activa**, hasta `compuerta.carriles_en_paralelo` a la vez, y las demás esperan su turno. Cada subagente, con su propia pestaña, hace §1 a §3 solo para su fuente: `busqueda cupo`, `pendiente`, `conocida`, `registrar`, `evaluar`, `consulta` y `vista`, respetando el cupo y los topes de su riesgo; lee antes `perfil/perfil.md` e `intereses.md` para puntuar. Un subagente no agrega fuentes, no genera el ranking y no pide aprobaciones: ante login, CAPTCHA o bloqueo registra el corte y sigue con otra consulta o termina.

El agente principal, al juntar los reportes: (1) busca duplicados entre fuentes por empresa y cargo normalizados (el mismo aviso con la empresa escrita distinto) y los consolida; dos subagentes que registran la misma vacante a la vez pueden pisar la lista de fuentes de una de las dos, así que repasa `oportunidad listar` por esos casos; (2) corre `ranking generar` una sola vez y presenta §4. El reporte de cada subagente es breve: consultas hechas, vacantes nuevas con ID, descartadas a simple vista, cortes y su causa, y las dudas de duplicado.

## Formato de las preguntas

- Cada pregunta de `AskUserQuestion` es autocontenida: lleva el ID o la vacante y qué pasa con cada opción, sin depender del texto anterior.
- En una tanda de varias preguntas, anteponer `[van X de Y preguntas]`. Una pregunta a la vez.
