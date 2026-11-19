# Investigación: CV que pasa ATS y convence a un reclutador humano

Última actualización: 2026-11-18

Documento vivo y genérico (sin datos de ningún usuario). Lo consumen B3 (CV base), B7 (adaptación por vacante) y cualquier variante de CV de Agente0. Decisión de formato maestro: D7 en `docs/decisiones.md`.

## Cómo actualizar este documento

1. Leerlo completo antes de tocarlo. Conservar lo vigente; corregir o ampliar solo lo que cambió.
2. Cada sección tiene "Verificado" (fecha de la última revisión de sus fuentes) y "Fuentes" (URLs). Al revisar una sección, actualizar esa fecha y no borrar URLs: si una cae, marcarla `(caída, fecha)`.
3. Las fuentes llevan una marca: `[F]` = la página se leyó entera; `[B]` = solo se vio el resumen de un resultado de búsqueda (no se pudo abrir o no se abrió). Las `[B]` son lo primero que conviene reverificar.
4. Si dos fuentes se contradicen, anotar ambas y la decisión tomada, no borrar una.
5. Toda actualización agrega una línea al "Registro de cambios" del final (fecha, qué cambió, por qué) y actualiza "Última actualización" de arriba.
6. Cada sección termina con "Pendiente de verificar": ahí van las dudas abiertas para la próxima corrida.

Escala de fuerza de la evidencia (usada en las secciones y en la tabla):
- Alta: documentación o declaración de un proveedor de ATS o de parsing, institución académica, o prueba propia reproducible con los comandos indicados.
- Media: varias fuentes independientes y coherentes, o estudio con método publicado pero limitado.
- Baja: blogs de herramientas de CV, estudios de un proveedor sin método publicado, columnas de opinión.
- Folclore: afirmación repetida sin fuente verificable.

## Resumen ejecutivo

- Un ATS no "rechaza" CVs por su cuenta. Convierte el archivo a texto, lo mapea a campos (nombre, contacto, cargos, empresas, fechas, educación, habilidades) y deja que reclutadores busquen y filtren. Greenhouse lo dice de forma expresa; el rechazo automático existe solo como regla del empleador sobre respuestas a preguntas del formulario (autorización de trabajo, ubicación, renta, años de experiencia), no sobre el texto del CV. Los riesgos reales son otros: un perfil mal parseado (campos vacíos o cargos mezclados) y no aparecer en la búsqueda del reclutador.
- Lo que rompe el parseo está documentado por los propios proveedores: archivos escaneados o imagen, columnas, tablas, nombre y contacto en encabezado, pie o cuadro de texto, gráficos y fotos, letras separadas por espacios, y fechas partidas en dos líneas.
- Una columna, texto real, títulos de sección estándar, fechas completas en una línea y sin foto es la combinación más robusta. No hay una garantía universal ("no existe una prueba universal", Buk): se verifica extrayendo el texto.
- En LaTeX con XeTeX/tectonic, las fuentes salen incrustadas con ToUnicode sin configuración extra, pero hay cuatro trampas medidas en una prueba propia: ligaduras `ff/ffi` (se extraen como U+FB00...), interletraje con `LetterSpace` (un extractor partió "EXPERIENCIA"), fechas con `\hfill` (otro las separó del cargo) y la viñeta por defecto (no se extrae como texto).
- Para humanos: lectura inicial de unos 7 segundos (estudio de 2018 con método poco documentado), por lo que titular, perfil de 3 a 4 líneas y viñetas de logro con verbo de acción, escala y resultado deciden. No se inventa la métrica: escala, alcance y frecuencia también cuentan, y lo estimado se rotula "estimado".
- Largo: en Chile las fuentes dicen "ideal una página, máximo dos"; con unos 6 años o más de experiencia, dos páginas son aceptables si la primera concentra el valor. La evidencia a favor de dos páginas (un estudio de un proveedor de CV) es débil.
- Omitir foto, edad, estado civil, RUT y referencias es la práctica chilena y la de los mercados anglosajones; la foto es la que más varía por país.
- Palabras clave: los ATS modernos buscan también por sinónimos y términos relacionados (Greenhouse, Workday); no hace falta apilarlas. Se usan los términos de la vacante solo si hay evidencia real, una vez en el perfil o experiencia y una en habilidades.
- Idioma: el del aviso. Para un perfil en Chile con interés regional: base en español y variante en inglés derivada, con los mismos hechos.

## 1. Cómo parsean los ATS y qué lo rompe

Verificado: 2026-11-18

