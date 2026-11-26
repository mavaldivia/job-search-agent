# Phenom (sitio de empleos de empresa, `careers.<empresa>.com/.../apply`, con login a Workday)

Lecciones de los formularios de Phenom. Léelo después de `SKILL.md`.

- Parte sin cuenta, login ni CAPTCHA. Es de varios pasos: datos, experiencia, preguntas, preguntas adicionales, divulgaciones voluntarias y revisión.
- **El consentimiento de privacidad va implícito en «Next» del paso 1**: no presionarlo sin que el usuario lo acepte. Los pasos siguientes no se ven sin hacerlo.
- El paso 1 trae «Upload Resume» (PDF o DOCX, máximo 1 MB), que envía el archivo antes de «Next»: subir recién con la aceptación del usuario y revisar después los campos por si autocompleta.
- La casilla de comunidad de talento viene desmarcada: dejarla así.
- Las divulgaciones voluntarias son datos sensibles: las contesta el usuario.
- **Tras subir el CV la pestaña puede quedar sin responder** (ni captura ni JS) durante un rato; en la prueba bastó que el usuario la revisara y el archivo quedó adjunto.
- **El autocompletado desde el CV se equivoca**: puso el apellido materno como paterno y el teléfono con el código de país repetido. Leer todos los campos después de subir y corregirlos.
- El paso 1 se llena con `form_input`; el radio de antigüedad en la empresa se vuelve a dibujar y su `ref` cambia.
- **Si el correo ya tiene una postulación al cargo**, «Next» del paso 1 lleva a `applythankyou?status=alreadyApplied`. El título de la página dice «Thank you for applying», pero **no es la confirmación de un envío nuevo** (D14): mirar `status` y el texto, no registrar `POSTULADO` y avisar al usuario.
- Hasta aquí se probó el llenado del paso 1; los pasos siguientes y el envío no se han probado.
