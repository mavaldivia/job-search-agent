# Consumo

En USD a precio de lista por modelo (no es lo que descuenta el plan; sirve para comparar). Se mide con `python -m agente0 consumo [N]` (sesiones) y `python -m agente0 consumo procesos` (por tipo).

## Costo por proceso (historial hasta el 25 nov)

| Proceso | Unidad | USD: mediana (rango) |
|---|---|---|
| Buscar vacantes | 1 fuente (26 casos) | 1,12 (0,32–2,42) |
| Buscar vacantes | corrida de 12 fuentes, ~2.400 resultados vistos | 18,7 (~0,77 por 100 vistos; ~0,22 por aviso leído) |
| Buscar vacantes | corrida de 10 fuentes con 2 días nuevos, ~540 vistos | 8,1 (~1,5 por 100 vistos) |
| Adaptar CV | 1 subagente (4 casos) | 0,94 (0,61–1,23) |
| Revisar CV | 1 subagente (6 casos) | 0,25 (0,20–1,04) |
| Preparar postulación | 1 subagente (11 casos) | 0,76 (0,27–3,52) |
| Postular | 1 envío confirmado, con sus subagentes (7 casos) | ~2,4 (0,47–7,7) |
| Sueldos | 1 rol y mercado (11 casos) | 0,53 (0,01–0,89) |

- El número de preguntas del formulario no explica el costo de postular con estos 7 casos. Los más caros son los que reconocieron un portal nuevo o corrigieron su perfil, y uno anterior al subagente por vacante, que carga trabajo de otras.
- Buscar tiene un costo fijo por fuente: cada subagente parte con ~37 k de contexto.

## Sesiones

| Fecha | Etapas | USD | Mejora |
|---|---|---|---|
| 19–25 nov (línea base) | todo el historial | ~215 (~70 % agente principal) | cortar sesiones tras una tarea pesada |
| 25 nov (antes del cierre) | todos, actualizar_estado, guardar, medición por proceso y plan de eficiencia | 2,74 (sin subagentes; contexto máx 277 k) | comando por proceso con precios por modelo; falta evitar referencias grandes y partir el análisis en otra sesión |
| 26 nov (carriles) | preparar y postular: 4 subagentes en 2 carriles y 1 revisor, 2 envíos confirmados con ayuda del usuario; todos (la sesión partió el 25) | 7,97 (3,30 subagentes; principal contexto máx 237 k) | revisar el destino externo y los procesos en curso antes de lanzar (aplicado); no adaptar el CV si el formulario está tras una aceptación del usuario (aplicado con su aprobación) |
| 26 nov (`/postular100`) | todos y corrida completa: 10 subagentes de búsqueda, 8 de preparación y 5 revisores; 3 envíos confirmados (1 automático, 2 con aprobación); un corte por límite de uso a mitad | 25,69 al empezar el cierre (búsqueda 9,41; preparación 7,02; revisores 1,33; principal 7,92, contexto máx 359 k); ~8,6 por envío | ninguno de los 3 envíos salió de la búsqueda de ese día (2 días después de la anterior). Aplicado: leer exigencias del formulario antes del CV en los portales nuevos. Propuesto: buscar solo si la última búsqueda tiene 3 días o más, y postular en una sesión limpia |
