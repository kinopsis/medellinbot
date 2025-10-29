# Fuentes de Información para MedellínBot - Agentes y Web Scraping

## Documento de Referencia: Fuentes de Datos por Agente

Este documento detalla todas las fuentes web que deben ser utilizadas para alimentar los cuatro agentes especializados de MedellínBot mediante técnicas de web scraping, APIs públicas y acceso a datos abiertos.

---

## 1. AGENTE DE TRÁMITES

### 1.1 Fuentes Principales - Alcaldía de Medellín

| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Portal Trámites y Servicios | https://www.medellin.gov.co/es/tramites-y-servicios/ | Catálogo completo de trámites municipales, requisitos, costos, tiempos | Web scraping |
| Portal Tributario | https://www.medellin.gov.co/es/secretaria-de-hacienda/portal-tributario/ | Trámites de impuestos, servicios en línea, certificados | Web scraping |
| Pago de Impuestos | https://www.medellin.gov.co/es/pago-de-impuestos-alcaldia-de-medellin/ | Predial, industria y comercio, otros impuestos | Web scraping |
| Movilidad en Línea | https://www.medellin.gov.co/portal-movilidad/ | Trámites de tránsito de Medellín | Web scraping |

### 1.2 Datos Estructurados Requeridos

Por cada trámite se debe extraer:
- Nombre del trámite
- Descripción breve
- Requisitos (documentos necesarios)
- Costo (en pesos colombianos)
- Tiempo de respuesta
- Canales disponibles (presencial, en línea, telefónico)
- Direcciones y horarios de atención
- Enlaces a formularios o pagos en línea
- Entidad responsable

### 1.3 Frecuencia de Actualización
- Semanal para información general
- Diaria para tarifas y horarios

---

## 2. AGENTE DE PQRSD (Router Inteligente)

### 2.1 Fuentes - Alcaldía de Medellín

| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Portal PQRSD Alcaldía | https://www.medellin.gov.co/es/pqrsd/ | Lineamientos, proceso, entidades competentes | Web scraping |
| Servicio Ciudadanía | https://www.medellin.gov.co/es/secretaria-de-gestion-humana/servicio-a-la-ciudadania/ | Canales de atención, sedes | Web scraping |

### 2.2 Fuentes - Entidades Municipales y Regionales

#### EPM (Empresas Públicas de Medellín)
| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Servicio al Cliente EPM | https://www.epm.com.co/clientesyusuarios/servicio-al-cliente | Canales atención, PQRSD servicios públicos | Web scraping |
| Comunícate con EPM | https://www.epm.com.co/clientesyusuarios/servicio-al-cliente/comunicate-con-nosotros | Líneas de contacto, WhatsApp, chat | Web scraping |
| Menú Atención EPM | Manual de atención y servicios | Tipos de solicitudes, tiempos respuesta | Documento oficial |

#### Metro de Medellín
| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Portal Metro | https://www.metrodemedellin.gov.co | Información general, servicios | Web scraping |
| Atención Pasajeros | https://metromedellin.com.co | Teléfono atención, horarios, contacto | Web scraping |

#### Emvarias (Aseo y Basuras)
| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Portal Emvarias | https://www.emvarias.com.co/emvarias | Servicios de aseo, contacto | Web scraping |
| Sedes y Puntos | https://www.emvarias.com.co/emvarias/sedesypuntos | Direcciones, líneas atención, WhatsApp | Web scraping |
| Servicios Especiales | https://www.emvarias.com.co/emvarias/serviciosespeciales | Escombros, RCD, residuos vegetales | Web scraping |

#### Policía Nacional - Medellín
| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| PQRS Policía | https://www.policia.gov.co/pqrs | Portal de denuncias y quejas | Web scraping |
| Directorio Policía Medellín | https://www.policia.gov.co/directorio/292355 | Teléfonos, direcciones comisarías | Web scraping |
| Inspecciones Policía | https://www.medellin.gov.co/es/secretaria-seguridad/seguridad-y-convivencia/inspecciones-de-policia/ | Competencias, ubicación | Web scraping |

