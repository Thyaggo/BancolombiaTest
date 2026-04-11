# Pipeline de Indexación y Agente (`pipeline.py`)

## Descripción
El Pipeline es el orquestador principal del sistema. Su función es doble:
1.  **Fase de Indexación:** Transformar los datos extraídos por el Crawler (archivo JSONL) en vectores dentro de la base de datos (ChromaDB).
2.  **Fase de Configuración:** Instanciar y conectar el modelo LLM con las herramientas MCP para crear el Agente inteligente.

## Clase `BancolombiaPipeline`

### Métodos Principales

#### `indexar_datos(force_reindex=False)`
Lee el archivo de salida del Crawler línea a línea para un uso eficiente de la memoria RAM. Realiza las siguientes tareas:
-   **Deduplicación:** Verifica si la URL ya existe en ChromaDB antes de procesarla para evitar duplicados.
-   **Filtrado:** Ignora registros incompletos o sin contenido semántico relevante (`fit_markdown`).
-   **Chunking:** Utiliza `RecursiveCharacterTextSplitter` para dividir cada página en fragmentos de **1500 caracteres con un solapamiento (overlap) de 300 caracteres**. Esto asegura que las ideas no se corten abruptamente.
-   **Procesamiento por Lotes:** Agrupa los documentos en bloques de 50 antes de indexarlos para optimizar el rendimiento de la base de datos.
-   **Force Reindex:** Permite borrar la colección actual y reconstruirla desde cero si es necesario.

#### `configurar_agente()`
Configura el motor de razonamiento del sistema (LLM) y sus capacidades externas:
-   **Modelo:** Utiliza `google_genai:gemini-3.1-flash-lite-preview` como el cerebro del sistema.
-   **Conector MCP:** Utiliza `MultiServerMCPClient` para lanzar el servidor MCP como un subproceso (`stdio`) y registrar sus herramientas.
-   **Middleware de Resumen:** Configura una política de memoria para el historial de conversación. Cuando se superan los 3000 tokens, el sistema resume los mensajes antiguos manteniendo los 10 más recientes intactos.
-   **Checkpointer:** Utiliza `InMemorySaver` para gestionar el estado de múltiples conversaciones simultáneas mediante `thread_id`.

## Decisiones Técnicas
-   **LangChain + LangGraph:** El agente se construye sobre estas librerías para facilitar la orquestación de herramientas (Tools) y la persistencia de la memoria de sesión.
-   **Eficiencia de Lectura:** Al procesar el JSONL línea a línea, el sistema puede manejar archivos de datos de varios gigabytes sin agotar la memoria del servidor o contenedor.
-   **Arquitectura Desacoplada:** El pipeline no gestiona la lógica de base de datos directamente, sino que delega esa responsabilidad al cliente `VectorDBClient` inyectado en su constructor.