Hallazgos:
- Flujo común: conversión del archivo a texto, extracción de entidades, mapeo a campos del perfil de candidato y, si el empleador lo activa, comparación con criterios. Greenhouse: el parseo "auto-rellena los campos"; Workday (HiredScore) muestra un "Parsed CV" con experiencia, educación y habilidades; SmartRecruiters normaliza las habilidades con una taxonomía. Fuerza: alta.
- Campos mapeados: nombre, contacto, cargos, empresas, fechas, grados e instituciones, habilidades. Fuerza: alta (Greenhouse, Workday, SmartRecruiters).
- Qué lo rompe (Greenhouse, lista oficial de causas de parseo fallido): archivo de imagen en vez de documento, más de 2,5 MB, gráficos, fotos o word art, tablas, encabezados y pies, nombre y contacto en encabezado, pie o cuadro de texto, diseño en columnas, letras separadas por espacios, nombres de empresa sin identificador (Inc., S.A.) y cargos incompletos ("Sr. Account Exec"). iCIMS: un nombre en el encabezado puede impedir crear el perfil. SAP SuccessFactors: un PDF escaneado o que fue imagen no se parsea; el texto en PDF sí. Un proveedor de parsing (RChilli) agrega: un rango de fechas partido en dos líneas puede no leerse y un año suelto no cuenta como período. Fuerza: alta para Greenhouse, iCIMS y SAP; media para RChilli (proveedor de parsing con interés comercial).
- Mito del rechazo automático: Greenhouse Talent Matching (opt-in: el empleador calibra criterios y obtiene categorías Strong, Good, Partial y Limited) "no rechaza ni avanza a ningún candidato" y las decisiones las toman reclutadores; la regla Auto-Reject existe (planes Plus y Pro) pero se basa en respuestas a preguntas personalizadas, no en el texto del CV; la página para candidatos agrega que cada solicitud la revisan personas y que los filtros los define el reclutador (esa página dice que la IA no puntúa solicitudes, lo que parece contradecir a Talent Matching: ambas coinciden en que no hay rechazo automático por contenido). Una encuesta de Enhancv a 25 reclutadores (proveedor de servicios de CV, muestra pequeña) halló que el 92 % no usa rechazo automático por formato o palabras clave. El origen de la cifra "el 75 % de los CV se descarta" no se pudo rastrear a una fuente primaria. Fuerza: alta (Greenhouse), baja (encuesta), folclore (el 75 %).
- Dónde sí hay filtro duro: preguntas "knockout" del formulario (autorización de trabajo, licencias, ubicación, renta, años de experiencia). Para Agente0 esto es una regla de respuestas tipo, no del CV. Fuerza: alta (Greenhouse).
- Búsqueda y ranking: los reclutadores buscan por palabras clave, títulos y habilidades en la base de candidatos; LinkedIn Recruiter ofrece 40+ filtros (título, ubicación, habilidades) y búsqueda booleana. Cómo se ordenan los resultados no es público. Fuerza: alta (existencia de filtros), baja (reglas de ordenamiento).
- Comportamiento en Workday: guías de terceros dicen que el formulario se autocompleta desde el CV y que conviene revisar cada campo antes de enviar; no se encontró documentación oficial del módulo de reclutamiento. Fuerza: baja.

Fuentes:
- [F] Greenhouse, parseo fallido: https://support.greenhouse.io/hc/en-us/articles/200989175-Unsuccessful-resume-parse
- [F] Greenhouse, Talent Matching (no rechaza ni avanza): https://support.greenhouse.io/hc/en-us/articles/41131886674075
- [F] Greenhouse, reglas de aplicación (Auto-Reject sobre preguntas): https://support.greenhouse.io/hc/en-us/articles/203105595-Application-Rules-Overview
- [F] Greenhouse, qué pasa tras postular (revisión humana, filtros del reclutador): https://my.greenhouse.com/blogs/what-really-happens-after-you-apply-for-a-job
- [F] Workday HiredScore, perfiles y tipos de archivo: https://doc.workday.com/hiredscore/en-us/workday-hiredscore/recruiter-productivity-/concept--candidate-profiles.html
- [B] SAP SuccessFactors, parseo de CV (idiomas incluido español, PDF escaneado no parsea): https://help.sap.com/docs/successfactors-recruiting/setting-up-and-maintaining-sap-successfactors-recruiting/working-with-resume-parsing
- [B] iCIMS, nombre en encabezado impide el parseo: https://community.icims.com/articles/Knowledge/Creating-New-Candidates-via-Bulk-File-Transfer-Migrating-Legacy-Resumes-during-Implementation
- [B] SmartRecruiters, API de parseo y taxonomía de habilidades: https://developers.smartrecruiters.com/reference/candidatesresumeparse y https://www.smartrecruiters.com/resources/glossary/resume-parsing/ (la segunda devolvió 403)
- [F] RChilli (proveedor de parsing), consejos de formato: https://www.rchilli.com/tips-for-electronic-resume-writing
- [F] Enhancv vía IT Brief, encuesta a 25 reclutadores: https://itbrief.co.uk/story/study-reveals-ats-rarely-auto-rejects-cvs-debunks-75-myth
- [B] LinkedIn Recruiter, filtros: https://business.linkedin.com/talent-solutions/recruiter/recruiter-features
- [B] Jobscan, "un ATS rara vez rechaza": https://www.jobscan.co/blog/applicant-tracking-system-and-ats-systems

