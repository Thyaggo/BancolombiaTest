# Interfaz de Línea de Comandos (`main.py`)

## Descripción
`main.py` es el punto de entrada principal para interactuar con el Asistente Bancolombia desde la terminal. Orquestra la inicialización de todos los subsistemas y gestiona el bucle de conversación del usuario.

## Flujo de Ejecución

1.  **Carga de Entorno:** Lee las variables del archivo `.env` (especialmente `GOOGLE_API_KEY`).
2.  **Verificación de Datos:** Llama a `_ensure_data_file()`. Si el archivo JSONL no existe o está vacío, lanza el `crawler.py` automáticamente antes de continuar.
3.  **Inicialización:** Crea la instancia de `BancolombiaPipeline` y configura el Agente.
4.  **Bucle de Chat:** Entra en un ciclo `while` que lee la entrada del usuario (`input()`), procesa la pregunta a través del agente y muestra la respuesta.

## Funciones Auxiliares

### `_ensure_data_file()`
Garantiza que el sistema siempre tenga conocimiento para operar. Si falta el archivo de datos, informa al usuario y ejecuta el proceso de extracción de forma síncrona.

### `_extract_text_from_content(content)`
Normaliza la salida del modelo LLM (Gemini). Maneja tanto cadenas de texto directas como listas de bloques de contenido (`ContentBlocks`), asegurando que solo se imprima texto legible en la terminal.

## Manejo de Eventos (Streaming)
El CLI utiliza `agent.astream()` para procesar la respuesta del agente. Esto permite capturar información en tiempo real de dos tipos de eventos:
-   **Eventos `"tools"`:** Intercepta la salida de las herramientas MCP para extraer las fuentes consultadas (títulos y URLs) de forma estructurada.
-   **Eventos `"model"`:** Captura la respuesta final sintetizada por el LLM y la presenta al usuario.

## Visualización de Fuentes
Al final de cada respuesta que involucre el uso de herramientas de búsqueda, el sistema imprime una lista clara de las páginas de Bancolombia que se consultaron para generar dicha respuesta, promoviendo la transparencia y verificabilidad.