#### Fiscalía General de la Nación
| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Portal Denuncias Fiscalía | https://www.fiscalia.gov.co/colombia/servicios-de-informacion-al-ciudadano/donde-y-como-denunciar/ | Canales denuncia, requisitos | Web scraping |
| Centro de Contacto | https://www.fiscalia.gov.co/colombia/servicios-de-informacion-al-ciudadano/centro-de-contacto/ | Línea 122, horarios | Web scraping |
| Consulta Denuncias | https://www.fiscalia.gov.co/colombia/portafolio-de-servicios/consulte-el-estado-de-su-denuncia/ | Seguimiento NUNC | Web scraping |
| Denuncia Virtual | https://sicecon.fiscalia.gov.co/denuncia/ingresoPrincipal | Formulario en línea | Integración API |

#### Personería de Medellín
| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Portal Personería | https://www.personeriamedellin.gov.co | Derechos humanos, tutelas, contacto | Web scraping |
| Línea Anticorrupción | Información de contacto | Teléfonos 3849999, correos | Documento |

#### INDER (Instituto Deportes y Recreación)
| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Portal INDER | https://www.inder.gov.co | Programas deportivos, escenarios | Web scraping |
| Directorio Institucional | https://www.inder.gov.co/directorio-institucional/ | Contactos por dependencia | Web scraping |
| Atención Ciudadano | atencion.ciudadano@inder.gov.co, Tel 369-9000 | Email y teléfono | Documento |

### 2.3 Datos Estructurados Requeridos

Por cada entidad competente:
- Nombre de la entidad
- Competencias (temas que atiende)
- Canales de contacto (teléfono, email, web, WhatsApp)
- Horarios de atención
- Direcciones físicas
- Proceso para radicar PQRSD
- Tiempos de respuesta según normativa

### 2.4 Mapeo de Competencias

**Alcaldía de Medellín:**
- Trámites municipales
- Impuestos locales
- Programas sociales
- Espacio público
- Obras públicas
- Cultura y educación

**EPM:**
- Agua potable
- Energía eléctrica
- Gas natural
- Telecomunicaciones
- Daños en servicios públicos

**Metro de Medellín:**
- Transporte masivo
- Estaciones y cables
- Tarjetas Cívica

**Emvarias:**
- Recolección basuras
- Aseo público
- Escombros y RCD
- Residuos especiales

**Policía Nacional:**
- Ruido y perturbación
- Consumo sustancias psicoactivas
- Venta ambulante ilegal
- Seguridad ciudadana

**Fiscalía:**
- Denuncias penales
- Delitos (hurto, lesiones, estafa, etc.)
- Casos de corrupción

**Personería:**
- Derechos humanos
- Tutelas
- Vigilancia conducta oficial

**INDER:**
- Escenarios deportivos
- Programas recreativos
- Eventos deportivos

### 2.5 Frecuencia de Actualización
- Mensual para información de contacto
- Trimestral para competencias y procesos

---

## 3. AGENTE DE PROGRAMAS SOCIALES

### 3.1 Fuentes Principales

#### Medellín Te Quiere Saludable
| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Noticias MTQS | https://www.medellin.gov.co/es/sala-de-prensa/noticias/el-programa-medellin-te-quiere-saludable-impactara-a-800-000-personas-en-2025/ | Cobertura, servicios, población objetivo | Web scraping |
| Secretaría de Salud | https://www.medellin.gov.co/es/secretaria-de-salud/ | Programas de salud pública | Web scraping |
| Subsecretaría Salud Pública | https://www.medellin.gov.co/es/secretaria-de-salud/subsecretaria-de-salud-publica/ | Estrategias de atención | Web scraping |

