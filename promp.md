¡Perfecto — buen objetivo! 🚀
Te propongo un plan técnico completo y listo para implementar que cubre arquitectura, responsabilidades de cada componente, esquemas de datos, ejemplos concretos de prompts para el Orchestrator (ADK) y los agentes especializados, snippets de código (Webhook Cloud Run + Orchestrator pseudocódigo), pipeline de embeddings & vector search, manejo de memoria (últimos 50 mensajes), seguridad y pruebas.

Lo siguiente es un **plan ejecutable** (sin hacerte preguntas adicionales) que puedes tomar tal cual o adaptar.

# 1) Visión general / Principios de diseño

* **Modularidad**: cada agente es responsable de un dominio (TRÁMITES, PQRSD, PROGRAMAS, NOTIFICACIONES). El Orchestrator solo enruta, mantiene contexto y memoria corta.
* **Separation of concerns**: interfaz (Telegram) ↔ Orchestrator ↔ Agents ↔ Knowledge Layer.
* **Escalabilidad**: Cloud Run (stateless) para webhook; Orchestrator como servicio desplegable (Cloud Run / GKE) y agentes escalables.
* **Privacidad y retención**: almacenar mínimo necesario y cifrar datos sensibles en reposo/transito; cumplir normas locales (Habeas Data / ley de protección de datos — incluye requisitos de consentimiento, posibilidad de borrar datos por usuario).
* **Observabilidad**: logs estructurados, traces (Cloud Trace), métricas (Prometheus/Cloud Monitoring).

# 2) Flujo de alto nivel

1. Usuario escribe a bot Telegram → Telegram envía POST al **Webhook (Cloud Run)**.
2. Webhook normaliza mensaje, recupera `session_id` y últimos 50 mensajes de **Firestore** (memoria de sesión), envía paquete al **Orchestrator (ADK)**.
3. Orchestrator ejecuta:

   * Clasificación de intención (intent classifier).
   * Recupera contexto + embeddings relevantes (Vertex Vector Search).
   * Decide routing a agente especializado.
   * Envia prompt + contexto al agente destino (o ejecuta tools).
4. Agente realiza acción (buscar trámite en Cloud SQL, crear radicado en Firestore, llamar API externa) y devuelve respuesta.
5. Orchestrator aplica formato final y responde al Webhook → Telegram → usuario.
6. Persistencia transaccional: Firestore para eventos / radicados; Cloud SQL para catálogo estructurado; Vector DB (Vertex) para embeddings.

# 3) Componentes y responsabilidades

## A. Telegram Bot Interface (Cloud Run)

* **Responsabilidad**: recibir webhook, autenticación del request (token Telegram), normalizar mensajes, rate limiting, forward a Orchestrator.
* **Tech**: Python (FastAPI/Flask) o Node.js (Express).
* **Outputs**: `session_id`, `user_id`, `message_text`, `attachments`, `timestamp`.

## B. Orchestrator Agent (ADK)

Funciones:

* **Intent classification**: modelo ligero (fasttext, scikit-learn) o LLM few-shot.
* **Routing**: rules + confidence thresholds (if low confidence -> preguntar clarificación / transferir a humano).
* **Context manager**: compone prompt del agente con memoria (últimos 50 mensajes).
* **Session memory**: persistir en Firestore.
* **Tool invocation**: llamadas a APIs (Cloud SQL, Firestore, APIs externas).
* **Fallback**: caso humano / cola.

## C. Domain Agents (TRÁMITES, PQRSD, PROGRAMAS, NOTIFICACIONES)

* Cada uno tiene:

  * **Prompt template** que guía su output.
  * **Tools**: búsqueda en Cloud SQL, crear radicado en Firestore, APIs municipales, generador de documentos, validación de datos.
  * **Policies**: validaciones y límites (p. ej. no dar asesoría legal, sólo información).

## D. Knowledge Layer

* **Vertex AI Vector Search**: embeddings de documentos (PDFs, FAQs, normativas).
* **Firestore**: sesiones, transacciones (radicados), logs de conversaciones (indices temporales).
* **Cloud SQL (Postgres/MySQL)**: catálogo de trámites (estructurado) con relaciones y versionado.

