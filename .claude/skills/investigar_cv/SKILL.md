---
name: investigar_cv
description: Mitad "investigar mejoras del CV para ATS" de la operación 4 de Agente0. Actualiza (o crea si falta) el documento vivo docs/investigacion_cv_ats.md con buenas prácticas de CV para ATS y para reclutadores, y contrasta con él el CV base del usuario. La sugiere el agente al abrir el menú cuando pasan 30 días sin uso (reloj de CV base, D15) y el usuario la acepta; también se puede invocar con /investigar_cv, con un tema opcional.
---

# investigar_cv

Diseño: decisión B3 (2026-11-18) y D15 en `docs/decisiones.md`. Esta skill es genérica: no lleva datos de ningún usuario. Solo lee la web; no envía nada ni usa el navegador del usuario.

## 0. Preparación

1. Leer `docs/investigacion_cv_ats.md` completo, incluidos "Cómo actualizar este documento" y el registro de cambios. Si no existe, crearlo con la misma estructura: cabecera "Última actualización", "Cómo actualizar este documento", resumen ejecutivo, secciones con `Verificado`, `Fuentes` (marca `[F]` leída entera, `[B]` solo resumen de búsqueda) y `Pendiente de verificar`, tabla práctica-evidencia-fuerza, checklist y registro de cambios.
2. Si el usuario dio un tema (por ejemplo "ATS en LinkedIn"), acotar a él. Sin tema, priorizar: secciones con más fuentes `[B]`, los "Pendiente de verificar" y las secciones con la fecha `Verificado` más antigua.

## 1. Investigar

- `WebSearch` en modo estándar; "extended" solo si un resultado sale flojo o desactualizado. `WebFetch` para leer las fuentes enteras.
- Preferir fuentes primarias y recientes: documentación de ATS (Greenhouse, Workday, Lever, SmartRecruiters, iCIMS, SAP, Oracle) y portales de empleo locales del usuario según su país (`$AGENTE0_DATOS/perfil/intereses.md`).
- Distinguir evidencia de folclore y anotar la fuerza de cada hallazgo (escala del documento). Citar la URL de cada afirmación.

## 2. Actualizar el documento

1. Conservar lo vigente; corregir o ampliar solo lo que cambió. Si dos fuentes se contradicen, anotar ambas y la decisión, sin borrar una.
2. Actualizar `Verificado` y las fuentes de cada sección tocada; marcar `(caída, fecha)` las URLs que ya no cargan.
3. Agregar una línea al "Registro de cambios" (fecha, qué cambió, por qué) y actualizar "Última actualización".
4. El documento es público y genérico: nunca escribir datos de un usuario (nombre, empleador, proyectos, cifras). Antes de guardar, releer lo agregado con esa regla.

## 3. Contrastar con el CV base del usuario

1. Leer la última carpeta de `$AGENTE0_DATOS/cv/base/<fecha>/` (`.tex`, auditoría) y aplicarle el checklist del documento, incluidos los límites de tamaño por bloque de la decisión B3.
2. Presentar en pocas líneas qué prácticas cambiaron y qué cambios propone al CV, cada uno con su razón. No modificar el CV sin aprobación: una versión nueva va en una carpeta nueva con fecha (D7), nunca encima de la anterior, y se audita contra `perfil.md` como siempre.
3. Lo que dependa de un dato del usuario que falte se pide al usuario, no se infiere (regla de veracidad).

## 4. Cierre

Decir en una o dos líneas qué cambió en el documento y qué se propone al CV. Al terminar, registrar la ejecución en el reloj de CV base con `python -m agente0 recordatorio operacion cv_base` (D15).