Pendiente de verificar: documentación oficial de Lever (https://help.lever.co/hc/en-us/articles/20087345054749 no cargó), Workday módulo de reclutamiento, Taleo/Oracle y SmartRecruiters (solo hay material de terceros), cómo parsean los ATS chilenos (Buk, Trabajando, Laborum: no hay documentación técnica pública hallada).

## 2. Formato y archivo

Verificado: 2026-11-18

Hallazgos:
- PDF con texto frente a DOCX: Workday (HiredScore) admite DOC, DOCX, PDF, RTF y TXT; iCIMS recomienda doc, docx, pdf, rtf y txt; SAP parsea PDF con texto pero no escaneado. Las fuentes de consejo se contradicen: RChilli y una nota de BBC Mundo (vía MDZ) prefieren Word; Forbes Chile (columna de opinión) prefiere PDF. Decisión: PDF con texto por defecto, verificado con extracción; si el portal solo acepta DOCX o el parseo falla, DOCX como salida alternativa (D7 ya lo contempla). Seguir siempre el formato que pida el aviso. Fuerza: media (no hay prueba comparada independiente).
- Una columna, sin tablas, sin cuadros de texto: Greenhouse lo lista entre las causas de parseo fallido; Jobscan probó un CV de diseño con columnas y tabla en Lever y solo se leyó la experiencia (ignoró habilidades, contacto y enlaces). Fuerza: alta (Greenhouse), media (Jobscan, cualitativo).
- Encabezados y pies de página: no poner nombre ni contacto allí (Greenhouse, iCIMS, RChilli). Fuerza: alta.
- Íconos, gráficos, barras de nivel de habilidad: gráficos y word art rompen el parseo (Greenhouse); un ícono como etiqueta de contacto se extrae como carácter basura o nada. Fuerza: alta (gráficos), media (íconos).
- Foto: Greenhouse la lista como causa de parseo fallido. En Chile: un consultor de empleo (BioBioChile, 2023) no la recomienda; Randstad (vía Meganoticias, 2026) la considera opcional y actual si se incluye; El Mostrador y Adecco dicen que no es obligatoria. Harvard OCS indica omitir foto, edad y género. En EE. UU. y Reino Unido se desaconseja; Alemania y parte de Europa la esperan; en España y LatAm hay variación (fuentes de blogs). Fuerza: media para "omitir en el CV ATS", baja para las normas por país.
- Datos a omitir: edad, estado civil, RUT, nacionalidad, dirección exacta y referencias (BioBioChile, G-Talent, Adecco; Harvard para referencias). El RUT es opcional y se entrega si el aviso lo exige (El Mostrador). Conservar nombre, ciudad o región, teléfono, correo profesional y LinkedIn o portafolio (G-Talent). Fuerza: media.
- Tipografías: Jobscan recomienda Calibri, Arial, Georgia, Helvetica y similares a 10-12 pt en cuerpo, 14-16 en títulos y 18-22 en el nombre, y no reducir la letra para que quepa; dice haber probado cómo las leen los ATS, sin publicar método. Lo que sí importa técnicamente es que la fuente quede incrustada con mapa ToUnicode (sección 3). Fuerza: baja para la lista de fuentes, alta para el requisito de incrustación.
- Márgenes: no hay evidencia sólida; usar 1,5 a 2 cm. Fuerza: sin evidencia (práctica).
- Viñetas: círculos o guiones simples; símbolos elaborados pueden fallar (Jobscan). Fuerza: baja.
- Fechas: "Mes Año" o "MM/AAAA", siempre el mismo formato en todo el CV; el rango completo en una sola línea (Jobscan, RChilli); los ATS calculan duraciones y huecos a partir de ellas (Santa Clara University). Fuerza: media.
- Títulos de sección estándar. Español: Perfil profesional (o Resumen), Experiencia laboral, Educación, Habilidades, Idiomas, Certificaciones, Proyectos (Buk, G-Talent). Inglés: Professional Summary, Work Experience, Education, Skills, Languages, Certifications, Projects (Jobscan). Evitar títulos creativos. Fuerza: media.
- Enlaces: escribir la URL como texto visible (linkedin.com/in/...), porque el hipervínculo puede perderse (Lever ignoró los enlaces en la prueba de Jobscan). Fuerza: media.
- Nombre del archivo: `Nombre-Apellido-CV.pdf` (o con el cargo), sin espacios ni tildes. Las fuentes se contradicen sobre si el ATS lo usa; ayuda a quien lo recibe. Fuerza: baja.
- Tamaño: Greenhouse no parsea archivos de más de 2,5 MB; una fuente de terceros (baja) dice que Oracle Taleo limita por defecto a 1 MB por adjunto. Un CV con texto pesa decenas de KB. Fuerza: alta para 2,5 MB, baja para 1 MB.

Fuentes:
- [F] Greenhouse, parseo fallido: https://support.greenhouse.io/hc/en-us/articles/200989175-Unsuccessful-resume-parse
- [F] RChilli: https://www.rchilli.com/tips-for-electronic-resume-writing
- [F] Jobscan, tablas y columnas (prueba en Lever): https://www.jobscan.co/blog/resume-tables-columns-ats/
- [F] Jobscan, tipografías: https://www.jobscan.co/blog/best-fonts-resume-ats-recruiter/
- [B] Jobscan, fechas: https://www.jobscan.co/blog/resume-dates
- [B] Santa Clara University sobre errores de formato ATS: https://www.scu.edu/careercenter/toolkit/job-scan-common-ats-resume-formatting-mistakes/
- [F] Harvard FAS OCS (omitir foto, edad, género, referencias): https://careerservices.fas.harvard.edu/resources/create-a-strong-resume
- [F] BioBioChile, 2023: https://www.biobiochile.cl/noticias/servicios/explicado/2023/11/29/sin-foto-y-al-grano-5-consejos-para-un-curriculum-ganador.shtml
- [F] Meganoticias, 2026-11-02 (Randstad): https://www.meganoticias.cl/nacional/535342-cuantas-paginas-debe-tener-un-cv-empleo-trabajo-postulacion-02-11-2026.html
- [F] G-Talent (Chile, 2026): https://www.g-talent.net/blogs/desarrollo-profesional/cv-ats-chile-2026-compatible-inteligencia-artificial
- [F] Buk Chile, filtros ATS: https://www.buk.cl/blog/filtros-ats
- [F] Forbes Chile (columna de opinión, 2025): https://forbes.cl/red-forbes/2025-10-09/como-armar-un-cv-en-epocas-de-inteligencia-artificial/
- [B] El Mostrador (RUT y foto opcionales): https://www.elmostrador.cl/datos-utiles/2025/05/25/como-hacer-un-curriculum-vitae-en-chile-guia-practica-para-conseguir-entrevistas-segun-la-ia/
- [B] Adecco Chile: https://www.adecco.com/es-cl/blog/como-hacer-cv-que-funcione
- [B] Taleo, límite de tamaño y reglas (terceros, baja confianza): https://atsverification.com/ats/taleo/
- [B] Computrabajo Chile, "crear un buen CV" (PDF o Word; la página no cargó entera): https://cl.computrabajo.com/desarrollo-profesional/novedades/crear-un-buen-cv-en-computrabajo
- [B] Foto por país (blog de un proveedor, baja confianza): https://www.betterpic.io/blog/cv-photos-2025-best-practices

Pendiente de verificar: si Laborum, Trabajando.com y Computrabajo autocompletan el perfil al subir un CV y con qué formato; preferencia real PDF/DOCX de Workday del módulo de reclutamiento; norma de foto en LatAm con una fuente primaria.

## 3. Particularidades de LaTeX, XeLaTeX y tectonic

Verificado: 2026-11-18 (pruebas propias con tectonic 0.16.9, TeX Gyre Heros, pdftotext 26.07.0 y pypdf 6.9.2)

Hallazgos (cada uno con su fuerza):
- ToUnicode: con XeTeX/tectonic (xdvipdfmx) las fuentes OpenType salen como CID Type 0C, incrustadas, subconjunto y con mapa Unicode (`pdffonts`: columna `uni = yes`). No hace falta `\pdfgentounicode` ni `glyphtounicode`: son primitivas de pdfTeX y los hilos de la lista XeTeX indican que no aplican a XeLaTeX. Tildes y eñe se extrajeron intactas (á, é, í, ó, ú, ñ, Ó) tanto con pdftotext como con pypdf si el texto se escribe en Unicode directo (no con `\'a`). Fuerza: alta (prueba propia reproducible); la afirmación sobre `glyphtounicode` en XeTeX es media (listas de correo antiguas).
- Ligaduras: con la configuración por defecto de fontspec, "Efficient" se extrajo como "Eﬀicient" (U+FB00) en pdftotext y en pypdf; pdftotext descompone solo `fi` y `fl`, no `ff`. Solución probada: `Ligatures={TeX,NoCommon}` en la fuente; la extracción pasó a "Efficient" y `ff`, `ffi`, `ffl` salen normales. `Ligatures=TeX` se mantiene para que `--` siga produciendo el guion largo. Fuerza: alta (prueba propia); la recomendación coincide con una guía de un proveedor (baja).
- Interletraje: con `LetterSpace=9` pdftotext extrajo bien "EXPERIENCIA PROFESIONAL", pero pypdf devolvió "EXPERIEN CIA PROFESIONAL". Otros extractores pueden partir palabras de la misma forma; no usar `LetterSpace` ni versalitas (`\textsc`) en el CV ATS. Fuerza: alta (prueba propia), pero solo con dos extractores.
- Alineación de fechas con `\hfill`: pdftotext sin `-layout` puso la fecha después de la línea siguiente al cargo ("Cargo / Empresa / línea en blanco / Fechas"); pypdf y `-layout` la dejaron en la misma línea. Mitigación adoptada: cargo y empresa en una línea y fechas en la siguiente, sin hueco horizontal. Fuerza: alta (prueba propia), media en su relevancia para un ATS concreto, porque los parsers comerciales usan coordenadas.
- Viñetas: con babel-spanish y enumitem la viñeta por defecto se dibujó como cuadrado pequeño y no apareció en ninguna extracción. Con `label={•}` (carácter Unicode U+2022 directo) se extrae como "•". Fuerza: alta (prueba propia).
- Fuentes en tectonic: `fontspec` no encuentra una familia por su nombre comercial para las fuentes del bundle (`\setmainfont{TeX Gyre Heros}` falló con "cannot be found"); sí funciona por nombre de archivo: `\setmainfont{texgyreheros}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic]`. El primer uso descarga los archivos del bundle (hace falta red una vez); después queda en caché. TeX Gyre Heros es un clon de Helvetica con licencia libre, portable entre usuarios, a diferencia de fuentes del sistema (Arial, Helvetica) que no existen en todas las máquinas. Una fuente como Noto Sans puede no estar instalada. Fuerza: alta (prueba propia).
- hyperref: `hidelinks` evita los recuadros de color; `unicode` y `pdftitle`, `pdfauthor`, `pdflang` dejan metadatos limpios. Los enlaces se escriben con la URL como texto visible. No hay evidencia de que el ATS use el metadato; es higiene (y evita filtrar el nombre del programa o rutas). Fuerza: baja para ATS, sin costo.
- Guionado: desactivar (`\hyphenpenalty=10000`, `\exhyphenpenalty=10000`) y usar `\raggedright`: una palabra partida al final de línea se extrae como dos fragmentos y el espaciado variable de la justificación empeora la separación de palabras. Razonamiento propio sin prueba comparada. Fuerza: baja.
- Orden de lectura: una columna sin TikZ ni texto posicionado sigue el orden del código fuente; es la razón de fondo de D7. Fuerza: alta.
- Comprobación recomendada: `pdffonts` (todas `emb yes`, `uni yes`), `pdftotext -layout` y `pdftotext` sin layout, un extractor distinto (pypdf), búsqueda de ligaduras U+FB00 a U+FB06 y del carácter de reemplazo, copiar y pegar a un editor de texto plano (G-Talent lo sugiere) y render a PNG para revisar. Ver el checklist.

Fuentes:
- Prueba propia (reproducible con los comandos del checklist): tectonic 0.16.9, TeX Gyre Heros, `Ligatures={TeX,NoCommon}`, `LetterSpace`, `\hfill`, viñetas.
- [B] Guía LaTeX de un proveedor (ligaduras, ToUnicode, íconos): https://atsverification.com/blog/latex-resume-ats-friendly/
- [B] Hilo de lista XeTeX, ligaduras y búsqueda en PDF: https://tug.org/pipermail/xetex/2010-June/016983.html
- [B] Hilo de lista XeTeX, PDF buscables: https://tug.org/pipermail/xetex/2012-October/023699.html
- [B] Hilo de lista XeTeX, texto en fuentes Type0 con subconjunto: https://tug.org/pipermail/xetex/2018-August/027385.html
- [B] Packt LaTeX Cookbook (`glyphtounicode` en pdfTeX): https://subscription.packtpub.com/book/business-and-other/9781784395148/3/ch03lvl1sec37/enabling-the-searching-and-copying-of-ligatures

Pendiente de verificar: probar con extractores adicionales (pdfminer, PyMuPDF, Apache Tika) y con un parser comercial si hay acceso; si `\XeTeXgenerateactualtext` mejora la extracción; comportamiento de otras fuentes del bundle (TeX Gyre Pagella, Termes) y de Inter o Noto cuando el usuario las tenga instaladas.

## 4. Contenido que convence a un humano

Verificado: 2026-11-18

Hallazgos:
- Lectura rápida: un estudio de TheLadders de 2018 midió 7,4 segundos de promedio en la revisión inicial, con seguimiento ocular; recomienda títulos y subtítulos claros, evitar frases largas, columnas múltiples y poco espacio en blanco, y señala que un reclutador interesado dedica a la segunda página tanto como a la primera. Críticas: no publica tamaño de muestra ni método. Tomarlo como dirección, no como medida precisa. Fuerza: baja a media.
- Titular y perfil: un titular con el cargo estándar del mercado (Forbes Chile: traducir cargos poco comunes a un título estándar o mostrar la versión interna y la externa; LinkedIn: los reclutadores buscan por título). Perfil de 3 a 4 líneas con años, ámbito, escala y especialidad (G-Talent). Evitar objetivos genéricos (Simplify, blog de reclutamiento). Fuerza: media.
- Viñetas de logro: verbo de acción, qué se logró, cuánto y cómo. Harvard OCS: lenguaje específico, activo y basado en hechos ("quantify and qualify"), empezar con verbo de acción, sin pronombres ni abreviaturas, y no omitir resultados; reemplazar "responsable de". Fórmula de Laszlo Bock (Google, 2014): "logré [X], medido por [Y], haciendo [Z]"; la medida puede ser escala, frecuencia, tiempo o alcance, no solo porcentajes. Fuerza: alta (Harvard), media (Bock, vía artículos secundarios).
- Cuantificar sin inventar: usar solo cifras con respaldo del perfil; si no hay resultado medido, describir escala (países, usuarios, volumen, horizonte) y el trabajo realizado. Lo estimado se rotula "estimado" con su método; lo que está en desarrollo se rotula "en desarrollo". Una cifra aproximada se escribe como aproximada ("aproximadamente 12"). Es regla de veracidad de Agente0, no una convención de CV. Fuerza: regla del proyecto.
- Orden de secciones para unos 6 años de experiencia: nombre y contacto, titular, perfil, experiencia (cronología inversa), habilidades, proyectos propios, educación, idiomas. Harvard: cronología inversa y secciones por orden de importancia; G-Talent: encabezado, perfil, experiencia, habilidades, formación, proyectos. Con más de 5 años la educación baja de posición. Fuerza: media.
- Largo: en Chile, Randstad (vía Meganoticias) dice que no debe superar dos páginas y que un CV de tareas rinde menos que uno de logros; BioBioChile: "idealmente una página, máximo dos"; G-Talent: una o dos por familia de cargos. El estudio de ResumeGo (482 reclutadores, simulación con CV bien redactados, hecho por un servicio de CV) halló que dos páginas fueron elegidas 2,6 veces más en nivel medio y 2,9 veces más en gerencial; no probó el filtro ATS. Conclusión: hasta dos páginas con la primera reuniendo perfil y la trayectoria completa; una página cuando el aviso o el portal lo favorezca; nada de relleno. Fuerza: baja a media.
- Qué omitir: foto, edad, estado civil, RUT, nacionalidad, dirección exacta, referencias, pronombres, objetivos genéricos (sección 2). Harvard también excluye género y fechas al inicio de cada línea. Fuerza: media.
- Proyectos propios y en desarrollo: sección aparte de la experiencia, con rango de fechas "desde AAAA" y estado explícito ("en desarrollo", "pausado"), qué se construyó y con qué, y ningún resultado no verificado. Un proyecto pausado o caducado no se presenta como activo ni como negocio. Fuente genérica de guías de proyectos (baja) más la regla de veracidad.
- Coherencia con LinkedIn: Greenhouse (consejo de un reclutador) pide que la experiencia en LinkedIn sea igual o similar a la del CV, porque muchos reclutadores miran LinkedIn antes que el CV. Fuerza: media.

Fuentes:
- [B] TheLadders 2018 vía HR Dive: https://www.hrdive.com/news/eye-tracking-study-shows-recruiters-look-at-resumes-for-7-seconds/ ; crítica de método: https://www.ere.net/articles/is-the-6-second-resume-scan-a-myth
- [F] Harvard FAS OCS: https://careerservices.fas.harvard.edu/resources/create-a-strong-resume
- [B] Harvard School of Public Health, guía de CV: https://content.sph.harvard.edu/wwwhsph/sites/36/2016/06/Resume-Guide-June-2016.pdf
- [B] Bock, fórmula (Inc.): https://www.inc.com/melanie-curtin/job-hunting-a-google-executive-says-to-use-this-3-part-resume-formula-to-stand-out.html ; texto original: https://www.calstatela.edu/sites/default/files/formula_for_a_winning_resume.docx
- [F] ResumeGo vía CNBC: https://www.cnbc.com/2018/12/19/resumego-hiring-managers-prefer-candidates-with-two-page-resumes.html
- [F] Meganoticias (Randstad): https://www.meganoticias.cl/nacional/535342-cuantas-paginas-debe-tener-un-cv-empleo-trabajo-postulacion-02-11-2026.html
- [F] BioBioChile: https://www.biobiochile.cl/noticias/servicios/explicado/2023/11/29/sin-foto-y-al-grano-5-consejos-para-un-curriculum-ganador.shtml
- [F] G-Talent: https://www.g-talent.net/blogs/desarrollo-profesional/cv-ats-chile-2026-compatible-inteligencia-artificial
- [F] Greenhouse, consejos de un reclutador: https://www.greenhouse.com/blog/get-hired-a-recruiters-advice-for-job-seekers
- [B] Guía de proyectos en el CV (genérica): https://topresume.com/career-advice/list-projects-on-a-resume
- [B] Simplify, resumen frente a objetivo (blog de reclutamiento): https://simplify.jobs/blog/do-you-need-a-resume-summary

Pendiente de verificar: un estudio reciente con método publicado sobre tiempo de lectura y largo en mercados hispanohablantes; preferencia de resumen frente a objetivo con una fuente primaria; si LinkedIn publica guía propia sobre coherencia CV y perfil.

## 5. Palabras clave y alineación con familias de cargos

Verificado: 2026-11-18

Hallazgos:
- La búsqueda no es solo literal: Greenhouse dice que su IA sugiere términos y sinónimos relacionados a los reclutadores, por lo que los candidatos no necesitan apilar palabras clave; Talent Matching compara "términos relacionados" contra las habilidades calibradas y varios términos pueden mapear a una misma habilidad, de modo que repetir no sube el puntaje. Workday Skills Cloud fusiona sinónimos (hasta más de 20 por habilidad en su lanzamiento de 2018) y sugiere habilidades relacionadas; SmartRecruiters normaliza habilidades con una taxonomía. Fuerza: alta (Greenhouse), media (Workday, material de 2018 y guía de administración), media (SmartRecruiters, whitepaper).
- Aun así, parsers y búsquedas más antiguos dependen de coincidencia exacta; por eso conviene usar el término tal como lo escribe el mercado ("BigQuery", "Looker Studio") y, cuando el aviso usa sigla y nombre completo, escribir ambos una vez ("Business Intelligence (BI)"). Fuerza: baja (blogs), práctica común.
- Dónde ponerlas: de forma natural en perfil y experiencia, con contexto, y una vez en la lista de habilidades; sin repetir muchas veces ni ocultar texto (G-Talent, Buk). Buk advierte que la sobreoptimización dificulta la lectura humana. No hay una densidad óptima verificada. La cifra "+45 % de probabilidad" de Jobscan no se verificó. Fuerza: media (G-Talent, Buk), folclore (la cifra).
- Habilidades bien hechas: agrupadas por categoría (lenguajes y datos, modelamiento, plataformas, BI), con las herramientas que de verdad se usan y el contexto en las viñetas; sin barras de nivel ni gráficos (rompen el parseo). Si una herramienta se conoce solo por proyectos propios, rotularlo "(proyectos propios)". Una palabra del aviso no es una habilidad demostrada: sin evidencia, se omite y se anota como brecha. Fuerza: media (parseo), regla del proyecto (veracidad).
- Base frente a adaptación: en el CV base van los hechos verificables completos, cargos, empresas y fechas (nunca cambian), y el vocabulario amplio de las tres o cuatro familias de cargos objetivo. En el paso 0 de cada vacante (B7) se adaptan: titular (con el cargo estándar del aviso si es verdad), perfil, orden de los grupos de habilidades, qué tres o cuatro viñetas abren cada cargo, y términos propios de la vacante solo si hay evidencia. Greenhouse aconseja subir arriba las habilidades que pide el puesto y revisar la coherencia con LinkedIn. Fuerza: media.

Fuentes:
- [F] Greenhouse, qué pasa tras postular (términos y sinónimos): https://my.greenhouse.com/blogs/what-really-happens-after-you-apply-for-a-job
- [F] Greenhouse, Talent Matching: https://support.greenhouse.io/hc/en-us/articles/41131886674075
- [F] Greenhouse, consejos de un reclutador: https://www.greenhouse.com/blog/get-hired-a-recruiters-advice-for-job-seekers
- [B] Workday, Skills Cloud (2018): https://newsroom.workday.com/2018-10-02-Workday-Delivers-Machine-Learning-Powered-Skills-Cloud-to-Unlock-Untapped-Workforce-Potential ; guía de administración: https://doc.workday.com/admin-guide/en-us/human-capital-management/skills-and-skills-cloud/skills-cloud/bkh1675290302153.html
- [B] SmartRecruiters, API de parseo (habilidades normalizadas): https://developers.smartrecruiters.com/reference/candidatesresumeparse
- [F] Buk Chile: https://www.buk.cl/blog/filtros-ats
- [F] G-Talent: https://www.g-talent.net/blogs/desarrollo-profesional/cv-ats-chile-2026-compatible-inteligencia-artificial
- [F] Forbes Chile: https://forbes.cl/red-forbes/2025-10-09/como-armar-un-cv-en-epocas-de-inteligencia-artificial/

Pendiente de verificar: si los ATS usados en Chile aplican ontologías de habilidades en español; lista de sinónimos y siglas frecuentes por familia de cargos (se puede construir de avisos reales en B7).

## 6. Idioma del CV

Verificado: 2026-11-18

Hallazgos:
- Regla general: el idioma del aviso. G-Talent (guía para Chile) recomienda seguir el lenguaje de la vacante sin copiarla. Para empresas de EE. UU. o multinacionales que contratan en LatAm, las guías de trabajo remoto y Deel recomiendan CV en inglés; para empresas regionales en español, español neutro. Adaptar, no traducir palabra por palabra (weremoto). Fuerza: baja (blogs y portales de empleo).
- Español como idioma de parseo: SAP SuccessFactors lista el español entre sus idiomas de parseo; no se encontró información equivalente para los demás ATS. Fuerza: media (solo SAP).
- Recomendación para un perfil en Chile con interés posible en cargos remotos o regionales: base en español (portales chilenos, empleadores locales, avisos en español) y una variante en inglés derivada del mismo contenido verificado, usada cuando el aviso esté en inglés o la empresa sea multinacional con proceso en inglés. Mantener los mismos hechos y el mismo nivel declarado de inglés (sin inflarlo); no mezclar idiomas dentro del mismo CV salvo nombres de herramientas, cargos y siglas del mercado. Esto es criterio, no evidencia directa.

Fuentes:
- [F] G-Talent: https://www.g-talent.net/blogs/desarrollo-profesional/cv-ats-chile-2026-compatible-inteligencia-artificial
- [B] Deel, CV para trabajo remoto: https://deel.com/es/blog/cv-para-trabajo-remoto
- [B] Trabajo remoto para empresas de EE. UU. desde LatAm: https://jobrise.io/es/blog/trabajo-remoto-empresas-usa-desde-latam-2026/
- [B] weremoto, adaptar el CV al inglés: https://weremoto.com/blog/como-adaptar-tu-cv-de-espanol-a-ingles-con-claude-sin-que-suene-a-google-translate
- [B] SAP SuccessFactors, idiomas de parseo: https://help.sap.com/docs/successfactors-recruiting/setting-up-and-maintaining-sap-successfactors-recruiting/working-with-resume-parsing

Pendiente de verificar: evidencia más sólida sobre preferencia de idioma en procesos regionales (por ejemplo, políticas de contratación de multinacionales con sede en LatAm); si los ATS parsean bien CVs mixtos.

## 7. Tabla: práctica, evidencia y fuerza

| Práctica | Evidencia o fuente | Fuerza |
|---|---|---|
| El ATS no rechaza solo por formato o palabras clave | Greenhouse (Talent Matching no rechaza; revisión humana) y encuesta de Enhancv a 25 reclutadores | Alta (Greenhouse), baja (encuesta) |
| Auto-Reject actúa sobre respuestas del formulario, no sobre el CV | Greenhouse, Application Rules Overview | Alta |
| "El 75 % de los CV se descarta por ATS" | Sin fuente primaria (rastreo a un argumento comercial de 2012, no verificado) | Folclore |
| Una columna, sin tablas ni cuadros de texto | Greenhouse (causas de parseo fallido), prueba de Jobscan en Lever | Alta |
| Nombre y contacto en el cuerpo, no en encabezado o pie | Greenhouse, iCIMS, RChilli | Alta |
| Sin foto, gráficos ni íconos en la versión ATS | Greenhouse (fotos y gráficos); prácticas chilena y anglosajona | Alta (ATS), media (norma local) |
| Archivo con texto real, no escaneado | Greenhouse, SAP SuccessFactors, API de SmartRecruiters | Alta |
| Menos de 2,5 MB | Greenhouse | Alta |
| PDF por defecto, DOCX si el portal lo exige o el parseo falla | Workday, iCIMS aceptan ambos; fuentes de consejo se contradicen | Media |
| Títulos de sección estándar | Buk, Jobscan, G-Talent | Media |
| Fechas "Mes Año" consistentes, rango en una línea | Jobscan, RChilli, Santa Clara University | Media |
| Cargos completos y empresas con nombre legal reconocible | Greenhouse | Alta |
| URL visible como texto, no solo hipervínculo | Prueba de Jobscan en Lever | Media |
| Tipografía sans común, 10 a 12 pt | Jobscan (método no publicado) | Baja |
| Fuente incrustada con ToUnicode | Prueba propia (`pdffonts`, `uni = yes`); XeTeX/xdvipdfmx lo hace por defecto | Alta |
| `Ligatures={TeX,NoCommon}` en XeLaTeX | Prueba propia: sin ello "ff" se extrae como U+FB00 | Alta |
| No usar `LetterSpace` ni versalitas en el CV ATS | Prueba propia: pypdf partió "EXPERIENCIA" | Alta (2 extractores) |
| Fechas en el mismo bloque de texto que el cargo (sin `\hfill`) | Prueba propia con pdftotext sin layout | Alta (prueba), media (relevancia) |
| Viñeta explícita "•" | Prueba propia: la viñeta por defecto no se extrajo | Alta |
| Sin guionado y alineado a la izquierda | Razonamiento propio | Baja |
| Metadatos del PDF (título, autor, idioma) | Higiene; sin evidencia de efecto en ATS | Baja |
| Lectura inicial de pocos segundos | TheLadders 2018 (método poco documentado) | Baja a media |
| Viñetas con verbo de acción y resultado | Harvard OCS; fórmula de Bock | Alta (Harvard), media (Bock) |
| Cuantificar sin inventar; rotular estimado y en desarrollo | Regla de veracidad de Agente0 | Regla del proyecto |
| Hasta dos páginas con 5 años o más de experiencia | Randstad, BioBioChile, ResumeGo (no probó ATS) | Baja a media |
| Omitir edad, estado civil, RUT, referencias, objetivo genérico | BioBioChile, Adecco, G-Talent, Harvard | Media |
| Foto: omitir en el CV ATS | Greenhouse; Harvard; normas locales variables | Media |
| Términos relacionados y sinónimos se buscan; no apilar | Greenhouse, Workday Skills Cloud, SmartRecruiters | Alta (Greenhouse), media (otros) |
| Palabra clave solo si hay evidencia; una vez en contexto y una en habilidades | G-Talent, Buk; regla de veracidad | Media |
| Habilidades sin barras de nivel | Greenhouse (gráficos rompen el parseo) | Alta (gráficos), media (aplicación a barras) |
| Coherencia CV y LinkedIn | Greenhouse, consejo de un reclutador | Media |
| CV en el idioma del aviso; base en español y variante en inglés | G-Talent, Deel, weremoto; criterio propio | Baja |
| Nombre de archivo `Nombre-Apellido-CV.pdf` | Jobscan, G-Talent (las fuentes se contradicen sobre su efecto) | Baja |

## 8. Checklist para validar un CV ATS antes de enviarlo

Reutilizable por cualquier variante (B7). Marcar cada punto; si algo falla, corregir y recompilar.

Archivo y formato
- [ ] A4, una columna, sin tablas, cuadros de texto, TikZ ni texto posicionado.
- [ ] Sin foto, íconos, gráficos ni barras de nivel.
- [ ] Nombre y contacto en el cuerpo (no en encabezado ni pie).
- [ ] Contacto completo en texto: correo, teléfono, ciudad o región, LinkedIn y GitHub como texto visible.
- [ ] Peso del archivo por debajo de 1 MB (límite duro 2,5 MB en Greenhouse).
- [ ] Nombre del archivo `Nombre-Apellido-CV.pdf` (o con el cargo), sin espacios ni tildes.
- [ ] Número de páginas: 2 como máximo; una si el aviso lo favorece; sin relleno. La primera página reúne perfil y los cargos.

Extracción (comandos)
- [ ] `pdfinfo archivo.pdf` muestra A4, el número de páginas esperado y título y autor correctos.
- [ ] `pdffonts archivo.pdf`: todas las fuentes con `emb yes` y `uni yes`.
- [ ] `pdftotext -layout archivo.pdf -` y `pdftotext archivo.pdf -`: orden de lectura correcto (encabezado, perfil, experiencia, habilidades, educación), sin palabras partidas, sin párrafos mezclados.
- [ ] Un extractor distinto (por ejemplo, `pypdf`) devuelve el mismo texto sin palabras partidas.
- [ ] Sin ligaduras ni caracteres raros: `pdftotext archivo.pdf - | grep -P '[\x{FB00}-\x{FB06}\x{FFFD}]'` no devuelve nada.
- [ ] Tildes y eñe intactas (revisar una por una las palabras con á, é, í, ó, ú, ñ).
- [ ] Cada fecha está en la misma línea que su rango completo, y cada cargo, empresa y fecha se leen como un bloque.
- [ ] Todas las palabras del `.tex` aparecen en la extracción.
- [ ] Copiar y pegar el texto del PDF en un editor de texto plano se lee en orden.
- [ ] `pdftoppm -png -r 110 archivo.pdf pg` y revisión visual: sin solapamientos, sin líneas de una sola palabra, sin texto fuera de margen.

Estructura y fechas
- [ ] Títulos de sección estándar (Perfil profesional, Experiencia laboral, Habilidades, Educación, Idiomas, Proyectos).
- [ ] Cronología inversa; "Mes Año" o "MM/AAAA" con un solo formato; rangos completos; "Actualidad" para lo vigente.
- [ ] Cargos completos (sin abreviaturas) y empresas con su nombre reconocible.

Contenido y veracidad
- [ ] Cada afirmación está respaldada por el perfil confirmado; auditoría `afirmación -> dato del perfil` hecha y aprobada.
- [ ] Cargos, empresas y fechas idénticos al perfil. Un descriptor informal (por ejemplo "Lead") solo si el perfil lo permite y sin presentarlo como cargo contractual.
- [ ] Cifras exactamente como el perfil las permite: aproximadas con "aproximadamente", agregadas con "en conjunto", estimadas con "estimado" y su método, en desarrollo con "en desarrollo".
- [ ] Sin cifras, ahorros, certificaciones ni herramientas que el perfil no confirme; sin palabras de la vacante que no sean habilidades demostradas.
- [ ] Herramientas conocidas solo por proyectos propios rotuladas como tales.
- [ ] Sin liderazgo jerárquico, presupuesto ni "equipo liderado" que el perfil no respalde.
- [ ] Proyectos propios con estado real (en desarrollo, pausado) y sin resultados no verificados.
- [ ] Idioma declarado con el nivel real y su condición (autoevaluado o certificado).
- [ ] Omitidos: foto, edad, estado civil, RUT, nacionalidad, dirección exacta, referencias, objetivo genérico.

Palabras clave y adaptación
- [ ] Titular con el cargo estándar del aviso (si es cierto) o de la familia de cargos.
- [ ] Términos de la vacante presentes solo si hay evidencia, una vez en perfil o experiencia con contexto y una en habilidades; sin texto oculto ni repeticiones.
- [ ] Siglas y nombre completo escritos cuando el aviso usa ambos.
- [ ] Orden de las habilidades y de las viñetas ajustado a la vacante; hechos sin cambios.
- [ ] Coherente con el perfil de LinkedIn.
- [ ] Idioma del CV igual al del aviso.

Envío
- [ ] Formato pedido por el portal (PDF o DOCX); si es DOCX, repetir las verificaciones de extracción sobre el DOCX.
- [ ] Tras subir el archivo, si el portal autocompleta campos, revisarlos uno por uno (cargos, fechas, educación).
- [ ] Instantánea inmutable del CV enviado guardada junto con la postulación (regla 5 de Agente0).

## Registro de cambios

| Fecha | Qué cambió | Por qué |
|---|---|---|
| 2026-11-18 | Creación inicial del documento: resumen, seis secciones temáticas, tabla de evidencia y checklist. Incluye pruebas propias de extracción con tectonic 0.16.9, pdftotext y pypdf. | Ítem B3 (CV base ATS): fundamentar el formato y el contenido del CV base antes de construirlo. |