# 4) Esquemas de datos sugeridos

## Firestore (NoSQL — colecciones)

* `sessions/{session_id}`:

  * `user_id`, `created_at`, `last_active`, `messages` (array of last 50 message metadata — store only text + role + timestamp + embedding_id?)
  * `memory_summary` (optional short summary)
* `radicados/{radicado_id}`:

  * `user_id`, `tipo`, `entidad`, `status`, `created_at`, `meta` (campos libres), `attachments`
* `logs/{log_id}`:

  * `session_id`, `component`, `action`, `payload`, `timestamp`

**Nota**: almacenar solo lo esencial; si hay datos sensibles (documentos de identidad) cifrar y/o no guardar.

## Cloud SQL (Relacional — ejemplo Postgres)

Tabla `tramites`:

```
id SERIAL PRIMARY KEY
codigo VARCHAR UNIQUE
titulo TEXT
descripcion TEXT
requisitos JSONB
plazos VARCHAR
costo VARCHAR
ubicacion_oficinas JSONB  -- list of {name,address,lat,lng,horario}
entidad VARCHAR
categoria VARCHAR
version INT
updated_at TIMESTAMP
```

Tabla `programas_sociales`:

```
id, nombre, elegibilidad_criteria JSONB, descripcion, periodo, contact_info JSONB
```

# 5) Memoria de sesión: diseño y algoritmo

* **Objetivo**: mantener últimos 50 mensajes por sesión y un `memory_summary` que capture puntos persistentes (p. ej. dirección, número de documento — si aplicable y con consentimiento).
* **Implementación**:

  * En Firestore `sessions/{id}.messages` como array o subcolección `sessions/{id}/messages` con timestamp y role.
  * Cuando el array excede 50, eliminar más antiguos.
  * Opcional: cada N mensajes (ej. 10) ejecutar función que resuma la sesión en `memory_summary` (modelos de resumen).
* **Uso en prompts**: incluir `memory_summary` + los últimos N mensajes (p. ej. 8) para mantener contexto.

# 6) Clasificación de intención (intents) — taxonomía sugerida

* `tramite_buscar`
* `tramite_requisitos`
* `tramite_oficinas`
* `pqrsd_crear`
* `pqrsd_estado`
* `programa_buscar`
* `programa_elegibilidad`
* `notificacion_pico_placa`
* `notificacion_cierre_vial`
* `saludo`
* `despedida`
* `clarificacion` (pregunta de back-and-forth)
* `human_escalation`

**Estrategia**:

* Primer paso: intent classifier probabilístico. Si `confidence >= 0.85` → ruta directa; si `0.5-0.85` → pedir 1 pregunta de clarificación; si `<0.5` → fallback humano.
* Entrenar con few-shot prompts + ejemplos o con small ML model (automatable using Vertex AutoML / ML infra). Puedes usar un LLM para clasificación con few-shot examples en prompt si quieres evitar infra ML inicial.

# 7) Prompting: templates (esenciales — en español)

## A. Prompt Orchestrator → Intent classifier (few-shot)

```
Eres un clasificador de intenciones para un bot de atención ciudadana. 
Recibe solo el mensaje del usuario y responde en JSON con { "intent": "...", "confidence": 0-1 }.

Ejemplos:
1) "¿Dónde puedo pagar el impuesto de industria?" -> {"intent":"tramite_buscar","confidence":0.95}
2) "Quiero crear una queja formal contra el servicio de agua" -> {"intent":"pqrsd_crear","confidence":0.98}
3) "¿Habrá cierre vial mañana en mi barrio?" -> {"intent":"notificacion_cierre_vial","confidence":0.92}

Ahora clasifica este mensaje: 
MESSAGE: "{user_message}"
```

## B. Prompt Orchestrator → Domain routing + instructions (span)

```
Eres un Orchestrator que decide a cuál agente enviar la petición. 
Input: { "intent": "...", "user_message": "...", "session_summary": "...", "last_messages": [...] }
Reglas:
- Si intent contiene "tramite" -> TRAMITES_AGENT
- Si intent contiene "pqrsd" -> PQRSD_AGENT
- Si intent contiene "programa" -> PROGRAMAS_AGENT
- Si intent contiene "pico" o "cierre" -> NOTIFICACIONES_AGENT
- Si confidence < 0.5 -> RESPONDER: "No entendí. ¿Puedes especificar?" (no enrutar)

Output JSON:
{ "route": "TRAMITES_AGENT", "reason": "..." }
```

