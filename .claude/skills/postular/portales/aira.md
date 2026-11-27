# Aira

Lecciones de postular en portales de grandes empresas hechos con esta plataforma. Léelo después de `SKILL.md` si el formulario es de Aira.

- **Aira (portales de empleo de grandes empresas)**: «Postular» exige tener cuenta y sesión del usuario (no se crea). El formulario de preguntas («Estado postulación») usa botones de opción y barras de años que son controles personalizados: marcar un valor por script deja el `checked` del DOM pero no el modelo de la página, y «Enviar postulación» responde «Campo requerido» sin enviar nada; hay que hacer clic real sobre cada opción (si ya viene marcada, pulsar otra y volver) y volver a mirar, porque el aviso de error mueve el diseño. El CV se sube con `file_upload` sobre el campo de archivo y la vista previa (el ojo) muestra el archivo realmente adjunto: usarla para comprobarlo. Desmarcar «Guardar CV en mi perfil». Un envío rechazado por validación no es un envío fallido: la instantánea congelada sigue valiendo si las respuestas no cambian. Confirmación: «Postulación enviada».
- **Sesión que expira al enviar**: «Enviar postulación» puede llevar a la pantalla de ingreso sin mensaje. Queda `ENVIO_INTENTADO`; se verifica en «Mis postulaciones» cuando el usuario vuelva a entrar y no se reenvía antes. Validar la sesión (recargar) justo antes de congelar la instantánea.
- **Valores precargados**: renta, CV y «Guardar CV en mi perfil» (puede venir marcado) se heredan de postulaciones anteriores; sobrescribir y verificar.
- **Cada empresa es una instancia**: la sesión de la Aira de una empresa no sirve en la de otra.
- Después de enviar puede quedar una lista de pruebas (personalidad, inteligencia) que responde el usuario: anotarlas en `accionables`.