#### Buen Comienzo
| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Portal Buen Comienzo | https://www.medellin.gov.co/es/secretaria-de-educacion/estudiantes/buen-comienzo/ | Modalidades, requisitos, contacto | Web scraping |
| Inscripciones 2025 | https://www.medellin.edu.co/estudiantes/buen-comienzo/ | Proceso inscripción, "Busca Tu Cupo" | Web scraping |
| Noticias Buen Comienzo | https://www.medellin.gov.co/es/sala-de-prensa/noticias/buen-comienzo-365-transforma-la-vida-de-la-primera-infancia-de-medellin/ | Novedades, Buen Comienzo 365 | Web scraping |
| Metrosalud - Entorno Familiar | https://www.metrosalud.gov.co/metrosalud/pyp/71-buen-comienzo | Atención 0-2 años, modalidad familiar | Web scraping |

#### Subsidios de Vivienda
| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| ISVIMED | https://isvimed.gov.co | Programas de vivienda social | Web scraping |

#### Otros Programas
| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Plan de Desarrollo | Portal Alcaldía sección programas | Todos los programas vigentes | Web scraping |
| Secretaría Inclusión Social | Portal oficial | Programas población vulnerable | Web scraping |

### 3.2 Datos Estructurados Requeridos

Por cada programa:
- Nombre del programa
- Descripción y objetivos
- Población objetivo (edad, ubicación, condición socioeconómica)
- Requisitos de elegibilidad
- Beneficios ofrecidos
- Proceso de inscripción (paso a paso)
- Documentos requeridos
- Contactos (teléfono, correo, dirección)
- Enlaces web para inscripción
- Fechas de convocatorias (si aplica)

### 3.3 Frecuencia de Actualización
- Mensual para información general
- Semanal durante periodos de inscripción

---

## 4. AGENTE DE NOTIFICACIONES

### 4.1 Pico y Placa

| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Pico y Placa Oficial | https://www.medellin.gov.co/es/secretaria-de-movilidad/pico-y-placa-medellin-hoy/ | Rotación semestral, horarios, vías exentas | Web scraping |
| Secretaría Movilidad | https://www.medellin.gov.co/es/secretaria-de-movilidad/ | Cierres viales, eventos | Web scraping |
| API Pico y Placa | https://rapidapi.com/tortutales/api/pico-y-placa-medellin | API de consulta (evaluar) | API REST |
| Noticias Pico Placa | Portales de noticias locales | Actualizaciones semanales | Web scraping |

### 4.2 Cierres Viales y Movilidad

| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Geo Medellín | https://www.medellin.gov.co/irj/portal/medellin?NavigationTarget=contenido%2F6989-Geomedellin-el-portal-de-datos-geograficos-del-Municipio-de-Medellin | Mapa cierres viales, control movilidad | Web scraping / API |
| SIMM - Sistema Movilidad | Secretaría de Movilidad | Sistema inteligente de movilidad | API si disponible |
| Twitter/X @STTMed | https://www.instagram.com/sttmed/ y redes sociales | Alertas en tiempo real | Social media API |

### 4.3 Eventos y Actividades

| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| MEData - Eventos | https://medata.gov.co | Eventos culturales, deportivos, comunitarios | API de datos abiertos |
| Portal MEData | https://www.medellin.gov.co/irj/portal/medellin?NavigationTarget=contenido%2F6991-MEData-el-portal-de-datos-publicos-del-Municipio-de-Medellin | Acceso datasets públicos | Web scraping / API |
| Agenda Cultural Alcaldía | Portal de cultura | Eventos por comuna | Web scraping |
| INDER Eventos | https://www.inder.gov.co | Actividades deportivas y recreativas | Web scraping |

### 4.4 Datos Estructurados Requeridos

**Pico y Placa:**
- Fecha actual
- Dígitos con restricción (carros y motos)
- Horario de restricción
- Vías exentas
- Excepciones (vehículos eléctricos, híbridos, GNC)

