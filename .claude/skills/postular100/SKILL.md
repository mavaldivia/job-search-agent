---
name: postular100
description: Corrida completa de Agente0 con autonomía 100 % solo mientras dura. Muestra el aviso de D12 y pide confirmación, activa 100 %, actualiza la búsqueda de vacantes y el ranking, postula al Top y vuelve al nivel anterior. Usar cuando el usuario invoque /postular100 o diga «ponte a postular nomás, actualiza el research y postula con autonomía 100 %».
---

# postular100

Comando que la origina: «ponte a postular nomás! actualiza el research y postula con autonomia 100%».

Diseño: D12 y la decisión del 2026-11-26 sobre `/postular100` en `docs/decisiones.md`. Esta skill es genérica: no lleva datos de ningún usuario. Solo encadena otras skills; sus reglas rigen completas.

## 1. Confirmar y activar

1. Comprobar `AGENTE0_DATOS` y leer el nivel vigente con `python -m agente0 configuracion ver` (es el **nivel previo**). Si ya es 100 y el último cambio de `configuracion/autonomia.jsonl` menciona `/postular100`, quedó de una corrida interrumpida: el nivel previo es su campo `de`.
2. Mostrar completo `python -m agente0 autonomia aviso 100` y pedir confirmación con `AskUserQuestion` (autocontenida). Invocar el comando no es la confirmación: se pide en cada corrida. Si no confirma, ofrecer la corrida al nivel previo o terminar.
3. `python -m agente0 configuracion editar` con `{"cambios": {"autonomia": 100}, "confirmacion": "<sus palabras> (/postular100, solo esta corrida; al terminar vuelve a <nivel previo> %)"}`.

## 2. Actualizar la búsqueda

Skill `actualizar_postulaciones_potenciales`, con un subagente por fuente (§7) y el ranking al final. La investigación de sueldos corre solo si un rango venció y la de términos solo si su recordatorio está vencido y el usuario la acepta. Se saltan las fuentes o portales que el usuario o `docs/tracking/todos.md` tengan en pausa.

## 3. Postular

`python -m agente0 carriles` y skill `postular` §6: un subagente por vacante, de a uno por portal, hasta agotar las vacantes de hoy dentro de los cupos. El CV se adapta con `adaptar_cv` en automático.

Lo que a 100 % sigue siendo del usuario (portales con tope, montos de renta, preguntas abiertas nuevas, login, CAPTCHA, 2FA, términos, RUT) no detiene el resto: queda `PREPARADA` o con su pestaña abierta y se le presenta todo junto.

## 4. Volver al nivel previo

Apenas no quede nada que pueda salir solo, y también si el usuario detiene la corrida o algo falla: `configuracion editar` con `{"cambios": {"autonomia": <nivel previo>}}` (bajar no pide confirmación). Se hace antes de entregarle el turno con la cola de pendientes. Verificarlo con `configuracion ver`.

## 5. Cierre

Reporte breve: enviadas y confirmadas, intentadas sin confirmar, pendientes del usuario con lo que falta en cada una, descartadas con su motivo, y el nivel en que quedó la configuración.
