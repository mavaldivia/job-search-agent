---
name: investigar_mercado
description: Investiga con un enjambre de subagentes en paralelo cuánto paga el mercado por cada rol y seniority de interés del usuario (Chile en CLP y remoto internacional en USD) y guarda la tabla de rangos con sus fuentes y su vigencia (B24). La usa el agente al preparar la renta de una postulación cuando falta un rango o venció. Usar cuando el usuario invoque /investigar_mercado, pida "cómo están los sueldos" o `python -m agente0 mercado evaluar` responda que no hay rango o que venció.
---

# investigar_mercado

Diseño: decisión B24 (2026-11-20) en `docs/decisiones.md`. Esta skill es genérica: no lleva datos de ningún usuario. Solo lee la web; no usa el navegador del usuario ni envía nada.

**Privacidad**: a los subagentes solo se les dice rol, seniority, país y modalidad. Nunca nombre, empresa actual, renta, perfil ni nada de `$AGENTE0_DATOS`.

## 0. Qué falta

1. `python -m agente0 mercado listar`: qué rangos hay, de qué fecha y cuáles están vigentes (vigencia en `mercado.vigencia_dias`, 30 por defecto).
2. Los roles salen de los cargos de prioridad alta de `$AGENTE0_DATOS/perfil/intereses.md` (I1), agrupados en familias de mercado, y los niveles de I2 agrupados en `Lead` (Lead, Jefe), `Manager` (Manager, Subgerente) y `Head` (Head, Gerente, Director). Los mercados son `Chile` (CLP) y `Remoto internacional` (USD, cargos remotos contratables desde Chile).
3. Investigar solo lo que falta o venció, salvo que el usuario pida refrescar todo. Si el usuario dio una vacante, solo su rol, seniority y mercado.

## 1. Enjambre

Un subagente por combinación rol y mercado, todos en el mismo mensaje para que corran en paralelo, cada uno con los tres niveles de seniority. Cada subagente recibe:

- El rol (con los títulos que agrupa), el mercado y los tres niveles, y la fecha de hoy.
- Buscar con `WebSearch` y leer con `WebFetch` guías salariales de consultoras de selección, portales de empleo y de sueldos, y estudios publicados, de los últimos 18 meses. Citar la URL exacta y la cifra tal como la publica cada fuente. Nunca inventar ni completar una cifra: si no hay dato publicado, decirlo.
- Normalizar solo el período (anual a mensual dividiendo por 12) y dejar la moneda y la base (bruto o líquido) como la publica la fuente. Chile: preferir fuentes en bruto mensual. Remoto internacional: USD bruto, de empresas que contratan en Latinoamérica o con contratistas remotos; no usar sueldos de Estados Unidos para residentes de allá.
- Percentiles por fuente: usar los que publique y no completar los que falten (muchas guías llegan al percentil 75: sin p90 publicado, `p90` va vacío y la propuesta usa el 75 con una nota). Si solo da un rango mínimo a máximo, tratarlo como percentil 25 a 75 (p50 es el punto medio y p75 el máximo) y anotarlo. Con varias fuentes, tomar la mediana de cada percentil.
- Devolver solo JSON: una lista `rangos` con `rol`, `seniority`, `mercado`, `unidad`, `p50`, `p75`, `p90`, `metodo`, `fuentes` (`nombre`, `url`, `dato` con lo que dice la fuente) y `confianza` (`alta` con 3 o más fuentes, `media` con 2, `baja` con 1), y una lista `sin_datos` con las combinaciones que no pudo respaldar.

## 2. Revisar

1. Guardar solo rangos de guías o estudios publicados que calcen con el rol (su título o un equivalente de nivel documentado). Descartar las ofertas de empleo sueltas usadas como única fuente, los cargos de otra familia, las cifras que la fuente declara con otra base (por ejemplo costo del empleador) y las filas cuyas fuentes divergen tanto que su mediana no representa a ninguna: un rango inflado hace omitir vacantes buenas. No bajar la vara para llenar la tabla. Cada fila lleva `confianza` (`alta` con 3 o más fuentes, `media` con 2, `baja` con 1) y se muestra así.
2. Comprobar que los percentiles estén ordenados y que cada URL exista (`WebFetch` a las que parezcan dudosas).
3. Pasar a la unidad de la tabla: Chile bruto a CLP líquido mensual con los supuestos y las fuentes de `configuracion/renta_factores.json` (CL), calculando el impuesto único del nivel de cada cifra, no con un factor de otro nivel; anotar el método en `metodo`. USD queda en USD bruto mensual.

## 3. Guardar y mostrar

1. `python -m agente0 mercado guardar` (JSON por stdin: un rango, con `unidad` y `investigado` de hoy), uno por fila revisada.
2. Mostrar una tabla corta: rol, seniority, mercado, p50, p75, p90, número de fuentes y confianza, y las combinaciones sin datos. Los rangos solo se usan para proponer una renta que el usuario aprueba cada vez (D12, B17).
