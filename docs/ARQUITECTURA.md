# Asistente Bancolombia - Arquitectura y Conceptos

## Tabla de contenido

1. [Resumen del sistema](#resumen-del-sistema)
2. [Arquitectura general](#arquitectura-general)
3. [Flujo de datos end-to-end](#flujo-de-datos-end-to-end)
4. [Componentes del sistema](#componentes-del-sistema)
   - [Crawler](#1-crawler-crawlerpy)
   - [Base de datos vectorial](#2-base-de-datos-vectorial-databasepy)
   - [Pipeline de indexacion y agente](#3-pipeline-de-indexacion-y-agente-pipelinepy)
   - [Servidor MCP](#4-servidor-mcp-mcp_serverpy)
   - [Interfaz CLI](#5-interfaz-cli-mainpy)
   - [Interfaz Web](#6-interfaz-web-streamlit_apppy)
5. [Conceptos fundamentales](#conceptos-fundamentales)
   - [RAG (Retrieval-Augmented Generation)](#rag-retrieval-augmented-generation)
   - [MCP (Model Context Protocol)](#mcp-model-context-protocol)
   - [Embeddings y busqueda vectorial](#embeddings-y-busqueda-vectorial)
   - [Agentes con herramientas](#agentes-con-herramientas)
   - [Streaming de eventos](#streaming-de-eventos)
   - [Structured output en herramientas](#structured-output-en-herramientas)
6. [Stack tecnologico](#stack-tecnologico)
7. [Estructura de archivos](#estructura-de-archivos)
8. [Infraestructura y despliegue](#infraestructura-y-despliegue)
9. [Testing](#testing)

---

## Resumen del sistema

Este proyecto implementa un **asistente conversacional** especializado en productos y servicios de Bancolombia. El sistema:

1. **Extrae** contenido del sitio web de Bancolombia mediante web crawling automatizado.
2. **Indexa** el contenido en una base de datos vectorial (ChromaDB) usando embeddings multilingues.
3. **Expone** la base de conocimiento como herramientas MCP que un LLM puede invocar.
4. **Responde** preguntas de los usuarios mediante un agente LangChain que consulta las herramientas y genera respuestas con fuentes citadas.

El usuario puede interactuar via una **interfaz web** (Streamlit) o una **CLI** de terminal.

---

## Arquitectura general

```
                                    +-------------------+
                                    |   Usuario final   |
                                    +--------+----------+
                                             |
                              +--------------+--------------+
                              |                             |
                    +---------v---------+        +----------v---------+
                    |  streamlit_app.py |        |      main.py       |
                    |   (Interfaz Web)  |        |   (Interfaz CLI)   |
                    +---------+---------+        +----------+---------+
                              |                             |
                              +-------------+---------------+
                                            |
                                  +---------v----------+
                                  |    pipeline.py     |
                                  | (Orquestador)      |
                                  |  - indexar_datos() |
                                  |  - crear agente    |
                                  +---------+----------+
                                            |
                         +------------------+------------------+
                         |                                     |
              +----------v-----------+              +----------v-----------+
              |   Agente LangChain   |              |    Indexacion        |
              |   (create_agent)     |              |  JSONL -> ChromaDB   |
              +----------+-----------+              +----------+-----------+
                         |                                     |
                         | invoca tools via MCP                |
                         |                                     |
              +----------v-----------+              +----------v-----------+
              |   mcp_server.py      |              |    database.py       |
              |  (Servidor MCP)      |              |  (VectorDBClient)    |
              |  - search_kb         +------+------>+  - ChromaDB          |
              |  - get_article       |      |       |  - HuggingFace      |
              |  - list_categories   |      |       |    Embeddings       |
              +----------------------+      |       +----------------------+
                                            |
                                  +---------v----------+
                                  |    crawler.py      |
                                  | (Web Scraping)     |
                                  |  Crawl4AI +        |
                                  |  Playwright        |
                                  +--------------------+
```

---

## Flujo de datos end-to-end

### Fase 1: Extraccion de datos (Crawler)

```
bancolombia.com  -->  Crawl4AI + Playwright  -->  resultados_bancolombia.jsonl
     (web)            (headless browser)           (JSONL, 1 linea por pagina)
```

El crawler (`crawler.py`) navega `bancolombia.com/personas`, extrae todos los enlaces internos, los filtra y descarga cada pagina. El contenido HTML se convierte a **Markdown filtrado** (`fit_markdown`) usando la estrategia `PruningContentFilter` que elimina boilerplate (headers, footers, navs). Cada pagina se persiste como una linea JSON con metadata (URL, titulo, categoria, fecha).

### Fase 2: Indexacion (Pipeline)

```
resultados_bancolombia.jsonl  -->  Text Splitter  -->  Embeddings  -->  ChromaDB
     (archivo plano)              (chunks 1500 chars)   (MiniLM-L12)    (vectores)
```

`pipeline.py` lee el JSONL linea a linea, divide el contenido en chunks de 1500 caracteres con overlap de 300, genera embeddings con el modelo `paraphrase-multilingual-MiniLM-L12-v2`, e indexa los vectores en ChromaDB. Se usa procesamiento por lotes de 50 documentos para optimizar I/O.

### Fase 3: Consulta (Agente)

```
Pregunta del usuario
       |
       v
  Agente LangChain (Gemini Flash)
       |
       |-- decide invocar tool --> MCP Server --> ChromaDB (similarity_search)
       |                                |
       |                                v
       |                          KnowledgeBaseResponse
       |                          {contenido, fuentes[]}
       |
       v
  Respuesta final + Fuentes consultadas
```

El agente recibe la pregunta, decide si necesita consultar la base de conocimiento invocando herramientas MCP. La herramienta `search_knowledge_base` retorna los fragmentos relevantes junto con las **URLs de las fuentes**. El agente sintetiza una respuesta y el sistema muestra las fuentes al usuario.

---

## Componentes del sistema

### 1. Crawler (`crawler.py`)

**Responsabilidad:** Extraer y persistir contenido de bancolombia.com.

**Conceptos clave:**

- **Crawling en 2 fases**: Primero extrae URLs semilla de la pagina principal, luego hace deep crawl de cada URL.
- **Persistencia atomica**: Escribe cada pagina al JSONL inmediatamente con `f.flush()`, evitando perdida de datos si el proceso se interrumpe.
- **Rate limiting adaptativo**: `MemoryAdaptiveDispatcher` ajusta la concurrencia segun el uso de memoria del sistema (umbral: 80%).
- **Filtrado de contenido**: `PruningContentFilter` con threshold 0.5 elimina secciones de bajo valor semantico (menus, footers, scripts).
- **Categorizacion automatica**: `categorizar_url()` clasifica cada URL en una de 8 categorias basandose en patrones del path.
- **Invocable como modulo**: `run_crawler(output_file)` puede ser llamado desde `main.py` o `streamlit_app.py` cuando no existe el JSONL.

**Formato de salida (JSONL):**
```json
{
  "url": "https://www.bancolombia.com/personas/cuentas/ahorro",
  "titulo": "Cuentas de Ahorro",
  "categoria": "Productos y Servicios",
  "status_code": 200,
  "scraped_at": "2025-01-15 10:30:00",
  "fit_markdown": "Contenido filtrado en markdown...",
  "raw_markdown": "Contenido completo sin filtrar..."
}
```

### 2. Base de datos vectorial (`database.py`)

**Responsabilidad:** Gestionar la conexion a ChromaDB y el modelo de embeddings.

**Conceptos clave:**

- **Patron Singleton lazy**: `get_store()` crea la instancia de `Chroma` solo en la primera llamada.
- **Embeddings multilingues**: Usa `paraphrase-multilingual-MiniLM-L12-v2`, un modelo de Sentence Transformers optimizado para espanol y otros idiomas. Genera vectores de 384 dimensiones.
- **Persistencia local**: ChromaDB se almacena en disco (`chroma_banco_db/`), sobrevive reinicios del proceso.
- **Validacion de entrada**: Rechaza rutas vacias o nulas en el constructor.

### 3. Pipeline de indexacion y agente (`pipeline.py`)

**Responsabilidad:** Orquestar la indexacion de datos y la configuracion del agente conversacional.

**`indexar_datos()`:**
- Lee el JSONL linea a linea (eficiencia de memoria para archivos grandes).
- **Deduplicacion**: Compara URLs nuevas contra las existentes en ChromaDB para evitar reindexacion.
- **Validacion de registros**: Ignora lineas con JSON invalido, sin URL, o sin `fit_markdown`.
- **Chunking**: `RecursiveCharacterTextSplitter` con 1500 chars y 300 de overlap. Divide respetando limites de palabras y parrafos.
- **Force reindex**: Opcion para borrar la coleccion y reconstruir desde cero.

**`configurar_agente()`:**
- Instancia el modelo LLM: `google_genai:gemini-3.1-flash-lite-preview`.
- Conecta al servidor MCP via `MultiServerMCPClient` usando transporte `stdio` (subproceso).
- Configura `SummarizationMiddleware`: cuando la conversacion excede 3000 tokens, resume automaticamente manteniendo los ultimos 10 mensajes.
- Usa `InMemorySaver` como checkpointer para mantener estado de conversacion por `thread_id`.

### 4. Servidor MCP (`mcp_server.py`)

**Responsabilidad:** Exponer la base de conocimiento como herramientas MCP que el agente puede invocar.

**Herramientas disponibles:**

| Tool | Descripcion | Retorno |
|------|-------------|---------|
| `search_knowledge_base(query)` | Busqueda semantica (top 3) | `KnowledgeBaseResponse` (Pydantic): `{contenido, fuentes[]}` |
| `get_article_by_url(url)` | Recupera articulo completo por URL | JSON string: `{contenido, fuentes[]}` |
| `list_categories()` | Lista categorias unicas de la BD | String con lista de categorias |

**Recurso MCP:**

| Resource | Descripcion |
|----------|-------------|
| `knowledge-base://stats` | Estadisticas de la base: num. documentos, modelo de embeddings, fecha de scraping |

**Conceptos clave:**

- **Structured output con Pydantic**: `search_knowledge_base` retorna un `KnowledgeBaseResponse(BaseModel)` en lugar de texto plano. Esto permite que el agente acceda a las fuentes como datos estructurados via `msg.artifact['structured_content']['fuentes']`, sin depender de regex.
- **Deduplicacion de fuentes**: Si multiples chunks pertenecen a la misma URL, solo se reporta una vez en el campo `fuentes`.
- **Validacion de parametros**: Ambas herramientas validan que `query`/`url` no esten vacios antes de consultar la BD.

### 5. Interfaz CLI (`main.py`)

**Responsabilidad:** Punto de entrada para uso en terminal.

**Flujo:**
1. Carga `.env` y valida `GOOGLE_API_KEY`.
2. Verifica existencia del JSONL; si falta, ejecuta el crawler automaticamente.
3. Inicializa el pipeline y el agente.
4. Entra en un bucle de lectura-respuesta por `input()`.

**Captura de fuentes:**
Durante el streaming de eventos del agente, intercepta:
- Eventos `"tools"` -> extrae fuentes de `msg.artifact['structured_content']['fuentes']`.
- Eventos `"model"` -> extrae la respuesta de texto usando `_extract_text_from_content()` (maneja tanto `str` como `list[ContentBlock]`).

### 6. Interfaz Web (`streamlit_app.py`)

**Responsabilidad:** Interfaz web conversacional con Streamlit.

**Conceptos clave:**

- **Event loop en thread daemon**: Streamlit tiene su propio event loop; las coroutines del agente se ejecutan en un loop separado via `asyncio.run_coroutine_threadsafe()`.
- **Cache del agente**: `@st.cache_resource` inicializa el agente una sola vez y lo reutiliza en reruns de Streamlit.
- **Auto-crawling**: `_ensure_data_file()` verifica el JSONL al inicio. Si falta, muestra un `st.status()` con progreso mientras ejecuta el crawler.
- **Historial de fuentes**: Las fuentes se guardan como markdown en el historial de sesion para que persistan al re-renderizar mensajes previos.

---

## Conceptos fundamentales

### RAG (Retrieval-Augmented Generation)

RAG es el patron arquitectonico central del sistema. En lugar de depender exclusivamente del conocimiento parametrico del LLM, el agente **recupera informacion relevante** de una base de datos externa antes de generar su respuesta.

```
      Pregunta
         |
    +----v-----+       +-------------+       +-----------+
    |  Retrieval| ----> | Augmentation| ----> | Generation|
    |  (ChromaDB|       | (contexto + |       | (Gemini   |
    |  search)  |       |  pregunta)  |       |  Flash)   |
    +-----------+       +-------------+       +-----------+
```

**Ventajas en este proyecto:**
- El LLM no necesita estar entrenado en datos especificos de Bancolombia.
- La informacion se actualiza re-ejecutando el crawler sin reentrenar el modelo.
- Las respuestas incluyen fuentes verificables (URLs de bancolombia.com).

### MCP (Model Context Protocol)

MCP es un protocolo abierto creado por Anthropic que estandariza como los modelos de lenguaje acceden a herramientas y datos externos. En este sistema:

- **Servidor MCP** (`mcp_server.py`): Proceso independiente que expone `search_knowledge_base`, `get_article_by_url` y `list_categories` como herramientas.
- **Cliente MCP** (`MultiServerMCPClient` en `pipeline.py`): Conecta al servidor via `stdio` (subproceso) y registra las herramientas en el agente LangChain.
- **Transporte stdio**: El servidor MCP se ejecuta como un subproceso Python. La comunicacion se hace via stdin/stdout con mensajes JSON-RPC.

```
pipeline.py                     mcp_server.py
    |                                |
    |--- spawn subprocess ---------> |
    |                                |
    |--- JSON-RPC (stdin) ---------> |
    |    "search_knowledge_base"     |
    |                                |--- query ChromaDB
    |                                |<-- results
    |<-- JSON-RPC (stdout) --------- |
    |    KnowledgeBaseResponse       |
```

**Por que MCP y no herramientas directas?**
- Desacopla la logica de acceso a datos del agente.
- El servidor MCP puede ser reemplazado o ampliado sin modificar el agente.
- Permite exponer recursos como `knowledge-base://stats`.

### Embeddings y busqueda vectorial

El modelo `paraphrase-multilingual-MiniLM-L12-v2` convierte texto a vectores de 384 dimensiones que capturan su significado semantico. ChromaDB almacena estos vectores y permite busqueda por similitud coseno.

```
"Cuentas de ahorro Bancolombia"  -->  [0.23, -0.15, 0.87, ...]  (384 dims)
"Productos para ahorrar dinero"  -->  [0.21, -0.14, 0.85, ...]  (alta similitud)
"Creditos de vivienda"           -->  [0.05, 0.72, -0.33, ...]  (baja similitud)
```

**Chunking strategy:**
Los documentos se dividen en fragmentos de 1500 caracteres con 300 de overlap. El overlap asegura que las ideas que cruzan limites de chunk no se pierdan.

### Agentes con herramientas

El agente usa `create_agent` de LangChain que implementa un ciclo **ReAct** (Reasoning + Acting):

1. El agente recibe la pregunta.
2. **Razona** si necesita una herramienta y cual.
3. **Actua** invocando la herramienta via MCP.
4. **Observa** el resultado (contenido + fuentes).
5. **Razona** si tiene suficiente informacion.
6. **Responde** al usuario con la sintesis.

El `SummarizationMiddleware` comprime automaticamente el historial cuando supera 3000 tokens, manteniendo los ultimos 10 mensajes intactos y resumiendo los anteriores.

### Streaming de eventos

El agente emite eventos incrementales via `agent.astream()`:

```python
# Evento 1: El modelo decide invocar un tool
{"model": {"messages": [AIMessage(tool_calls=[...])]}}

# Evento 2: El tool retorna su resultado
{"tools": {"messages": [ToolMessage(content="...", artifact={...})]}}

# Evento 3: El modelo genera la respuesta final
{"model": {"messages": [AIMessage(content="Respuesta final")]}}
```

Los clientes (`main.py`, `streamlit_app.py`) interceptan estos eventos para:
- Capturar fuentes de los eventos `"tools"` (vienen en `msg.artifact`).
- Mostrar la respuesta de los eventos `"model"`.

### Structured output en herramientas

`search_knowledge_base` retorna un modelo Pydantic `KnowledgeBaseResponse`:

```python
class KnowledgeBaseResponse(BaseModel):
    contenido: str                          # Texto de los fragmentos
    fuentes: list[dict[str, str]] | list    # [{titulo, url}, ...]
```

Cuando FastMCP serializa un retorno Pydantic, lo expone en el `ToolMessage.artifact` como:
```python
msg.artifact["structured_content"]["fuentes"]
# -> [{"titulo": "Cuentas de Ahorro", "url": "https://..."}]
```

Esto permite acceder a las fuentes como datos estructurados sin parsear texto.

---

## Stack tecnologico

| Capa | Tecnologia | Proposito |
|------|-----------|-----------|
| LLM | Google Gemini 3.1 Flash Lite | Generacion de respuestas |
| Framework de agentes | LangChain + LangGraph | Orquestacion del agente ReAct |
| Protocolo de herramientas | MCP (FastMCP) | Comunicacion agente <-> herramientas |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` | Vectorizacion de texto en espanol |
| Base vectorial | ChromaDB | Almacenamiento y busqueda de vectores |
| Web scraping | Crawl4AI + Playwright | Extraccion de contenido web |
| Interfaz web | Streamlit | UI conversacional |
| Contenedores | Docker + Docker Compose | Despliegue |
| Testing | pytest | Tests unitarios con mocks |

---

## Estructura de archivos

```
BancolombiaTest/
|
|-- src/
|   |-- crawler.py          # Web scraping de bancolombia.com
|   |-- database.py          # Cliente ChromaDB + embeddings
|   |-- pipeline.py          # Orquestador: indexacion + agente
|   |-- mcp_server.py        # Servidor MCP con herramientas de busqueda
|   |-- main.py              # Interfaz CLI
|   |-- streamlit_app.py     # Interfaz web Streamlit
|
|-- tests/
|   |-- conftest.py          # Fixtures compartidos (mock_vector_store, sample_jsonl)
|   |-- test_crawler.py      # Tests de is_crawlable, categorizar_url
|   |-- test_database.py     # Tests de VectorDBClient
|   |-- test_main.py         # Tests de _extract_text_from_content
|   |-- test_mcp_server.py   # Tests de las herramientas MCP
|   |-- test_pipeline.py     # Tests de indexar_datos
|
|-- data/                    # Directorio para el JSONL (montado como volumen en Docker)
|   |-- .gitkeep
|
|-- chroma_banco_db/         # Base vectorial ChromaDB (generada en runtime)
|
|-- Dockerfile               # Imagen Docker con Playwright + deps del sistema
|-- docker-compose.yml       # Servicio con volumenes y env vars
|-- .dockerignore            # Excluye datos, tests, cache del build
|-- requirements.txt         # Dependencias Python
|-- pyproject.toml           # Configuracion de pytest
|-- .env                     # GOOGLE_API_KEY (no versionado)
```

---

## Infraestructura y despliegue

### Variables de entorno

| Variable | Descripcion | Default |
|----------|------------|---------|
| `GOOGLE_API_KEY` | API key de Google AI Studio (obligatoria) | - |
| `DATA_DIR` | Directorio donde se almacena el JSONL | Raiz del proyecto |
| `DB_PATH` | Directorio de ChromaDB | `./chroma_banco_db` |

### Docker

El `Dockerfile` construye una imagen basada en `python:3.12-slim` con:
- Dependencias del sistema para Playwright (headless Chromium).
- `crawl4ai-setup` para instalar los navegadores.
- Healthcheck via `/_stcore/health` de Streamlit.

`docker-compose.yml` monta dos volumenes:
- `./data:/app/data` - Para el JSONL generado por el crawler.
- `./chroma_banco_db:/app/chroma_banco_db` - Para la base vectorial.

Si `./data` esta vacio al iniciar, la app detecta la ausencia del JSONL y ejecuta el crawler automaticamente.

```bash
# Iniciar el sistema
docker compose up --build

# El sistema:
# 1. Verifica si existe data/resultados_bancolombia.jsonl
# 2. Si no existe, ejecuta el crawler (~5-15 min)
# 3. Indexa el contenido en ChromaDB
# 4. Inicia el agente y la interfaz web en :8501
```

### Ejecucion local (sin Docker)

```bash
# 1. Instalar dependencias
pip install -r requirements.txt
crawl4ai-setup

# 2. Configurar API key
echo "GOOGLE_API_KEY=tu_clave" > .env

# 3a. Interfaz web
streamlit run src/streamlit_app.py

# 3b. Interfaz CLI
python src/main.py
```

---

## Testing

40 tests unitarios organizados por modulo, todos ejecutables sin servicios externos ni API keys:

```bash
python -m pytest tests/ -v
```

| Test file | Tests | Que valida |
|-----------|-------|------------|
| `test_crawler.py` | 10 | `is_crawlable()`, `categorizar_url()` con todas las categorias |
| `test_database.py` | 4 | `VectorDBClient`: creacion lazy, singleton, constantes |
| `test_main.py` | 7 | `_extract_text_from_content()`: str, ContentBlocks, tipos inesperados |
| `test_mcp_server.py` | 14 | Todas las herramientas MCP: resultados, vacios, errores, deduplicacion |
| `test_pipeline.py` | 5 | `indexar_datos()`: archivo faltante, procesamiento, lotes, force_reindex |

Todos los tests usan `unittest.mock.patch` para aislar dependencias externas (ChromaDB, embeddings, filesystem).
