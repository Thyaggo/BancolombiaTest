# Servidor MCP (`mcp_server.py`)

## Descripción
El servidor **MCP (Model Context Protocol)** es un componente independiente que expone la base de conocimiento de Bancolombia como herramientas (Tools) y recursos (Resources) estandarizados. Utiliza la librería `FastMCP` para facilitar la comunicación entre el Agente LLM y la base de datos vectorial.

## Herramientas (Tools) Disponibles

### `search_knowledge_base(query)`
Realiza una búsqueda semántica en la base de datos vectorial (top 3 resultados).
-   **Uso:** Cuando el agente necesita responder una pregunta general basada en el conocimiento de Bancolombia.
-   **Retorno:** Un objeto `KnowledgeBaseResponse` que contiene el texto de los fragmentos encontrados y una lista estructurada de las fuentes consultadas (títulos y URLs).

### `get_article_by_url(url)`
Recupera el contenido íntegro (todos los fragmentos) de una página específica de Bancolombia basándose en su URL exacta.
-   **Uso:** Cuando el agente necesita profundizar en un artículo sugerido previamente o cuando el usuario provee un enlace directo.
-   **Retorno:** Una cadena JSON con el contenido y la fuente de la página.

### `list_categories()`
Devuelve una lista única de las categorías de contenido presentes en la base de datos indexada.
-   **Uso:** Permite al agente conocer el alcance temático de su base de conocimiento y guiar al usuario.

## Recursos (Resources) Disponibles

### `knowledge-base://stats`
Un recurso estático que expone metadatos operativos de la base de conocimiento:
-   Número total de documentos indexados.
-   Fecha de la última extracción (timestamp de muestra).
-   Nombre del modelo de embeddings utilizado.

## Decisiones Técnicas
-   **Structured Output con Pydantic:** Se utiliza `KnowledgeBaseResponse(BaseModel)` para retornar datos estructurados al agente. Esto permite que el cliente (CLI o Web) acceda a las fuentes como datos crudos sin tener que parsear texto plano.
-   **Deduplicación de Fuentes:** Si la búsqueda vectorial retorna múltiples fragmentos de una misma página, el servidor los agrupa y reporta la URL una sola vez en la lista de fuentes.
-   **Aislamiento:** El servidor MCP se ejecuta como un subproceso independiente, desacoplando completamente la lógica de búsqueda de la lógica de conversación del agente.
