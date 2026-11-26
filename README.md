# Agente0

Agente que apoya y automatiza la búsqueda laboral de cualquier persona que quiera usarlo: mantiene el perfil del usuario, gestiona oportunidades, adapta el CV por vacante, asiste o ejecuta las postulaciones, registra el estado de cada proceso y aprende de los resultados reales. El usuario decide cuánto delega.

**Estado**: especificación funcional y decisiones de diseño cerradas (D1 a D18). Fase 2 cerrada (U6, biblioteca de respuestas tipo del primer usuario, aprobada). Construcción en curso (Fase 3): B1, estructura base, B2, onboarding del primer usuario, B3, CV base con verificador de tamaño por bloque, B15, operación "Actualizar perfil", B4, registro de postulaciones con instantánea por intento de envío, B5, biblioteca de respuestas tipo con variantes por familia de cargo, B6, oportunidades, ranking y skill de búsqueda (primer ranking real corrido), B7, adaptación de CV por vacante, B8, primera postulación asistida al 0 % con la skill `postular`, B9, actualizar estado y recompensa con la skill `actualizar_estado`, B10, recordatorios al abrir el menú, B11, autonomía configurable con la skill `actualizar_configuracion` (probada con datos reales al 25 y al 75 %), B16, simulación de configuración («¿y si...?» sobre las vacantes evaluadas), B17, conversión de renta (factor líquido a bruto guardado por país y tasa de cambio buscada cada vez), B18, buscador de vacantes (registro de búsquedas por fuente, búsqueda incremental, topes por riesgo y vacantes fuera del Top), B19, renta observada en el formulario como dato de la oportunidad, y B21, términos de búsqueda ampliados y corridos en siete portales (Indeed y el resto de LinkedIn quedan en B23, al final del plan), hechos; B24, renta esperada según el mercado (rangos investigados por un enjambre de subagentes, con techo, renta estándar sin rango, subida por fit y omisión de vacantes sin cuadre), hecho; B20, fuentes nuevas, B22, términos de búsqueda renovados cada 15 días, y B25, carriles por portal para buscar y postular en paralelo con subagentes, hechos con decisiones provisorias (2026-11-21); B12 (resumen semanal), B13 (medición del aprendizaje), B14 (aislamiento entre usuarios probado) y B23 con avances.

**Arquitectura**: agente sobre Claude Code, a demanda: una skill por operación del menú, archivos locales por usuario y la extensión de Chrome para navegar los portales.

## Flujo

1. **Inicio**: primera vez, onboarding; si no, menú.
2. **Operaciones**: actualizar perfil, postulaciones potenciales, estado de una postulación, CV base (con investigación ATS), configuración (incluida la autonomía) y respuestas tipo.
3. **Subflujo de postulación**: adaptar el CV, compuerta de autonomía, postular por navegación web, marcar "postulado" solo con confirmación y guardar el detalle. Si para avanzar en el formulario hace falta algo que solo puede hacer el usuario (aceptar privacidad o términos, crear cuenta, iniciar sesión), se le pide antes de adaptar el CV.

## Reglas principales

- Veracidad: no se inventa experiencia, renta, certificaciones ni cifras.
- Autonomía de 0 a 100 %: es delegación, no permisos. Ante CAPTCHA, fallas de login o preguntas sin evidencia, el agente pausa y pide intervención.
- Nunca se reenvía una postulación ya completada sin instrucción expresa.
- Cada envío guarda una instantánea inmutable de lo enviado.
- Los datos de cada usuario están aislados; las credenciales nunca van en el repositorio.

El detalle completo está en [`CLAUDE.md`](CLAUDE.md).

## Estructura

| Ruta | Contenido |
|---|---|
| `CLAUDE.md` | Instrucciones del proyecto y reglas del agente |
| `docs/contexto_completo.md` | Diseño extenso: operaciones, autonomía, aprendizaje, entidades, riesgos |
| `docs/onboarding.md` | Banco de preguntas del onboarding y operación "Actualizar perfil" |
| `docs/decisiones.md` | Decisiones tomadas y descartadas |
| `docs/tracking/todos.md` | Plan secuencial por fases |
| `docs/tracking/done.md` | Registro de lo completado |
| `docs/investigacion_cv_ats.md` | Buenas prácticas de CV para ATS y reclutadores; documento vivo que actualiza la skill `investigar_cv` |
| `docs/tracking/records.md` | Minutas de sesión (local, no versionado) |
| `.claude/skills/` | Una skill por operación del menú (hoy `actualizar_perfil`, `investigar_cv`, `editar_respuestas`, `actualizar_postulaciones_potenciales`, `adaptar_cv`, `postular`, `actualizar_estado`, `actualizar_configuracion`, `investigar_mercado`, `revision_semanal` e `investigar_terminos`) |
| `agente0/`, `tests/` | Código de apoyo (ruta de datos, estructura, ID de postulación, esquema de configuración, bitácora de revisiones del perfil, límites de tamaño de CV, registro de postulaciones, planilla de postulaciones, recordatorios, biblioteca de respuestas tipo, oportunidades, ranking, fuentes de búsqueda, compuerta de autonomía, edición de la configuración, simulación de configuración, conversión de renta, rangos de mercado, registro de búsquedas, carriles por portal, resumen semanal, medición del aprendizaje y gasto por sesión y tipo de proceso) y pruebas de integración |
| `$AGENTE0_DATOS/` | Datos de cada usuario, fuera del repo (sugerida `Agente0_datos/<usuario>/`, junto al repo). `python -m agente0 init` crea la estructura |
| `solo_lectura/` | Requisitos (flujo v1.1) y material previo; local, no versionado y no se edita |

