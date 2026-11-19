---
name: adaptar_cv
description: Paso 0 del subflujo de postulación de Agente0 (adaptar el CV base a una vacante). Parte del CV base ATS del usuario y de una oportunidad registrada, ajusta titular, perfil, orden de habilidades y énfasis de las viñetas sin inventar nada, verifica los límites de tamaño, audita la veracidad y entrega el CV adaptado con un resumen de cambios y brechas para que el usuario lo apruebe. Usar cuando el usuario invoque /adaptar_cv <id de oportunidad>, pida adaptar su CV a una vacante o cuando el subflujo de postulación llegue al paso 0.
---

# adaptar_cv

Diseño: D7 (formato maestro y variantes), D8 (la carta no es parte de este paso) y la decisión de B3 (límites por bloque, auditoría y revisor) en `docs/decisiones.md`; checklist en `docs/investigacion_cv_ats.md` §8. Esta skill es genérica: no lleva datos de ningún usuario.

Alcance: producir y verificar un CV adaptado a una vacante. No postula, no sube archivos, no genera cartas (D8) y no modifica el CV base ni el perfil.

## Dónde queda cada cosa

Todo en los datos del usuario, junto a la vacante: `$AGENTE0_DATOS/oportunidades/<id>/cv/<fecha>/`, con el mismo ID de la oportunidad y de la futura postulación.

| Archivo | Qué es |
|---|---|
| `cv_ats.tex` y `cv_ats.pdf` | El CV adaptado (versión ATS) |
| `cv_ats.png` (`-1`, `-2`) | Render de cada página, para revisión visual |
| `auditoria.md` | Cada afirmación nueva o cambiada contra `perfil.md` |
| `resumen.md` | Cambios respecto del base, requisitos cubiertos, brechas y aprobación |

Una adaptación nueva de la misma vacante va en otra carpeta (`<fecha>-2`), nunca encima de la anterior. El `cv_ats.pdf` aprobado es el que la postulación copiará como instantánea (regla 5); aquí no se envía nada.

## 0. Preparación

1. Comprobar que `AGENTE0_DATOS` existe. Leer `oportunidades/<id>/oportunidad.json` y `publicacion.txt` (el texto literal puntuado). Si la oportunidad no está en `POTENCIAL` o `EN_POSTULACION`, decirlo y parar. Si ya existe una postulación para ese ID con envío confirmado, parar (antiduplicación, regla 4).
2. Leer `perfil/perfil.md` completo (en especial E6 a E13: límites de veracidad, brechas y herramientas que el usuario pidió dejar fuera del CV) e `intereses.md` (familias de CV).
3. Leer la última carpeta de `cv/base/<fecha>/`: `base_ats.tex`, `limites.json` y `base_ats_auditoria.md`. El CV base ATS es el maestro y la fuente del contenido (B3).
4. Leer el checklist de `docs/investigacion_cv_ats.md` §8 y la configuración (`configuracion.json`, campo `autonomia`).

## 1. Analizar la vacante

1. Requisitos y términos de la publicación, separados en: obligatorios, deseables y cultura o contexto.
2. Idioma: el del aviso. Español por defecto; una variante en inglés solo cuando el aviso esté en inglés o la empresa lo exija, con los mismos hechos y el mismo nivel de inglés declarado (investigación §6).
3. Para cada requisito, decidir con el perfil: cubierto (con la evidencia exacta), cubierto en parte, o brecha. Una palabra de la vacante no es una habilidad demostrada: sin evidencia, no entra al CV y va como brecha.
4. Titular: el cargo estándar del aviso solo si es verdad y el perfil lo permite como descriptor (nunca como cargo contractual); si no, el de la familia de cargos más cercana.

## 2. Qué se puede cambiar y qué no

Se adapta:
- Titular y perfil profesional.
- Orden de los grupos de HABILIDADES y de las habilidades dentro de cada grupo; rótulo del grupo cuando el aviso usa otro término equivalente y es cierto.
- Qué viñetas abren cada cargo y su orden, y la redacción de cada una para destacar lo pertinente a la vacante, sin agregar hechos.
- Orden y énfasis de los proyectos propios; una sección puede acortarse, pero no se inventa una nueva.
- Siglas y nombre completo cuando el aviso usa ambos.

