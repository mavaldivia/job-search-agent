---
name: investigar_terminos
description: Renueva los términos de búsqueda de vacantes de Agente0 (B22). Investiga cómo nombran hoy el mercado y los portales los cargos del perfil del usuario, propone términos nuevos con su razón y términos que rinden poco, y con la confirmación del usuario los suma a la lista de términos de sus intereses (I8) y reinicia el reloj de 15 días. La sugiere el agente al abrir el menú cuando pasan 15 días sin renovar (caso `terminos` de D15) y el usuario la acepta; también se invoca con /investigar_terminos.
---

# investigar_terminos

Diseño: B22 y D15 en `docs/decisiones.md`. Esta skill es genérica: no lleva datos de ningún usuario. Los términos del usuario viven en `$AGENTE0_DATOS/perfil/intereses.md` (sección de términos de búsqueda, I8). Solo lee la web; no usa el navegador del usuario ni busca vacantes: eso es de `actualizar_postulaciones_potenciales`.

Regla: el agente **propone** y el usuario **confirma**. Ningún término entra a la lista ni sale de ella sin su OK (la lista es dato del usuario, no del agente).

## 0. Preparación

1. `python -m agente0 recordatorio ultima terminos` (la fecha de la última renovación, o `sin_registro`) y leer en `intereses.md` los cargos de I1, los filtros de I5 y la lista vigente de términos (I8), incluidos los que el usuario ya rechazó.
2. `python -m agente0 busqueda resumen`: qué consultas distintas se han hecho por fuente. Para cada término, ver en `busquedas/registro.jsonl` cuántas vacantes nuevas dio en sus últimas corridas (`nuevas`): un término con 0 nuevas en dos corridas o más es candidato a retirar.

## 1. Investigar

Un subagente por familia de cargo del perfil (las «familias de CV» de I1; hasta `compuerta.carriles_en_paralelo` a la vez), con `WebSearch` y `WebFetch` solamente, sin Chrome y sin datos personales: reciben el país, el nivel buscado y las palabras de la familia, nada más. Cada uno lee avisos publicados en los últimos 30 días en portales públicos del país del usuario y entrega: los títulos de cargo que **realmente aparecen** en los avisos de esa familia y nivel, con cuántos avisos los usan y 2 enlaces de ejemplo, y los sinónimos en español y en inglés. Los que no aparecen en ningún aviso reciente no se proponen.

## 2. Proponer

1. Comparar con la lista vigente y quedarse con lo que falta. Cada término propuesto lleva su razón en una línea (cuántos avisos recientes lo usan y un ejemplo con enlace). Máximo 15 por renovación.
2. Aparte, los términos de la lista que rindieron poco (candidatos a retirar), con su cifra de vacantes nuevas.
3. Un mal fit de I5 nunca se propone aunque el mercado lo use.

## 3. Confirmar y guardar

1. Una pregunta de `AskUserQuestion` autocontenida y de selección múltiple con los términos propuestos (cada opción lleva el término y su razón) y otra con los candidatos a retirar. Sin respuesta, no se guarda nada.
2. Los confirmados se suman a I8 con su fecha y la fuente «renovación de términos AAAA-MM-DD»; los que el usuario rechaza se anotan como rechazados para no volver a proponerlos; los retirados se marcan como retirados con su fecha (no se borran: la lista queda como historial). Un término nuevo no hereda lo cubierto por otros: `busqueda pendiente` devuelve para él toda la ventana en la próxima corrida de la operación 2.
3. Registrar la renovación: `python -m agente0 recordatorio operacion terminos` (aunque el usuario haya confirmado cero cambios: la lista se revisó).

## 4. Cierre

Decir en dos líneas qué entró, qué salió y cuándo vuelve a tocar (en `recordatorios_dias.terminos` días). Si el usuario dijo «ahora no» al recordatorio, no se registra la operación: el caso sigue vencido (D15).
