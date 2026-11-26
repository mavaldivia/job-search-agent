# LinkedIn («Solicitud sencilla»)

Lecciones de postular por la solicitud sencilla de LinkedIn (riesgo alto, tope de nivel 50 % en la configuración del usuario: el envío siempre pasa por su aprobación).

- **El modal es un `<dialog>` del documento principal**, no un iframe ni un shadow root. `find` y `javascript_tool` con `document.querySelector('dialog')` lo leen barato (texto, radios, valores de campos, casillas). `get_page_text` lee la página y no el modal: no usarlo para el diálogo.
- **Pasos**: contacto, CV, preguntas adicionales y revisar. Contacto y CV vienen precargados del perfil de LinkedIn; el CV que viene preseleccionado suele ser uno genérico y hay que reemplazarlo por el adaptado.
- **Subir el CV**: el botón «Cargar currículum» no tiene `input[type=file]` en el DOM y `file_upload` rechaza el botón. Solución probada: parchar `HTMLInputElement.prototype.click` para que los inputs de tipo file se anexen al `body` sin abrir el selector, pulsar el botón por JS, ubicar el input con `find`, `file_upload` sobre ese input y restaurar el `click` original. El archivo queda además en la lista de currículums del perfil del usuario y el flujo no permite borrarlo: avisarlo antes.
- **Renta**: el campo de expectativa de renta exige texto numérico. Con `$`, puntos o palabras responde «Información incorrecta» y «Revisar» no avanza. Acordar con el usuario un número sin unidad antes de postular (y decirle que sin unidad el reclutador puede leerlo como líquido o como bruto).
- **Revisar (último paso)**: «Seguir a la empresa» viene marcado por defecto; desmarcarlo. La vista previa avisa que el empleador recibe una copia del perfil y que respuestas y CV se guardan en el perfil para futuras solicitudes.
- **Ya postulada**: en el listado, la etiqueta «Solicitados» o «Solicitud enviada» es «ya postulado» (también por fuera de Agente0). Cada clic en una tarjeta gasta una lectura del tope de búsqueda, incluso en una ya postulada.
- **Confirmación**: el diálogo «Solicitud enviada» y, en la ficha, «Estado de la solicitud: Solicitud enviada».
- `javascript_tool` bloquea devolver `src` de iframes y URLs con parámetros.
