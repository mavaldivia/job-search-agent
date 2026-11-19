# Agente0

Agente que apoya y automatiza la búsqueda laboral de cualquier persona que quiera usarlo: mantiene el perfil del usuario, gestiona oportunidades, adapta el CV por vacante, asiste o ejecuta las postulaciones, registra el estado de cada proceso y aprende de los resultados reales. El usuario decide cuánto delega.

**Estado**: especificación funcional y decisiones de diseño cerradas (D1 a D18). Fase 2 cerrada (U6, biblioteca de respuestas tipo del primer usuario, aprobada). Construcción en curso (Fase 3): B1, estructura base, B2, onboarding del primer usuario, y B15, operación "Actualizar perfil", hechos.

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
| `docs/tracking/records.md` | Minutas de sesión |
| `.claude/skills/` | Una skill por operación del menú (hoy `actualizar_perfil`) |
| `agente0/`, `tests/` | Código de apoyo (ruta de datos, estructura, ID de postulación, esquema de configuración, bitácora de revisiones del perfil) y pruebas de integración |
| `$AGENTE0_DATOS/` | Datos de cada usuario, fuera del repo (sugerida `~/Agente0-datos/`). `python -m agente0 init` crea la estructura |
| `solo_lectura/` | Requisitos (flujo v1.1) y material previo; no se edita |

## Plan

1. **Fase 1**: decisiones de diseño (D1 a D18), cerrada.
2. **Fase 2**: datos del primer usuario, cerrada.
3. **Fase 3**: construcción mínima con un usuario, subiendo la autonomía de forma gradual.

## Uso

```bash
export AGENTE0_DATOS=~/Agente0-datos   # una carpeta = una persona, fuera del repo
python -m agente0 init                 # crea la estructura sin pisar lo existente
python -m agente0 revision ultima      # fecha de la última revisión del perfil
python -m pytest                       # pruebas de integración
```
