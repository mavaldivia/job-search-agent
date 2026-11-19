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
```

- `registrar` es idempotente: repetirlo actualiza la vigencia y suma fuentes, y no resucita una vacante cerrada o descartada. La `url` oficial fija el ID, el mismo que usará la postulación: registrar solo cuando ya se conoce el enlace oficial.
- `evaluar` exige todos los criterios de `priorizacion.criterios` y los filtros activos que califica el agente (`modalidad_ubicacion`, `seniority`, `requisitos_obligatorios`, `cargo_mal_fit`). `renta` y `empresa_excluida` los decide el código. Si el texto de la publicación no cambió, el CLI conserva el puntaje guardado (estabilidad de D11); `"forzar": true` solo cuando cambió el perfil y el usuario acepta repuntuar.
- `ranking generar` descarta con motivo las que incumplen un filtro, pasa a `EN_POSTULACION` las que ya tienen postulación, y deja en `pendientes` las que aún no tienen evaluación vigente.

## 0. Preparación

1. Comprobar que `AGENTE0_DATOS` existe. Correr `configuracion ver` (parámetros vigentes: criterios, pesos, umbrales, Top, `ventana_dias`, filtros, renta mínima, empresas excluidas) y `ranking ultimo`.
2. Leer `perfil/perfil.md` e `intereses.md` (cargos, seniority, geografía, mal fit, familias de CV) y, si existe, el material de `origen/`.
3. `fuentes listar`. Si está vacía: proponer una lista inicial según el país del usuario (tipo, método `web` o `navegador`, riesgo) y guardarla con `fuentes guardar` solo tras su aprobación. El repo no trae catálogo por país.
4. Antes de la primera acción externa en un portal, pedir consentimiento (D3). Los portales por navegador usan la sesión abierta del usuario: si piden login, 2FA o CAPTCHA, pausar esa fuente y avisar; no pedir ni escribir credenciales.

## 1. Descubrir

- Por cada fuente activa: método `web` con búsqueda y lectura de páginas; método `navegador` con la extensión de Chrome, solo donde hace falta (D10). Ventana: vacantes publicadas en los últimos `ventana_dias`.
- Buscar con los cargos y la geografía del perfil, y descartar a simple vista el mal fit declarado en `intereses.md` antes de gastar lecturas. Sin ráfagas: lectura espaciada, solo las candidatas, nunca recorrer listados completos en un portal de riesgo alto.
- Una misma vacante en varias fuentes es un solo empleo: antes de registrar, correr `oportunidad listar` y comparar empresa y cargo. Las demás fuentes van en `fuentes` de la misma vacante.

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
3. Después: cambios respecto de la lista anterior (`NUEVA`, `SUBE`, `BAJA`, `SIN_CAMBIOS`, y las `salidas` con su motivo), las `descartadas` con su motivo (el usuario puede rescatarlas), cierres próximos (`cierra_el`), orden de ataque y las "sin verificar". El puntaje no es una probabilidad de entrevista.
4. Calibración de U4: mostrar cuáles cumplen los umbrales y cuáles no, e invitar al usuario a revisarlos con este primer ranking, antes de cualquier envío automático. Los umbrales y pesos se cambian en `configuracion.json`, nunca en código.

## 5. Portales sugeridos

Si el perfil sugiere una fuente que no está en la lista y vale la pena, proponerla con una línea de por qué e invitar al usuario a crear la cuenta si hace falta. El agente nunca crea la cuenta (D4). La fuente entra con `fuentes agregar` solo cuando el usuario la aprueba.

## 6. Acciones del usuario sobre el ranking

- Descartar una vacante: `oportunidad estado` a `DESCARTADO` con motivo "decisión del usuario".
- Rescatar una descartada: `oportunidad estado` a `POTENCIAL`; el código no la vuelve a descartar por filtros.
- Si el usuario pide postular, decir que el subflujo todavía no está construido.

## Formato de las preguntas

- Cada pregunta de `AskUserQuestion` es autocontenida: lleva el ID o la vacante y qué pasa con cada opción, sin depender del texto anterior.
- En una tanda de varias preguntas, anteponer `[van X de Y preguntas]`. Una pregunta a la vez.