**Cierres Viales:**
- Fecha y hora del cierre
- Ubicación exacta (calle, carrera, intersección)
- Motivo del cierre
- Duración estimada
- Rutas alternas
- Comuna afectada

**Eventos:**
- Nombre del evento
- Fecha y hora
- Ubicación (dirección, barrio, comuna)
- Tipo de evento (cultural, deportivo, salud, etc.)
- Público objetivo
- Costo (gratuito o con valor)
- Contacto organizador

### 4.5 Frecuencia de Actualización
- **Pico y Placa:** Diaria a las 00:00 AM
- **Cierres viales:** Cada 2 horas (tiempo real)
- **Eventos:** Semanal (lunes a las 8:00 AM)

---

## 5. FUENTES COMPLEMENTARIAS

### 5.1 Datos Abiertos

| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| MEData | https://medata.gov.co | Portal datos abiertos Medellín, 31 dependencias, 12 temáticas | API REST / CSV |
| MEData - Búsqueda | https://medata.gov.co/search | Buscador de datasets | Web scraping |
| Datos Abiertos Colombia | https://www.datos.gov.co | Datasets nacionales y municipales | API REST |
| Geo Medellín | Portal geográfico | Información georreferenciada, POT, mapas | API GIS |
| Datos Metro | https://datosabiertos-metrodemedellin.opendata.arcgis.com | Información transporte Metro | API ArcGIS |
| Datos Área Metropolitana | https://datosabiertos.metropol.gov.co | Datos regionales Valle de Aburrá | API REST |

### 5.2 Normativa y Documentos Oficiales

| Fuente | URL | Contenido | Método |
|--------|-----|-----------|--------|
| Normativa PQRSD Colombia | https://colaboracion.dnp.gov.co/CDT/Programa%20Nacional%20del%20Servicio%20al%20Ciudadano/ | Criterios normativos, procedimientos | Descarga PDF |
| Acuerdos Municipales | Portal Alcaldía - Normativa | Estatutos, decretos, resoluciones | Web scraping |
| Código de Policía | Ley 1801 de 2016 | Comportamientos contrarios convivencia | Documento oficial |

### 5.3 Google Maps API

| Servicio | Uso | Método |
|----------|-----|--------|
| Places API | Ubicación de oficinas, sedes de atención | API REST |
| Geocoding API | Conversión direcciones a coordenadas | API REST |
| Directions API | Rutas y tiempos de desplazamiento | API REST |

---

## 6. ESTRATEGIA DE WEB SCRAPING

### 6.1 Herramientas Recomendadas

**Python Libraries:**
- BeautifulSoup4: parsing HTML/XML
- Scrapy: framework completo de scraping
- Selenium: para sitios con JavaScript dinámico
- Requests: peticiones HTTP
- lxml: procesamiento XML rápido

**Gestión de scrapers:**
- Scrapy Cloud o ScrapingHub
- Cloud Scheduler + Cloud Functions (ejecución programada)
- Cloud Run (scrapers como servicios)

### 6.2 Buenas Prácticas

1. **Rate Limiting:** No más de 1 request por segundo por dominio
2. **User-Agent:** Identificarse como "MedellinBot/1.0"
3. **Robots.txt:** Respetar restricciones de cada sitio
4. **Caché:** Almacenar contenido con TTL apropiado
5. **Manejo de errores:** Reintentos con backoff exponencial
6. **Monitoreo:** Alertas si scraping falla o cambio en estructura HTML
7. **Logging:** Registrar todas las ejecuciones y errores

### 6.3 Almacenamiento de Datos Scrapeados

**Cloud SQL (PostgreSQL):**
- Tablas: tramites, entidades_pqrsd, programas_sociales, eventos
- Campos de metadata: fecha_scraping, url_fuente, version

