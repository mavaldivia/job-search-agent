# LinkedIn («Solicitud sencilla»)

Lecciones de postular por la solicitud sencilla de LinkedIn (riesgo alto, tope de nivel 50 % en la configuración del usuario: el envío siempre pasa por su aprobación).

- **El modal es un `<dialog>` del documento principal**, no un iframe ni un shadow root. `find` y `javascript_tool` con `document.querySelector('dialog')` lo leen barato (texto, radios, valores de campos, casillas). `get_page_text` lee la página y no el modal: no usarlo para el diálogo.
- **Pasos**: contacto, CV, preguntas adicionales y revisar. Contacto y CV vienen precargados del perfil de LinkedIn; el CV que viene preseleccionado suele ser uno genérico y hay que reemplazarlo por el adaptado.
- **Subir el CV**: el botón «Cargar currículum» no tiene `input[type=file]` en el DOM y `file_upload` rechaza el botón. Solución probada: parchar `HTMLInputElement.prototype.click` para que los inputs de tipo file se anexen al `body` sin abrir el selector, pulsar el botón por JS, ubicar el input con `find`, `file_upload` sobre ese input y restaurar el `click` original. El archivo queda además en la lista de currículums del perfil del usuario y el flujo no permite borrarlo: avisarlo antes.
- **Filtros excluyentes**: se puede avanzar hasta las preguntas (paso 3) con el CV preseleccionado, sin subir nada; leerlas antes de adaptar el CV. `javascript_tool` basta.
- **Texto del diálogo con `=`**: `javascript_tool` lo bloquea como dato de cookie; reemplazar `=` antes de devolverlo.
- **CV preseleccionado**: es el último subido y puede ser el adaptado para otra vacante; reemplazarlo siempre.
- **Renta**: el campo de expectativa de renta exige texto numérico. Con `$`, puntos o palabras responde «Información incorrecta» y «Revisar» no avanza. Acordar con el usuario un número sin unidad antes de postular (y decirle que sin unidad el reclutador puede leerlo como líquido o como bruto).
- **Revisar (último paso)**: «Seguir a la empresa» viene marcado por defecto; desmarcarlo. La vista previa avisa que el empleador recibe una copia del perfil y que respuestas y CV se guardan en el perfil para futuras solicitudes.
- **Ya postulada**: en el listado, la etiqueta «Solicitados» o «Solicitud enviada» es «ya postulado» (también por fuera de Agente0). Cada clic en una tarjeta gasta una lectura del tope de búsqueda, incluso en una ya postulada.
- **Confirmación**: el diálogo «Solicitud enviada» y, en la ficha, «Estado de la solicitud: Solicitud enviada».
- `javascript_tool` bloquea devolver `src` de iframes y URLs con parámetros.
- **«Solicitar en el sitio web de la empresa»**: el destino real viene en el parámetro `url` del enlace `linkedin.com/safety/go/`; se lee con JS devolviendo solo host y ruta, sin hacer clic. El agente principal lo revisa antes de lanzar el subagente: si el destino exige cuenta propia sin sesión, no lo lanza y avisa al usuario.
- **Destino externo en formularios de monday (`wkf.ms`)**: la lista «vacante a la que postulas» puede ser cerrada y no incluir la del aviso. Antes de adaptar el CV, abrirla y leer los `[role=option]`; si no está, detenerse (no elegir otra).
- **Portal propio de la empresa**: puede tener un botón «Postular» que llama directo a una función de envío; con sesión, un clic podría registrar la postulación sin vista previa. No pulsarlo antes de `postulacion intentar`.
- **Radios Yes/No de las preguntas**: el input puede medir 0x0 y no marcarse con clic por `ref`; clic por coordenadas sobre el círculo y verificar `checked`. En algunos avisos el paso de revisar no trae «Seguir a la empresa».