No cambia nunca: cargos oficiales, empresas, fechas, educación, idiomas y su nivel, ni los límites de veracidad del perfil (E12). Las cifras van exactamente como el perfil las permite (aproximadas, agregadas, "potencial estimado" con su método, "en desarrollo").

Herramientas que el usuario pidió dejar fuera del CV (perfil E9) solo vuelven si él lo pide para esta vacante. Herramientas conocidas solo por proyectos propios siguen rotuladas como tales.

## 3. Escribir la adaptación

1. Crear `oportunidades/<id>/cv/<fecha>/` y copiar ahí `base_ats.tex` como `cv_ats.tex`. Cambiar el comentario inicial: indicar el ID de la oportunidad, la fecha y la versión base de la que parte. Cambiar `pdftitle` solo si el nombre del documento lo exige.
2. Editar solo los bloques de la sección 2. Respetar el límite de cada bloque de `limites.json`; si el texto nuevo no cabe, reescribir más corto. Nunca reducir la letra ni los márgenes.
3. No dejar texto oculto ni repetir palabras clave: cada término de la vacante aparece una vez con contexto (perfil o experiencia) y una en habilidades.

## 4. Verificar

```bash
python -m agente0 cv verificar <cv_ats.tex> <limites.json del CV base>
pdftoppm -png -r 110 cv_ats.pdf cv_ats
pdftotext cv_ats.pdf - | head -80
```

- `cv verificar` debe salir sin líneas (límites por bloque, páginas esperadas, desbordes, fuentes y ligaduras). Si falla, se reescribe el texto y se repite.
- Mirar el PNG de cada página (sin solapamientos ni líneas de una palabra) y leer la extracción de texto (orden: encabezado, perfil, experiencia, habilidades, educación; sin palabras partidas).
- Pasar el checklist de §8 de la investigación en lo que cambió. Entregar el PDF en la carpeta de la adaptación.

## 5. Auditar la veracidad

En `auditoria.md`, una tabla `afirmación nueva o cambiada -> respaldo en perfil.md` con la sección E# y su línea. Lo que no cambió respecto del base hereda la auditoría del base y no se repite. Si una afirmación no tiene respaldo, se quita o se pide el dato al usuario; no se infiere. Anotar las afirmaciones que se evitaron a propósito por no tener evidencia.

Revisor independiente: un subagente que contraste el CV adaptado con `perfil.md` solo si `autonomia` es 75 o más (cuando el usuario no ve el CV antes del envío). Con autonomía menor, el revisor es el propio usuario al aprobar.

## 6. Resumen de cambios y brechas

En `resumen.md`:
1. `diff -u` condensado: qué cambió respecto del base, bloque por bloque, y por qué.
2. Requisitos de la vacante: cubiertos (con su evidencia), cubiertos en parte y brechas, en tres listas cortas.
3. Qué se decidió no afirmar y qué dato podría cambiar la adaptación si el usuario lo confirma (se pregunta, no se asume).
4. Si el CV no es apto para el envío automático según las condiciones del usuario, decir cuál falla.

## 7. Presentar y cerrar

Mostrar al usuario el resumen y el render de la primera página (la leída primero) y esperar su aprobación; la compuerta de autonomía de §5.2 del diseño decide si se puede continuar sin ella. Con la aprobación, anotar al final de `resumen.md` la fecha, el nivel de autonomía vigente y quién aprobó (regla 5). Un cambio pedido por el usuario crea otra carpeta con fecha, no edita la aprobada.

No avanzar a la postulación: el subflujo continúa con B8.

## Formato de las preguntas

- Cada pregunta de `AskUserQuestion` es autocontenida: lleva la vacante, el cambio propuesto y qué pasa con cada opción, sin depender del texto anterior.
- Pedir al usuario solo lo que es suyo (qué decir de sí mismo, riesgos que asume). Lo que resuelven el perfil, la investigación o las decisiones registradas se decide y se informa con su fuente.