## C. TRÁMITES_AGENT prompt template (para obtener info de Cloud SQL + respuesta)

```
Contexto: usuario pregunta sobre un trámite. Tienes acceso al catálogo estructurado y a los últimos mensajes de la sesión.
Tarea: 1) Buscar trámite que mejor coincida con la consulta (usar los campos: titulo, descripcion, requisitos), 2) Responder con: nombre del trámite, requisitos en lista, plazos, costo, oficinas cercanas (si hay), pasos a seguir y enlace de referencia.
Formato de salida: JSON + texto humano.

Ejemplo de salida JSON:
{
  "match_score": 0.93,
  "tramite": {
    "titulo": "...",
    "requisitos": ["...","..."],
    "plazos": "...",
    "costo": "...",
    "oficinas": [{"name":"", "address":"", "hours":""}],
    "pasos": ["Paso 1: ...", "Paso 2: ..."],
    "fuente": "url"
  },
  "texto_usuario": "Respuesta amigable en 3-5 frases en español."
}

INCLUYE SOLO información verificada del catálogo.
```

## D. PQRSD_AGENT (generar radicado)

```
Tarea: Genera un radicado (ticket) con la siguiente info y guíalo en el proceso administrativo.
Inputs: {user_metadata}, {descripcion_queja}, {adjuntos?}
Acciones: 1) Validar que la queja tenga entidad destino; 2) Generar `radicado_id` (UUID); 3) Persistir en Firestore; 4) Responder al usuario con número de radicado, plazos estimados y pasos siguientes.
Formato de salida: JSON con campos: radicado_id, entidad, fecha, estado_inicial, mensaje_usuario.
```

# 8) Snippets prácticos

## A. Webhook handler (Python + Flask) — Cloud Run

```python
# app.py
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)
ORCHESTRATOR_URL = os.environ['ORCHESTRATOR_URL']
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']

@app.route("/", methods=["POST"])
def webhook():
    payload = request.get_json()
    # Basic Telegram update
    chat_id = payload.get("message", {}).get("chat", {}).get("id")
    user_id = payload.get("message", {}).get("from", {}).get("id")
    text = payload.get("message", {}).get("text", "")
    # Build session_id (user_id or hashed)
    session_id = f"tg:{chat_id}"
    # Forward to orchestrator
    resp = requests.post(ORCHESTRATOR_URL + "/process", json={
        "session_id": session_id,
        "user_id": user_id,
        "text": text,
        "raw": payload
    }, timeout=15)
    return jsonify({"status":"ok"}), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

## B. Orchestrator pseudocódigo (high-level)

```python
def process(request_json):
    session_id = request_json["session_id"]
    user_id = request_json["user_id"]
    text = request_json["text"]
    # 1. load last 50 messages from Firestore
    messages = load_messages(session_id)
    # 2. call intent classifier
    intent_resp = intent_classify(text)
    if intent_resp['confidence'] < 0.5:
        reply = "Disculpa, no entendí. ¿Puedes reformular?"
        send_to_telegram(session_id, reply)
        return
    route = route_decision(intent_resp['intent'])
    # 3. enrich with vector search (retrieve 3 most similar docs)
    docs = vertex_vector_search(text, top_k=3)
    # 4. compile prompt for agent
    agent_payload = {
       "session_id": session_id,
       "user_id": user_id,
       "text": text,
       "docs": docs,
       "messages": messages
    }
    # 5. call domain agent
    agent_response = call_agent(route, agent_payload)
    # 6. persist logs & update session memory
    save_message(session_id, text, role='user')
    save_message(session_id, agent_response['texto_usuario'], role='agent')
    # 7. send to Telegram
    send_to_telegram(session_id, agent_response['texto_usuario'])
