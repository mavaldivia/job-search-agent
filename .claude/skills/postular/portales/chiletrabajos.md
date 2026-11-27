# Chiletrabajos

Lecciones de postular en este portal. Léelo después de `SKILL.md` si la vacante es de Chiletrabajos.

- **Sesión**: sin ella la cabecera muestra «Ingresa a tu cuenta» y `/trabajo/postular/<id>` pide registro. Con sesión, la cabecera muestra el nombre del usuario.
- **Formulario de una página** (`/trabajo/postular/<id>`): `textarea#carta` (precargada), a veces `salary` numérico sin base, `input#cv` (name `att1`, admite `file_upload` por `ref`) y el botón `input[name=apply]`. No hay vista previa: el clic envía.
- **El CV es el único del perfil**: adjuntar uno al postular reemplaza el del perfil. Hace falta la autorización del usuario antes de adjuntar; conviene pedirla antes de adaptar el CV.
- **Carta precargada**: es la guardada en el perfil y puede traer afirmaciones que `perfil.md` no respalda. Es opcional: sin carta aprobada, dejarla vacía.
- **Confirmación**: «Postulacion exitosa». Historial en `/dashboard/postulaciones` (solo los últimos 30 días).
- El iframe oculto de reCAPTCHA no es un desafío; `#google_vignette` en la URL es publicidad.
- **Disponibilidad**: algunos avisos traen `input[name=disp]` (texto opcional) y la casilla `#dispoIn` «Inmediata». Marcarla solo si el perfil dice que la disponibilidad es inmediata.
- **Pausa entre envíos**: el portal admite varias seguidas; respetar igual la de la compuerta.
