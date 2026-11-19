# Agente0

Agente que apoya y automatiza la búsqueda laboral de cualquier persona que quiera usarlo: mantiene el perfil del usuario, gestiona oportunidades, adapta el CV por vacante, asiste o ejecuta las postulaciones, registra el estado de cada proceso y aprende de los resultados reales. El usuario decide cuánto delega.

**Estado**: especificación funcional y decisiones de diseño cerradas (D1 a D18). Fase 2 cerrada (U6, biblioteca de respuestas tipo del primer usuario, aprobada). Construcción en curso (Fase 3): B1, estructura base, B2, onboarding del primer usuario, B3, CV base con verificador de tamaño por bloque, B15, operación "Actualizar perfil", B4, registro de postulaciones con instantánea por intento de envío, B5, biblioteca de respuestas tipo con variantes por familia de cargo, B6, oportunidades, ranking y skill de búsqueda (primer ranking real corrido), B7, adaptación de CV por vacante, y B8, primera postulación asistida al 0 % con la skill `postular`, hechos.

**Arquitectura**: agente sobre Claude Code, a demanda: una skill por operación del menú, archivos locales por usuario y la extensión de Chrome para navegar los portales.

## Flujo

1. **Inicio**: primera vez, onboarding; si no, menú.
2. **Operaciones**: actualizar perfil, postulaciones potenciales, estado de una postulación, CV base (con investigación ATS), configuración (incluida la autonomía) y respuestas tipo.
3. **Subflujo de postulación**: adaptar el CV, compuerta de autonomía, postular por navegación web, marcar "postulado" solo con confirmación y guardar el detalle.

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
| `.claude/skills/` | Una skill por operación del menú (hoy `actualizar_perfil`, `investigar_cv`, `editar_respuestas`, `actualizar_postulaciones_potenciales`, `adaptar_cv` y `postular`) |
| `agente0/`, `tests/` | Código de apoyo (ruta de datos, estructura, ID de postulación, esquema de configuración, bitácora de revisiones del perfil, límites de tamaño de CV, registro de postulaciones, biblioteca de respuestas tipo, oportunidades, ranking y fuentes de búsqueda) y pruebas de integración |
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
python -m agente0 cv calibrar cv.tex 2        # fija los límites por bloque de un CV (2 páginas)
python -m agente0 cv verificar cv.tex limites.json   # revisa tamaño, páginas, fuentes y extracción de texto
python -m agente0 postulacion crear < vacante.json   # registra una postulación; luego ver | intentar | confirmar | fallido | evento | finalizar <id>
python -m agente0 respuestas listar   # respuestas tipo vigentes; también pendientes | ver | versiones | guardar | revisar
python -m agente0 configuracion ver   # configuración vigente, con los valores iniciales de priorización
python -m agente0 oportunidad listar  # vacantes potenciales; también registrar | ver | evaluar | estado
python -m agente0 ranking generar     # arma el Top con la lista anterior como base; también ultimo
python -m agente0 fuentes listar      # fuentes de búsqueda del usuario; también guardar | agregar
python -m pytest                       # pruebas de integración
```
