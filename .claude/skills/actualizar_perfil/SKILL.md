---
name: actualizar_perfil
description: Operación 1 del menú de Agente0 (Actualizar perfil). Pone al día la experiencia del usuario desde la última revisión, por relato libre ("Cuéntame") o por preguntas de profundización ("Pregúntame"), guardando solo lo confirmado dato por dato. Usar cuando el usuario invoque /actualizar_perfil, elija "Actualizar perfil" en el menú o acepte el recordatorio de experiencia.
---

# actualizar_perfil

Diseño: `docs/onboarding.md` §3 (banco P1 a P8, detección de vacíos y reglas). Esta skill es genérica: no lleva datos de ningún usuario; todo sale del `perfil.md` de quien la corre.

Alcance: experiencia reciente (secciones E# de `perfil.md`). Intereses y configuración no se tocan aquí. Sin acciones externas ni navegador.

## 0. Preparación

1. Comprobar que `AGENTE0_DATOS` existe, que `$AGENTE0_DATOS/perfil.md` existe y que trae `onboarding_completo`. Si falta algo, decir que primero va el onboarding y terminar.
2. Leer `perfil.md` completo (incluidos los límites de veracidad E12 y las brechas E13) y `configuracion.json`.
3. Obtener la fecha de la última revisión: `python -m agente0 revision ultima` (usa la bitácora `revisiones_perfil.jsonl`; sin bitácora, la fecha del onboarding).

## 1. Entrada

Mostrar la fecha de la última revisión y los días transcurridos, y ofrecer los dos caminos con `AskUserQuestion`:

- **Cuéntame**: el usuario relata con sus palabras lo que ha hecho desde esa fecha.
- **Pregúntame**: el agente pregunta, empezando por lo que más probablemente cambió.

## 2. Cuéntame

1. Pedir el relato en texto libre y esperar. No interrumpir con preguntas hasta que termine.
2. Extraer datos candidatos (cargo, responsabilidad, logro, cifra, herramienta, proyecto, certificación, otro). Cada candidato lleva: el texto tal como lo dijo el usuario, la sección E# de `perfil.md` donde iría y si agrega, corrige o contradice algo existente. No completar ni inferir nada que el usuario no dijo.
3. Decir cuántos candidatos hay y presentarlos de a uno con `AskUserQuestion`: confirmar, corregir (el usuario escribe la versión correcta) o descartar.
4. Para un logro o una cifra, antes de confirmarlo preguntar cifra, cómo se midió y de dónde sale (P2). Sin respaldo, el dato se guarda sin la cifra o como `por_confirmar`, nunca como hecho.
5. Terminados los candidatos, pasar a la detección de vacíos (§4).

## 3. Pregúntame

1. Elegir del banco las preguntas que correspondan según lo débil del perfil y sumar los vacíos de §4. Mostrar la lista planeada y empezar por la que más haya podido cambiar.
2. Hacer una pregunta a la vez con `AskUserQuestion`. Cada respuesta se convierte en candidato y se confirma, corrige o descarta como en §2.3 y §2.4.

Banco de profundización:

| ID | Pregunta |
|---|---|
| P1 | ¿Qué cambió en tu trabajo desde la última revisión? ¿Nuevo cargo, equipo, alcance o responsabilidad? |
| P2 | ¿Qué lograste que puedas respaldar? ¿Con qué cifra, cómo se midió y de dónde sale? |
| P3 | ¿Qué herramientas o técnicas usaste por primera vez, y a qué nivel? |
| P4 | ¿Algún proyecto cambió de estado (de desarrollo a productivo, o se descontinuó)? ¿Hay proyectos nuevos? |
| P5 | ¿Cambió el número de personas que coordinas o a cargo, o tu responsabilidad sobre presupuesto? |
| P6 | ¿Hiciste cursos o certificaciones nuevos? |
| P7 | ¿Hay algo en tu perfil que ya no es cierto o que quieras matizar? |
| P8 | ¿Quieres corregir algo que haya salido en un CV o respuesta enviada? |

## 4. Detección de vacíos

En ambos caminos, buscar en `perfil.md` y preguntar por lo débil aunque el usuario no lo pida:

- logros sin cifra o sin fuente;
- proyectos sin estado;
- cifras sin método;
- datos `por_confirmar` abiertos;
- contradicciones sin resolver;
- datos cuya fecha `Confirmado` supera el plazo de `recordatorios_dias.experiencia`.

Preguntar por los más relevantes, hasta 3 por vuelta, y consultar si se sigue con más. Cada vacío se resuelve como un candidato más.

## 5. Reglas de guardado

- Solo se guarda lo confirmado. Se escribe en `perfil.md` dentro de su sección E# con `Edit`, junto con `- Fuente: dicho por el usuario, AAAA-MM-DD` y `- Confirmado: AAAA-MM-DD`. Lo que no se confirma no entra al CV ni a los formularios.
- Guardar cada dato al confirmarlo, no al final, para que una interrupción no pierda lo ya aprobado.
- Si el usuario no sabe o no quiere responder, registrar `sin_respuesta` o `por_confirmar` y seguir.
- Si un dato nuevo contradice uno existente, mostrar ambos y que el usuario decida cuál queda. No pisar en silencio; el valor anterior va en el resumen de la revisión (§6).
- No inferir cifras ni completar datos. Respetar los límites de veracidad E12: no proponer redacciones que los rompan.
- Un dato que no calza en ninguna sección E# o que es de intereses o configuración se anota aparte y se deriva a "Actualizar configuración".
- **Diario de vida laboral**: lo que el usuario dice que es contexto de cómo trabaja y no material de CV va a `$AGENTE0_DATOS/diario.md` (se crea si no existe), con fecha, texto, fuente y la marca "como diario y no como hito para el CV". Nada del diario entra al CV ni a los formularios salvo que el usuario lo marque como hito y se promueva a `perfil.md`. El detalle técnico interno de productos (configuraciones, tablas de prueba) no se guarda en `perfil.md`: si el usuario lo pide, va al diario.
- Un md de material previo (`solo_lectura/` u `origen/`) es insumo, no verdad: puede traer nombres de producto, idiomas o cifras mal atribuidos. Cada dato se confirma y, si el usuario lo corrige o lo niega, se registra la negación en la sección que corresponda cuando evita que el md se use después (por ejemplo, un idioma que no habla).

## 6. Cierre

1. Mostrar lo que cambió (agregado, corregido, descartado, pendiente) en pocas líneas.
2. Registrar la revisión, también si no hubo cambios o el usuario cortó antes (se registra lo confirmado hasta ahí):

```bash
python -m agente0 revision registrar <<'EOF'
{"modo": "cuentame", "cambios": [{"seccion": "E8b", "resumen": "antes: ...; ahora: ..."}]}
EOF
```

   `modo` es `cuentame` o `preguntame`; `seccion` es el ID de `perfil.md` (por ejemplo `E6` o `E8b`) o `diario` para una entrada de `diario.md`. La fecha se toma de hoy. Para un cambio con valor previo, el resumen lleva `antes:` y `ahora:`.
3. Si hubo un cambio relevante (cargo, logro, herramienta, certificación), preguntar si quiere revisar el CV base (operación 4). No modificar el CV por cuenta propia.

## Formato de las preguntas

- Cada pregunta de `AskUserQuestion` es autocontenida: lleva el dato propuesto, su sección y la duda, sin depender del texto anterior; las descripciones de las opciones explican qué se guarda con cada una.
- Anteponer el avance a cada pregunta: `[X/Y | avance Z%]`, con X = resueltas antes de la actual, Y = total del conjunto en curso (candidatos extraídos o preguntas planeadas) y Z = X/Y redondeado. Si aparecen candidatos nuevos, Y crece.
- Una pregunta a la vez. Sin tandas.