## Plan

1. **Fase 1**: decisiones de diseño (D1 a D18), cerrada.
2. **Fase 2**: datos del primer usuario, cerrada.
3. **Fase 3**: construcción mínima con un usuario, subiendo la autonomía de forma gradual.

## Uso

```bash
export AGENTE0_DATOS=/ruta/a/Agente0_datos/<usuario>   # una carpeta = una persona, fuera del repo
python -m agente0 init                 # crea la estructura sin pisar lo existente
python -m agente0 revision ultima      # fecha de la última revisión del perfil
python -m agente0 recordatorio pendientes   # casos con la ventana vencida; también preguntado | operacion <caso>
python -m agente0 cv calibrar cv.tex 2        # fija los límites por bloque de un CV (2 páginas)
python -m agente0 cv verificar cv.tex limites.json   # revisa tamaño, páginas, fuentes y extracción de texto
python -m agente0 postulacion crear < vacante.json   # registra una postulación; luego ver | intentar | confirmar | fallido | evento | recompensar | finalizar <id>
python -m agente0 planilla sync        # agrega a `postulaciones.csv` las postulaciones confirmadas que falten, con el status «Postulado sin validar» (columnas `status` y `accionables` tras `empresa`); las filas existentes no se tocan; también accionables <id> (texto por stdin: lo que viene, con su enlace)
python -m agente0 privacidad           # busca datos del usuario (RUT, correos, fechas, montos, nombre) en lo versionado y sale con error si los hay; un hook la corre antes de git commit y git push
python -m agente0 respuestas listar   # respuestas tipo vigentes; también pendientes | ver | versiones | guardar | revisar
python -m agente0 configuracion ver   # configuración vigente, con los valores iniciales de priorización; también editar (cambio parcial validado)
python -m agente0 autonomia matriz 75  # qué se hace solo y qué se aprueba en un nivel; también evaluar <id> | aviso 100
python -m agente0 simulacion < cambios.json   # qué vacantes cambiarían con una configuración hipotética ({"cambios": {...}}); no modifica nada
python -m agente0 renta convertir < pedido.json   # pasa un líquido a bruto (factor guardado por país; el bruto de Chile sale en número cerrado, con `monto_exacto` a la vista) y/o a otra moneda (tasa); también factor ver | guardar
python -m agente0 oportunidad listar  # vacantes potenciales; también registrar | ver | evaluar | estado | renta (tope observado en el formulario)
python -m agente0 mercado listar       # rangos de sueldo por rol y seniority con su vigencia; también guardar | evaluar <id> (renta propuesta en número cerrado y cuadre)
python -m agente0 ranking generar     # arma el Top con la lista anterior como base; también ultimo
python -m agente0 fuentes listar      # fuentes de búsqueda del usuario; también guardar | agregar
python -m agente0 busqueda resumen    # última búsqueda por fuente; también consulta | vista | vistas | pendiente | cupo | conocida
python -m agente0 carriles             # reparte el Top en carriles por portal (cupo del día, nivel, cola) para postular en paralelo con subagentes
python -m agente0 resumen semanal      # lo enviado y lo pendiente desde la última revisión semanal; también revisado (horas de esfuerzo)
python -m agente0 medicion ventanas    # contactos por hora y tasa de contacto por ventana de 4 semanas; también respuestas (tasa por versión)
python -m agente0 recordatorio pendientes   # casos vencidos al abrir el menú (experiencia, cv_base, configuracion, terminos); también ultima <caso>
python -m agente0 consumo 5            # gasto (USD de lista) de las últimas sesiones de Claude Code sobre el repo, por etapa y subagente
python -m agente0 consumo procesos     # costo unitario por tipo de proceso y por postulación según portal y tamaño de formulario
python -m pytest                       # pruebas de integración
```