```

# 9) Pipeline de embeddings (Document ingestion → Vertex Vector Search)

1. **Ingest documents** (PDFs, FAQs, normativas) into Cloud Storage.
2. **Preprocess**: OCR if necesario, clean text, split en chunks (500–1000 tokens) con metadatos (source, section, url).
3. **Embeddings**: ejecutar embedding model (Vertex or OpenAI) para cada chunk.
4. **Indexar**: subir embeddings y metadatos al Vertex Vector Search (o alternativa).
5. **Query time**: al buscar, hacer embedding del query y buscar top_k chunks; devolver metadatos al Orchestrator.

# 10) Acciones / Tools externas

* `BuscarTramites(cloudsql_query)`: busca en Cloud SQL por palabras clave + fuzzy match.
* `CrearRadicado(firestore_insert)`: escribe en Firestore e imprime radicado_id.
* `PicoPlacaAPI(geo)`: consulta servicio externo municipal para restricciones.
* `Notificaciones(push or Telegram)`: enviar mensajes proactivos (necesita opt-in).

# 11) Manejo humano / Escalamiento

* Si `intent == human_escalation` o `confidence < 0.5` repetido → abrir incidente en herramienta de atención (Zendesk/Intercom) con transcript y metadata (session_id, user_id, intent_probs).
* Incluir botón "Hablar con un asesor" en mensajes cuando corresponda.

# 12) Seguridad, privacidad y cumplimiento

* **Autenticación**: credenciales seguras para servicios (Secret Manager).
* **Auditoría**: registrar acciones sensibles en logs inmutables.
* **Encriptación**: datos sensibles cifrados en Reposo y TLS en tránsito.
* **Consentimiento**: notificar al usuario en el primer contacto que las conversaciones pueden almacenarse y pedir consentimiento para acciones (ej. crear radicado).
* **Borrado**: mecanismo para borrar sesión y datos por petición del usuario.

# 13) Testing y despliegue

* **Unit tests**: para funciones de parsing, DB queries, herramientas.
* **E2E tests**: flujo Telegram → Orchestrator → Agent → Telegram simulando varios intents.
* **Canary deploy**: empezar con porcentaje pequeño de tráfico en Cloud Run.
* **Monitoreo**: latencia, error rate, intents no reconocidos, sesiones activas.

# 14) Roadmap de implementación (priorizado - 8 sprints sugeridos)

1. Sprint 1: Webhook Cloud Run + Orchestrator minimal (intent classifier rule-based) + Firestore sessions.
2. Sprint 2: TRÁMITES agent básico con Cloud SQL y búsqueda simple.
3. Sprint 3: PQRSD agent — crear radicados en Firestore.
4. Sprint 4: Programas agent + vector search de FAQ mínimos.
5. Sprint 5: Integración Vertex embeddings y mejorar retrieval.
6. Sprint 6: NOTIFICACIONES agent + APIs externas (pico/placa).
7. Sprint 7: Seguridad, consentimientos, redacción legal.
8. Sprint 8: Observabilidad, tests automatizados y escalado.

# 15) Consideraciones operacionales y tips prácticos

* **Rate limits Telegram**: mantener retries exponenciales; evitar respuestas largas (usar split).
* **Cost control**: embeddings y LLM calls son los costos principales — cachear resultados y usar heurísticas (cuando `intent` es FAQ simple, responder con stored text en vez de LLM).
* **Human-in-loop**: para primeras versiones, tener humanos revisando radicados generados (control de calidad).

# 16) Entregables que te puedo dar ahora (elige lo que quieres que genere inmediatamente)

* A) Código completo del webhook + Orchestrator (Python/Node) listo para Cloud Run.
* B) Scripts SQL para crear el catálogo en Cloud SQL + ejemplo de datos.
* C) Pipeline de ingestion de documentos (Python) + code para embeddings + cargar a Vertex.
* D) Set de prompts en español (fino) para Orchestrator y cada agente (lista de ~20 prompts y few-shot examples).
* E) Plantilla de pruebas E2E (cypress/pytest + mocks).
* F) Documento de políticas de privacidad y consentimiento (borrador para incluir en bot).

Dime cuál(es) quieres que te entregue **ahora** y lo creo en el siguiente bloque (p. ej. "A y D"). No esperaré a nada: produciré el entregable seleccionado **en esta respuesta**.
