# Consumo por sesión

Una línea por sesión, medida con `python -m agente0 consumo`. Equivalente = entrada + 2x escritura de caché de 1 h + 1,25x de 5 min + 0,1x lectura de caché + 5x salida (aproximado, no es lo que descuenta el plan).

| Fecha | Etapas | Equivalente | Mejora |
|---|---|---|---|
| 19–26 nov (línea base) | varias | ~138 M (~97 M principal, ~41 M subagentes) | cortar sesiones tras una tarea pesada |
| 25 nov (antes del cierre) | todos (incluye la regla y el comando), actualizar_estado | 0,62 M (sin subagentes; contexto inicial 54 k, máximo 116 k) | medir con el comando en vez de reescribir un script |