**Firestore:**
- Colecciones: pico_placa_diario, cierres_viales_activos
- Datos transitorios con TTL

**Cloud Storage:**
- Archivos HTML/JSON originales (backup)
- Carpetas por fecha: gs://medellinbot-scraping/YYYY-MM-DD/

### 6.4 Procesamiento Post-Scraping

1. **Limpieza:** Eliminar HTML, caracteres especiales, normalizar texto
2. **Validación:** Verificar campos obligatorios completos
3. **Deduplicación:** Evitar registros duplicados
4. **Enriquecimiento:** Agregar embeddings con Vertex AI
5. **Indexación:** Cargar a Vertex AI Vector Search

---

## 7. CRONOGRAMA DE SCRAPING

| Frecuencia | Fuentes | Horario |
|------------|---------|---------|
| Diaria | Pico y placa, impuestos vigentes | 00:00 AM |
| Cada 2 horas | Cierres viales, alertas movilidad | 00:00, 02:00, 04:00... |
| Semanal | Trámites, programas sociales, eventos | Lunes 06:00 AM |
| Mensual | Contactos entidades, normativa | Primer día del mes 08:00 AM |
| Bajo demanda | Información específica de usuario | Tiempo real via API/cache |

---

## 8. MONITOREO Y MANTENIMIENTO

### 8.1 Indicadores de Salud

- % éxito de scrapers (objetivo: >95%)
- Tiempo de ejecución promedio
- Cantidad de registros extraídos vs esperados
- Tasa de errores por fuente

### 8.2 Alertas

**Cloud Monitoring:**
- Alerta si scraper falla 3 veces consecutivas
- Alerta si cambio drástico en cantidad de datos (±30%)
- Alerta si tiempo de ejecución >300% del promedio

**Notificaciones:**
- Email a equipo técnico
- Mensaje Slack/Teams
- Dashboard en Looker Studio

### 8.3 Mantenimiento

- **Revisión mensual:** Verificar que selectores CSS/XPath siguen válidos
- **Actualización de scrapers:** Al detectar cambios en estructura de sitios
- **Pruebas unitarias:** Validar cada scraper en entorno staging antes de producción

---

## 9. CONSIDERACIONES LEGALES

### 9.1 Cumplimiento Normativo

- **Datos públicos:** Toda la información es de portales oficiales y públicos
- **Terms of Service:** Revisar ToS de cada portal antes de scraping
- **Atribución:** Citar fuente en respuestas del bot cuando proceda
- **Actualidad:** Indicar fecha de última actualización de datos

### 9.2 Privacidad

- No scraping de datos personales de ciudadanos
- No almacenar información sensible (salud, judicial, etc.)
- Cumplir con Ley 1581 de 2012 (Protección Datos Colombia)

---

## 10. RESUMEN EJECUTIVO

### Conteo Total de Fuentes

- **Agente Trámites:** 4 fuentes principales
- **Agente PQRSD:** 20+ fuentes (8 entidades con múltiples portales)
- **Agente Programas Sociales:** 10 fuentes
- **Agente Notificaciones:** 8 fuentes
- **Datos Abiertos:** 6 plataformas
- **Total estimado:** 50+ URLs únicas para scraping

### Priorización Fase 1 (MVP)

**Alta prioridad:**
1. Trámites Alcaldía (top 20 más consultados)
2. PQRSD Alcaldía, EPM, Policía, Fiscalía (80% de casos)
3. Buen Comienzo y Medellín Te Quiere Saludable
4. Pico y placa

**Media prioridad:**
5. Metro, Emvarias, INDER
6. Cierres viales
7. Eventos culturales

**Baja prioridad (Fase 2):**
8. Resto de programas sociales
9. Trámites especializados
10. Integración completa MEData

---

**Documento generado:** 28 de octubre de 2025

**Versión:** 1.0

**Próxima revisión:** Noviembre 2025 (post-implementación Fase 1)

---